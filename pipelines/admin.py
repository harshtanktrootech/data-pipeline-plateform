from django.contrib import admin
from pipelines.models import Pipeline


@admin.register(Pipeline)
class PipelineAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "status",
        "created_by",
        "created_at",
    )