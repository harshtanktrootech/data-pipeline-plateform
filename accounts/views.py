from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group
from django.contrib import messages
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.permissions import IsAdmin, IsOperator, IsViewer
from audit.services import log_action


# ── HTML Authentication Views ──

def register_view(request):
    if request.user.is_authenticated:
        return redirect("pipeline-list-page")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        role_name = request.POST.get("role", "Viewer")
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        # 1. Validation
        if not username or not password:
            messages.error(request, "Username and password are required.")
            return render(request, "accounts/register.html")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "accounts/register.html")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists. Please pick another.")
            return render(request, "accounts/register.html")

        # 2. Create User
        user = User.objects.create_user(username=username, email=email, password=password)

        # 3. Assign Role Group (Admin, Operator, Viewer)
        group, _ = Group.objects.get_or_create(name=role_name)
        user.groups.add(group)

        if role_name == "Admin":
            user.is_staff = True  # Allows admin access
            user.save()

        messages.success(request, f"Account created successfully as {role_name}! Please log in.")
        return redirect("login-page")

    return render(request, "accounts/register.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("pipeline-list-page")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            log_action(user, "USER_LOGIN", f"User '{user.username}'", "Logged in via web form", request)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect("pipeline-list-page")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "accounts/login.html")


def logout_view(request):
    if request.user.is_authenticated:
        log_action(request.user, "USER_LOGOUT", f"User '{request.user.username}'", "Logged out from web interface", request)
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("login-page")


# ── DRF Test Views ──

class AdminTestAPIView(APIView):
    permission_classes = [IsAdmin]
    def get(self, request):
        return Response({"message": "Welcome Admin"})

class OperatorTestAPIView(APIView):
    permission_classes = [IsOperator]
    def get(self, request):
        return Response({"message": "Welcome Operator"})

class ViewerTestAPIView(APIView):
    permission_classes = [IsViewer]
    def get(self, request):
        return Response({"message": "Welcome Viewer"})


# ── Admin User Management & RBAC Views ──

def admin_only(view_func):
    """
    Decorator that checks if the logged-in user is an Admin or Superuser.
    If not, redirects them to dashboard with an error message.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        is_admin = request.user.is_superuser or request.user.groups.filter(name="Admin").exists()
        if not is_admin:
            messages.error(request, "Permission Denied: Only Admins can manage users.")
            return redirect("dashboard")
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@admin_only
def user_management_view(request):
    """
    Lists all users with their roles and handles the registration of new users by Admin.
    """
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        role_name = request.POST.get("role", "Viewer")

        if not username or not password:
            messages.error(request, "Username and password are required.")
            return redirect("user-management-page")

        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' already exists. Please pick another.")
            return redirect("user-management-page")

        # 1. Create User
        new_user = User.objects.create_user(username=username, email=email, password=password)

        # 2. Assign Role Group
        group, _ = Group.objects.get_or_create(name=role_name)
        new_user.groups.add(group)

        if role_name == "Admin":
            new_user.is_staff = True
            new_user.save()

        # 3. Log Audit Action
        log_action(
            user=request.user,
            action="USER_CREATE",
            resource=f"User #{new_user.id} ({new_user.username})",
            details=f"Created with role '{role_name}' by Admin '{request.user.username}'",
            request=request,
        )

        messages.success(request, f"User '{username}' registered successfully with role '{role_name}'!")
        return redirect("user-management-page")

    # GET Request: Fetch users with groups
    users = User.objects.all().prefetch_related("groups").order_by("-date_joined")

    users_data = []
    for u in users:
        group_names = list(u.groups.values_list("name", flat=True))
        if u.is_superuser or "Admin" in group_names:
            role = "Admin"
        elif "Operator" in group_names:
            role = "Operator"
        else:
            role = "Viewer"

        users_data.append({
            "user": u,
            "role": role,
        })

    return render(request, "accounts/user_management.html", {"users_data": users_data})


@login_required
@admin_only
def user_role_update_view(request, user_id):
    """
    Updates the role (Admin, Operator, Viewer) of an existing user.
    """
    if request.method == "POST":
        target_user = get_object_or_404(User, id=user_id)
        new_role = request.POST.get("role")

        # Safety Check: Admin cannot demote their own account
        if target_user == request.user and new_role != "Admin":
            messages.error(request, "Safety Warning: You cannot demote your own Admin account.")
            return redirect("user-management-page")

        if new_role in ["Admin", "Operator", "Viewer"]:
            old_groups = list(target_user.groups.values_list("name", flat=True))
            old_role = old_groups[0] if old_groups else "Viewer"

            # Reset previous roles and assign the new role
            target_user.groups.filter(name__in=["Admin", "Operator", "Viewer"]).delete()
            group, _ = Group.objects.get_or_create(name=new_role)
            target_user.groups.add(group)

            target_user.is_staff = (new_role == "Admin")
            target_user.save()

            # Log Audit Action
            log_action(
                user=request.user,
                action="USER_ROLE_UPDATE",
                resource=f"User #{target_user.id} ({target_user.username})",
                details=f"Role changed from '{old_role}' to '{new_role}' by Admin '{request.user.username}'",
                request=request,
            )

            messages.success(request, f"Role for '{target_user.username}' updated to '{new_role}'.")
        else:
            messages.error(request, "Invalid role selected.")

    return redirect("user-management-page")


@login_required
@admin_only
def user_delete_view(request, user_id):
    """
    Allows Admins to delete a user account safely and logs the action to Audit Log.
    """
    if request.method == "POST":
        target_user = get_object_or_404(User, id=user_id)

        # Safety Check 1: Admin cannot delete their own account
        if target_user == request.user:
            messages.error(request, "Safety Warning: You cannot delete your own account.")
            return redirect("user-management-page")

        # Safety Check 2: Prevent deleting the only superuser
        if target_user.is_superuser and User.objects.filter(is_superuser=True).count() <= 1:
            messages.error(request, "Safety Warning: Cannot delete the only superuser account.")
            return redirect("user-management-page")

        username = target_user.username
        user_id_val = target_user.id
        role = "Admin" if target_user.is_staff or target_user.groups.filter(name="Admin").exists() else (
            "Operator" if target_user.groups.filter(name="Operator").exists() else "Viewer"
        )

        # Reassign any pipelines created by this user to the requesting Admin
        # so data pipelines are preserved safely
        target_user.pipelines.update(created_by=request.user)

        target_user.delete()

        # Log Audit Action
        log_action(
            user=request.user,
            action="USER_DELETE",
            resource=f"User #{user_id_val} ({username})",
            details=f"User '{username}' (Role: {role}) deleted by Admin '{request.user.username}'",
            request=request,
        )

        messages.success(request, f"User '{username}' has been deleted successfully.")

    return redirect("user-management-page")

