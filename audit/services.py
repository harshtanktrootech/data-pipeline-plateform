from audit.models import AuditLog


def log_action(user, action: str, resource: str, details: str = ""):
    """
    Creates an audit log entry in the database.
    
    Usage:
      log_action(request.user, "PIPELINE_RUN", f"Pipeline #{pipeline.id}", "Manual trigger")
    """
    
    return AuditLog.objects.create(
        user=user if (user and user.is_authenticated) else None,
        action=action,
        resource=resource,
        details=details,
    )
