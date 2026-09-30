from django.db import models
from django.contrib.auth.models import User


class Pipeline(models.Model):

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
    ]

    name = models.CharField(max_length=100, unique=True,)

    description = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="pipelines",
    )
    table_name = models.CharField(max_length=100, blank=True, default="")
    source = models.CharField(max_length=200, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.table_name:
            self.table_name = self.name.lower().replace(" ", "_")
        super().save(*args, **kwargs)