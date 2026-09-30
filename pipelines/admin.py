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



# @admin.register(Customer)
# class CustomerAdmin(admin.ModelAdmin):
#     list_display = ("id", "name", "city", "created_at")
#     search_fields = ("name", "city")
