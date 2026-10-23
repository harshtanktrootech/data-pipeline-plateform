from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from rest_framework import generics

from accounts.permissions import IsAdmin
from audit.models import AuditLog
from audit.serializers import AuditLogSerializer


# ── REST API Views ──

class AuditLogListAPIView(generics.ListAPIView):
    """
    GET /api/audit/
    Lists system audit logs (Admin only).
    Supports optional query filters:
      - ?action=PIPELINE_RUN / USER_LOGIN / etc.
      - ?user=<user_id>
    """
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        queryset = AuditLog.objects.select_related("user").all()

        action_param = self.request.query_params.get("action")
        if action_param:
            queryset = queryset.filter(action=action_param.strip().upper())

        user_param = self.request.query_params.get("user")
        if user_param and user_param.isdigit():
            queryset = queryset.filter(user_id=int(user_param))

        return queryset


class AuditLogDetailAPIView(generics.RetrieveAPIView):
    """
    GET /api/audit/<id>/
    Retrieves a single audit log entry (Admin only).
    """
    queryset = AuditLog.objects.select_related("user").all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdmin]


# ── Frontend HTML Views ── 

@login_required(login_url="/login/")
def audit_log_list_page(request):
    """Admin-only view displaying system audit logs with user and date filtering."""
    is_admin = request.user.is_superuser or request.user.groups.filter(name="Admin").exists()
    
    if not is_admin:
        messages.error(request, "Permission Denied: Only Admins can access Audit Logs.")
        return redirect("pipeline-list-page")

    logs = AuditLog.objects.select_related("user").all()

    # 1. User Filter (Specific user or System)
    user_id = request.GET.get("user", "").strip()
    if user_id == "system":
        logs = logs.filter(user__isnull=True)
    elif user_id.isdigit():
        logs = logs.filter(user_id=int(user_id))

    # 2. Date Filter (Specific selected date)
    date_filter = request.GET.get("date", "").strip()
    if date_filter:
        logs = logs.filter(timestamp__date=date_filter)

    total_logs = logs.count()

    return render(
        request,
        "audit/audit_list.html",
        {
            "logs": logs[:100],
            "users": User.objects.all(),
            "total_logs": total_logs,
            "filters": {
                "user": user_id,
                "date": date_filter,
            },
        },
    )
