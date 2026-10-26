import os
import re
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User


def get_available_data_files():
    """Dynamically scan data/ folder and list all CSV files as dropdown choices."""
    data_dir = os.path.join(settings.BASE_DIR, "data")
    choices = [("", "-- Select Dataset --")]

    if os.path.exists(data_dir):
        for file in sorted(os.listdir(data_dir)):
            if file.endswith(".csv"):
                display_name = file.replace(".csv", "").replace("_", " ").title() + f" ({file})"
                file_path = f"data/{file}"
                choices.append((file_path, display_name))
    return choices


class Pipeline(models.Model):

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
    ]

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Name of the pipeline",
    )

    source = models.CharField(
        max_length=200,
        choices=get_available_data_files,
        blank=True,
        default="",
        help_text="Source CSV dataset file",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
        help_text="Current pipeline status",
    )

    description = models.TextField(
        blank=True,
        help_text="Optional pipeline notes/description",
    )

    table_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Target database table name (auto-generates as <name>_data if left blank)",
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="pipelines",
        null=True,
        blank=True,
        help_text="User who created this pipeline",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.table_name and self.name:
            base_name = re.sub(r"[^a-zA-Z0-9_]+", "_", self.name.lower().strip()).strip("_")
            self.table_name = f"{base_name}_data"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name