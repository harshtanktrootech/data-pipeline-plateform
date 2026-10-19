from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from executions.models import PipelineExecution
from executions.serializers import PipelineExecutionSerializer
from pipelines.models import Pipeline


# ── REST API Views ──

class PipelineExecutionListAPIView(generics.ListAPIView):
    """
    GET /api/executions/
    Lists pipeline executions with optional query filters:
      - ?status=SUCCESS / FAILED / RUNNING
      - ?pipeline=<pipeline_id>
    Accessible to all authenticated users (Admin, Operator, Viewer).
    """
    serializer_class = PipelineExecutionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = PipelineExecution.objects.select_related("pipeline", "triggered_by").all()
        
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param.strip().upper())
            
        pipeline_param = self.request.query_params.get("pipeline")
        if pipeline_param and pipeline_param.isdigit():
            queryset = queryset.filter(pipeline_id=int(pipeline_param))
            
        return queryset


class PipelineExecutionDetailAPIView(generics.RetrieveAPIView):
    """
    GET /api/executions/<id>/
    Retrieves full details of a specific execution run.
    """
    queryset = PipelineExecution.objects.select_related("pipeline", "triggered_by").all()
    serializer_class = PipelineExecutionSerializer
    permission_classes = [IsAuthenticated]


# ── Frontend HTML Views ──

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