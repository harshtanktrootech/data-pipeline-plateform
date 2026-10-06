from django.db import models
from django.contrib.auth.models import User


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ("USER_LOGIN", "User Login"),
        ("USER_LOGOUT", "User Logout"),
        ("PIPELINE_CREATE", "Pipeline Created"),
        ("PIPELINE_UPDATE", "Pipeline Updated"),
        ("PIPELINE_DELETE", "Pipeline Deleted"),
        ("PIPELINE_RUN", "Pipeline Run Triggered"),
        ("SCHEDULE_UPDATE", "Schedule Updated"),
        ("SCHEDULE_TOGGLE", "Schedule Toggled (Pause/Resume)"),
        ("SCHEDULE_DELETE", "Schedule Deleted"),
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
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"

    def __str__(self):
        user_str = self.user.username if self.user else "System"
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {user_str} - {self.get_action_display()} on {self.resource}"
