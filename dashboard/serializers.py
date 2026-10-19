from rest_framework import serializers
from executions.serializers import PipelineExecutionSerializer


class DashboardStatsSerializer(serializers.Serializer):
    """
    Serializer for platform-wide metrics and pipeline health.
    Matches the High-Level Modules: Dashboard & Analytics specification.
    """
    total_pipelines = serializers.IntegerField()
    successful_executions = serializers.IntegerField()
    failed_executions = serializers.IntegerField()
    running_executions = serializers.IntegerField()
    avg_execution_time = serializers.FloatField()
    active_pipelines = serializers.IntegerField()
    disabled_pipelines = serializers.IntegerField()
    failing_pipelines = serializers.IntegerField()
    recent_activities = PipelineExecutionSerializer(many=True, read_only=True)
