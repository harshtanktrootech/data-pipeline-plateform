from django.db import models
from django.contrib.auth.models import User


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ("USER_LOGIN", "User Login"),
        ("USER_LOGOUT", "User Logout"),
        ("USER_CREATE", "User Created"),
        ("USER_ROLE_UPDATE", "User Role Updated"),
        ("USER_DELETE", "User Deleted"),
        ("PIPELINE_CREATE", "Pipeline Created"),
        ("PIPELINE_UPDATE", "Pipeline Updated"),
        ("PIPELINE_DELETE", "Pipeline Deleted"),
        ("PIPELINE_RUN", "Pipeline Run Triggered"),
        ("PIPELINE_STATUS_CHANGE", "Pipeline Status Changed"),
        ("SCHEDULE_UPDATE", "Schedule Updated"),
        ("SCHEDULE_TOGGLE", "Schedule Toggled (Pause/Resume)"),
        ("SCHEDULE_DELETE", "Schedule Deleted"),
    ]

    STATUS_CHOICES = [
        ("SUCCESS", "Success"),
        ("PARTIALLY_FAILED", "Partially Failed"),
        ("FAILED", "Failed"),
        ("INFO", "Info"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text="User who performed the action (null for system/automated events)."
    )

    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    resource = models.CharField(max_length=255, help_text="The target entity (e.g. Pipeline #31)")
    details = models.TextField(blank=True, null=True, help_text="Additional details or metadata")
    
    # Execution & Outcome Tracking
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="INFO",
        blank=True,
        null=True,
        help_text="Outcome status of the action or execution"
    )
    records_added = models.IntegerField(default=0, help_text="Number of records newly inserted")
    records_updated = models.IntegerField(default=0, help_text="Number of records updated")
    records_failed = models.IntegerField(default=0, help_text="Number of records failed")
    error_details = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text="Detailed failure data and row-level errors saved as JSON"
    )
    execution = models.ForeignKey(
        "executions.PipelineExecution",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text="Optional link to pipeline execution"
    )

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"

    def __str__(self):
        user_str = self.user.username if self.user else "System"
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {user_str} - {self.get_action_display()} on {self.resource}"

    @property
    def outcome_status(self):
        """Resolves the outcome status with fallback parsing for legacy logs."""
        if self.status and self.status != "INFO":
            return self.status
        if self.details:
            if "Status: PARTIALLY_FAILED" in self.details:
                return "PARTIALLY_FAILED"
            if "Status: SUCCESS" in self.details:
                return "SUCCESS"
            if "Status: FAILED" in self.details:
                return "FAILED"
        return self.status or "INFO"

    @property
    def failed_rows_list(self):
        """Extracts list of failed rows with errors from error_details JSON."""
        if isinstance(self.error_details, dict):
            return self.error_details.get("failed_rows", [])
        if isinstance(self.error_details, list):
            return self.error_details
        return []

    @property
    def success_rows_list(self):
        """Extracts sample/list of successfully processed rows from error_details JSON."""
        if isinstance(self.error_details, dict):
            return self.error_details.get("success_rows", [])
        return []

    @property
    def display_records_added(self):
        if self.records_added:
            return self.records_added
        if self.details and "Loaded:" in self.details:
            import re
            m = re.search(r"Loaded:\s*(\d+)", self.details)
            if m:
                return int(m.group(1))
        return 0

    @property
    def total_processed(self):
        return self.records_added + self.records_updated + self.records_failed
