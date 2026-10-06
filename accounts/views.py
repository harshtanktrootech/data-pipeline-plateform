from django.shortcuts import render, redirect
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
