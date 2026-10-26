from django import forms
from django.contrib import admin
from pipelines.models import Pipeline, get_available_data_files


class PipelineAdminForm(forms.ModelForm):
    source = forms.ChoiceField(
        choices=get_available_data_files,
        required=True,
        help_text="Please select a valid dataset file from the dropdown.",
    )

    class Meta:
        model = Pipeline
        fields = "__all__"

    def clean_source(self):
        source = self.cleaned_data.get("source")
        if not source:
            raise forms.ValidationError("Please select a valid dataset file from the dropdown.")
        return source


@admin.register(Pipeline)
class PipelineAdmin(admin.ModelAdmin):
    form = PipelineAdminForm
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
