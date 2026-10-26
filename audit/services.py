from audit.models import AuditLog


def log_action(
    user,
    action: str,
    resource: str,
    details: str = "",
    status: str = "INFO",
    records_added: int = 0,
    records_updated: int = 0,
    records_failed: int = 0,
    error_details: dict | list = None,
    execution=None,
):
    """
    Creates an audit log entry in the database.
    
    Usage:
      log_action(request.user, "PIPELINE_RUN", f"Pipeline #{pipeline.id}", "Manual trigger",
                 status="SUCCESS", records_added=10, records_updated=0, records_failed=0,
                 error_details={...}, execution=execution)
    """
    return AuditLog.objects.create(
        user=user if (user and user.is_authenticated) else None,
        action=action,
        resource=resource,
        details=details,
        status=status or "INFO",
        records_added=records_added,
        records_updated=records_updated,
        records_failed=records_failed,
        error_details=error_details or {},
        execution=execution,
    )
