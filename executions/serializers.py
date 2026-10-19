from rest_framework import serializers
from executions.models import PipelineExecution


class PipelineExecutionSerializer(serializers.ModelSerializer):
    """
    Serializer for PipelineExecution model.
    Converts execution records to JSON and adds human-friendly fields:
    - pipeline_name: Name of the pipeline executed
    - trigger_label: Username who triggered the run or 'Celery Cron'
    - is_manual: Boolean indicating if it was manually triggered
    """
    pipeline_name = serializers.CharField(source="pipeline.name", read_only=True)
    trigger_label = serializers.CharField(read_only=True)
    is_manual = serializers.BooleanField(read_only=True)

    class Meta:
        model = PipelineExecution
        fields = [
            "id",
            "pipeline",
            "pipeline_name",
            "status",
            "triggered_by",
            "trigger_label",
            "is_manual",
            "records_extracted",
            "records_processed",
            "records_loaded",
            "duration_seconds",
            "error_message",
            "attempts",
            "started_at",
            "completed_at",
        ]
        read_only_fields = [
            "id",
            "started_at",
            "completed_at",
            "duration_seconds",
            "records_extracted",
            "records_processed",
            "records_loaded",
        ]
