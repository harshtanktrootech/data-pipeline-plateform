from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from audit.models import AuditLog


@login_required(login_url="/login/")
def audit_log_list_page(request):
    """Admin-only view displaying system audit logs."""
    is_admin = request.user.is_superuser or request.user.groups.filter(name="Admin").exists()
    
    if not is_admin:
        messages.error(request, "Permission Denied: Only Admins can access Audit Logs.")
        return redirect("pipeline-list-page")

    logs = AuditLog.objects.select_related("user").all()[:100]
    return render(request, "audit/audit_list.html", {"logs": logs})
