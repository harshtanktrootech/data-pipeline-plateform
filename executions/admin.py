from django.contrib import admin
from executions.models import PipelineExecution


@admin.register(PipelineExecution)
class PipelineExecutionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pipeline",
        "status",
        "triggered_by",
        "records_extracted",
        "records_processed",
        "records_loaded",
        "duration_seconds",
        "started_at",
    )
    list_filter = ("status", "pipeline", "started_at")
    search_fields = ("pipeline__name", "error_message", "triggered_by__username")
    readonly_fields = ("started_at", "completed_at", "duration_seconds")
    ordering = ("-started_at",)
