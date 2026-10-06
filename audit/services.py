from audit.models import AuditLog


def get_client_ip(request):
    """Extracts client IP address from HTTP request."""
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_action(user, action: str, resource: str, details: str = "", request=None):
    """
    Creates an audit log entry in the database.
    
    Usage:
      log_action(request.user, "PIPELINE_RUN", f"Pipeline #{pipeline.id}", "Manual trigger", request)
    """
    ip = get_client_ip(request) if request else None
    
    return AuditLog.objects.create(
        user=user if (user and user.is_authenticated) else None,
        action=action,
        resource=resource,
        details=details,
        ip_address=ip,
    )
