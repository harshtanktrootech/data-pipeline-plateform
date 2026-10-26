import os
from django import forms
from django.conf import settings
from pipelines.models import Pipeline, get_available_data_files


class PipelineCreateForm(forms.ModelForm):
    source = forms.ChoiceField(
        choices=get_available_data_files,
        widget=forms.Select(attrs={
            "class": "form-select",
            "id": "id_source",
        }),
    )

    table_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control font-monospace",
            "placeholder": "e.g. students_data",
            "id": "id_table_name",
        }),
    )

    status = forms.ChoiceField(
        choices=Pipeline.STATUS_CHOICES,
        widget=forms.Select(attrs={
            "class": "form-select",
            "id": "id_status",
        }),
        initial="active",
    )

    class Meta:
        model = Pipeline
        fields = ["name", "source", "status", "description", "table_name"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. Student Pipeline",
                "id": "id_name",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Optional pipeline notes...",
                "id": "id_description",
            }),
        }

    def clean_source(self):
        source = self.cleaned_data.get("source")
        if not source:
            raise forms.ValidationError("Please select a valid dataset file from the dropdown.")
        return source
