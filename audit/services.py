from audit.models import AuditLog


def log_action(user, action: str, resource: str, details: str = "", request=None):
    """
    Creates an audit log entry in the database.
    
    Usage:
      log_action(request.user, "PIPELINE_RUN", f"Pipeline #{pipeline.id}", "Manual trigger", request)
    """
    # ip = get_client_ip(request) if request else None
    
    return AuditLog.objects.create(
        user=user if (user and user.is_authenticated) else None,
        action=action,
        resource=resource,
        details=details,
    )
