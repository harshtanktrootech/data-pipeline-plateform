from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
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
    """Admin-only view displaying system audit logs."""
    is_admin = request.user.is_superuser or request.user.groups.filter(name="Admin").exists()
    
    if not is_admin:
        messages.error(request, "Permission Denied: Only Admins can access Audit Logs.")
        return redirect("pipeline-list-page")

    logs = AuditLog.objects.select_related("user").all()[:100]
    return render(request, "audit/audit_list.html", {"logs": logs})
