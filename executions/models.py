from django.db import models
from django.contrib.auth.models import User
from pipelines.models import Pipeline


class PipelineExecution(models.Model):
    STATUS_CHOICES = [
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
        ("RUNNING", "Running"),
    ]

    pipeline = models.ForeignKey(
        Pipeline,
        on_delete=models.CASCADE,
        related_name="executions",
        help_text="The pipeline that was executed."
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="RUNNING",
    )

    triggered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_executions",
        help_text="User who started this execution (null if scheduled/system)."
    )

    records_extracted = models.IntegerField(default=0)
    records_processed = models.IntegerField(default=0)
    records_loaded = models.IntegerField(default=0)
    duration_seconds = models.FloatField(default=0.0)

    error_message = models.TextField(blank=True, null=True)
    attempts = models.IntegerField(default=1)

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.pipeline.name} - {self.status} ({self.started_at.strftime('%Y-%m-%d %H:%M')})"
