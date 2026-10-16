from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Q

from pipelines.models import Pipeline
from executions.models import PipelineExecution


@login_required
def dashboard_view(request):
    """
    Display high-level pipeline metrics and pipeline health:
    - Total pipelines
    - Successful executions
    - Failed executions
    - Running pipelines
    - Average execution time
    - Recent pipeline activities
    - Pipeline Health (Active, Failed, Disabled) as shown in Photo 4
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

    # 3. Pipeline Health (Photo 4: Active, Failed, Disabled)
    active_pipelines = Pipeline.objects.filter(status="active").count()
    disabled_pipelines = Pipeline.objects.filter(status="inactive").count()

    # Failing pipelines: pipelines whose most recent execution status was FAILED
    failing_pipelines = 0
    all_pipelines = Pipeline.objects.prefetch_related("executions").all()
    for p in all_pipelines:
        latest_run = p.executions.first()
        if latest_run and latest_run.status == "FAILED":
            failing_pipelines += 1

    # 4. Recent pipeline activities (latest execution runs)
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
        # Pipeline Health
        "active_pipelines": active_pipelines,
        "disabled_pipelines": disabled_pipelines,
        "failing_pipelines": failing_pipelines,
    }

    return render(request, "dashboard/index.html", context)
