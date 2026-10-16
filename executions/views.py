from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from executions.models import PipelineExecution
from pipelines.models import Pipeline


@login_required(login_url="/login/")
def execution_history_page(request):
    """
    Dedicated Execution History page answering: 'What happened when my pipelines ran?'
    Displays execution status, duration, start timestamp, record counts, and errors.
    """
    status_filter = request.GET.get("status", "").strip().upper()
    pipeline_id = request.GET.get("pipeline", "").strip()

    executions = PipelineExecution.objects.select_related("pipeline", "triggered_by").all()

    if status_filter in ["SUCCESS", "FAILED", "RUNNING"]:
        executions = executions.filter(status=status_filter)
    else:
        status_filter = ""

    if pipeline_id.isdigit():
        executions = executions.filter(pipeline_id=int(pipeline_id))
    else:
        pipeline_id = ""

    has_running = PipelineExecution.objects.filter(status="RUNNING").exists()

    return render(
        request,
        "executions/execution_list.html",
        {
            "executions": executions[:100],
            "status_filter": status_filter,
            "pipeline_id": pipeline_id,
            "pipelines": Pipeline.objects.all(),
            "total_runs": executions.count(),
            "has_running": has_running,
        },
    )
