from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Q

from pipelines.models import Pipeline
from executions.models import PipelineExecution


@login_required
def dashboard_view(request):
    """
    Display high-level pipeline metrics:
    - Total pipelines
    - Successful executions
    - Failed executions
    - Running pipelines
    - Average execution time
    - Recent pipeline activities
    """
    # 1. Total pipelines
    total_pipelines = Pipeline.objects.count()

    # 2. Executions breakdown & Average runtime
    exec_stats = PipelineExecution.objects.aggregate(
        successful_executions=Count("id", filter=Q(status="SUCCESS")),
        failed_executions=Count("id", filter=Q(status="FAILED")),
        running_executions=Count("id", filter=Q(status="RUNNING")),
        avg_execution_time=Avg("duration_seconds"),
    )

    # 3. Recent pipeline activities (latest execution runs)
    recent_activities = PipelineExecution.objects.select_related(
        "pipeline", "triggered_by"
    ).all()[:10]

    context = {
        "total_pipelines": total_pipelines,
        "successful_executions": exec_stats["successful_executions"] or 0,
        "failed_executions": exec_stats["failed_executions"] or 0,
        "running_executions": exec_stats["running_executions"] or 0,
        "avg_execution_time": round(exec_stats["avg_execution_time"] or 0.0, 2),
        "recent_activities": recent_activities,
    }

    return render(request, "dashboard/index.html", context)
