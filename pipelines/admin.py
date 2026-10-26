from django.contrib import admin
from pipelines.models import Pipeline


@admin.register(Pipeline)
class PipelineAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "source",
        "status",
        "table_name",
        "created_by",
        "created_at",
    )
    list_filter = (
        "status",
        "created_by",
        "created_at",
    )
    search_fields = (
        "name",
        "source",
        "table_name",
        "description",
    )
    fields = (
        "name",
        "source",
        "status",
        "description",
        "table_name",
        "created_by",
    )

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        if "created_by" not in initial:
            initial["created_by"] = request.user
        return initial

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

