from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from rest_framework import generics

from accounts.permissions import IsAdmin
from audit.models import AuditLog
from audit.serializers import AuditLogSerializer

from django.shortcuts import get_object_or_404
import json
import re
from pipelines.models import Pipeline

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


@login_required(login_url="/login/")
def audit_log_detail_page(request, pk):
    """
    Admin-only view displaying complete detail of an individual Audit Log entry:
    - Actor, timestamp, action type, resource
    - Records added vs updated metrics
    - 2-Tab interface for Success and Failed data rows on Partial or Full failures
    - Full row-level error breakdown and JSON payload viewer
    """
    is_admin = request.user.is_superuser or request.user.groups.filter(name="Admin").exists()
    if not is_admin:
        messages.error(request, "Permission Denied: Only Admins can access Audit Log details.")
        return redirect("pipeline-list-page")


    log = get_object_or_404(
        AuditLog.objects.select_related("user", "execution", "execution__pipeline"),
        pk=pk,
    )

    # Try resolving associated pipeline
    pipeline = None
    if log.execution and log.execution.pipeline:
        pipeline = log.execution.pipeline
    elif log.resource:
        m = re.search(r"#(\d+)", log.resource)
        if m:
            pipeline = Pipeline.objects.filter(pk=int(m.group(1))).first()

    status = log.outcome_status
    records_added = log.display_records_added
    records_updated = log.records_updated
    records_failed = log.records_failed

    failed_rows = log.failed_rows_list
    success_rows = log.success_rows_list

    # Extract headers
    success_headers = []
    if success_rows and isinstance(success_rows[0], dict) and "data" in success_rows[0]:
        success_headers = list(success_rows[0]["data"].keys())

    failed_headers = []
    if failed_rows and isinstance(failed_rows[0], dict) and "data" in failed_rows[0]:
        failed_headers = list(failed_rows[0]["data"].keys())

    # Build clean row lists with cell values matching headers
    formatted_success_rows = []
    for item in success_rows:
        if isinstance(item, dict) and "data" in item:
            row_dict = item["data"]
            formatted_success_rows.append({
                "row_number": item.get("row_number", "-"),
                "action": item.get("action", "added"),
                "cells": [row_dict.get(h) for h in success_headers],
            })

    formatted_failed_rows = []
    for item in failed_rows:
        if isinstance(item, dict):
            row_dict = item.get("data", {})
            cells = [row_dict.get(h) for h in failed_headers] if failed_headers else []
            formatted_failed_rows.append({
                "row_number": item.get("row_number", "-"),
                "error": item.get("error", "Error encountered"),
                "cells": cells,
            })

    # Default active tab
    active_tab = "failed" if (status == "FAILED" and failed_rows) else "success"

    return render(
        request,
        "audit/audit_detail.html",
        {
            "log": log,
            "pipeline": pipeline,
            "status": status,
            "records_added": records_added,
            "records_updated": records_updated,
            "records_failed": records_failed,
            "success_headers": success_headers,
            "failed_headers": failed_headers,
            "success_rows": formatted_success_rows,
            "failed_rows": formatted_failed_rows,
            "active_tab": active_tab,
        },
    )
