from django.contrib.admin import widgets
import os
from django import forms
from django.conf import settings
from pipelines.models import Pipeline


def get_available_data_files():

    # Dynamically scan data/ folder and list all CSV files as dropdown choices
    data_dir = os.path.join(settings.BASE_DIR, "data")
    choices = [("", "-- Select a Predefined Dataset / File --")]

    if os.path.exists(data_dir):
        for file in sorted(os.listdir(data_dir)):
            if file.endwith(".csv"):
                display_name = file.replace(".csv, ").replace("_", " ").title() + f" (data/{file})"
                file_path = f"data/{file}"
                choices.append((file_path, display_name))
    return choices


class PipelineCreateForm(forms.ModelForm):
    source = forms.ChoiceField(
        choices=get_available_data_files,
        widget=forms.Select(attrs={"class": "form-select", "id": "id_source"}),
        help_text="Select one of the predefined dataset files in data/ directory.",
    )
    
    class Meta:
        model = Pipeline
        fields = ["name", "source", "description", "status"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., Student Admissions Pipeline",
                "id": "id_name",
            }),

            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Enter pipeline purpose, scheduale details, or source notes...",
                "id": "id_description",
            }),

            "source": forms.Select(attrs={
                "class": "form-select",
                "id": "id_source",
            }),

            "status": forms.Select(attrs={
                "class": "form-select",
                "id": "id_status",
            }),
        }

    def clean_source(self):
        source = self.cleaned_data.get("source")
        if not source:
            raise forms.ValidationError("Please select a valid dataset file from the dropdoun.")
        return source
