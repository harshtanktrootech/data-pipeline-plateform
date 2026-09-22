from rest_framework import serializers
from pipelines.models import Pipeline


class PipelineSerializer(serializers.ModelSerializer):

    class Meta:
        model = Pipeline

        fields = [
            "id",
            "name",
            "description",
            "status",
            "created_by",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_by",
            "created_at",
            "updated_at",
        ]


    def validate_name(self, value):

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Pipeline name cannot be empty."
            )

        if len(value) < 3:
            raise serializers.ValidationError(
                "Pipeline name must contain at least 3 characters."
            )

        return value