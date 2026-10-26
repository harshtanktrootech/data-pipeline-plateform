from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from pipelines.models import Pipeline
from executions.models import PipelineExecution
from dashboard.serializers import DashboardStatsSerializer


def get_dashboard_stats():

    total_pipelines = Pipeline.objects.count()

    exec_stats = PipelineExecution.objects.aggregate(
        successful_executions=Count("id", filter=Q(status="SUCCESS")),
        failed_executions=Count("id", filter=Q(status__in=["FAILED", "PARTIALLY_FAILED"])),
        running_executions=Count("id", filter=Q(status="RUNNING")),
        avg_execution_time=Avg("duration_seconds"),
    )

    active_pipelines = Pipeline.objects.filter(status="active").count()
    disabled_pipelines = Pipeline.objects.filter(status="inactive").count()

    # Failing pipelines: pipelines whose most recent execution status was FAILED or PARTIALLY_FAILED
    failing_pipelines = 0
    all_pipelines = Pipeline.objects.prefetch_related("executions").all()
    for p in all_pipelines:
        latest_run = p.executions.first()
        if latest_run and latest_run.status in ("FAILED", "PARTIALLY_FAILED"):
            failing_pipelines += 1

    recent_activities = PipelineExecution.objects.select_related(
        "pipeline", "triggered_by"
    ).all()[:10]

    return {
        "total_pipelines": total_pipelines,
        "successful_executions": exec_stats["successful_executions"] or 0,
        "failed_executions": exec_stats["failed_executions"] or 0,
        "running_executions": exec_stats["running_executions"] or 0,
        "avg_execution_time": round(exec_stats["avg_execution_time"] or 0.0, 2),
        "active_pipelines": active_pipelines,
        "disabled_pipelines": disabled_pipelines,
        "failing_pipelines": failing_pipelines,
        "recent_activities": recent_activities,
    }


# ── REST API View ──

class DashboardStatsAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        stats = get_dashboard_stats()
        serializer = DashboardStatsSerializer(stats)
        return Response(serializer.data)


# ── Frontend HTML View ──

@login_required
def dashboard_view(request):
    """Renders the HTML Dashboard with KPI cards and pipeline health."""
    context = get_dashboard_stats()
    return render(request, "dashboard/index.html", context)
