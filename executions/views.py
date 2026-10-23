from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
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
    Dedicated Execution History page with 4 filters:
    - Pipeline, Status, Triggered By, and Specific Date.
    """
    executions = PipelineExecution.objects.select_related("pipeline", "triggered_by").all()
    
    # 1. Pipeline Filter
    pipeline_id = request.GET.get("pipeline", "").strip()
    if pipeline_id.isdigit():
        executions = executions.filter(pipeline_id=int(pipeline_id))
    
    # 2. Status Filter (SUCCESS, FAILED, RUNNING)
    status_filter = request.GET.get("status", "").strip().upper()
    if status_filter in ["SUCCESS", "FAILED", "RUNNING"]:
        executions = executions.filter(status=status_filter)
    else:
        status_filter = ""
    
    # 3. Triggered By (Specific user OR System/Celery Cron)
    user_id = request.GET.get("user", "").strip()
    if user_id == "system":
        executions = executions.filter(triggered_by__isnull=True)
    elif user_id.isdigit():
        executions = executions.filter(triggered_by_id=int(user_id))
    
    # 4. Date Filter (Specific selected date)
    date_filter = request.GET.get("date", "").strip()
    if date_filter:
        executions = executions.filter(started_at__date=date_filter)
    
    has_running = PipelineExecution.objects.filter(status="RUNNING").exists()
    total_runs = executions.count()

    return render(request, "executions/execution_list.html", {
        "executions": executions[:100],
        "pipelines": Pipeline.objects.all(),
        "users": User.objects.all(),
        "total_runs": total_runs,
        "has_running": has_running,
        "filters": {
            "pipeline": pipeline_id,
            "status": status_filter,
            "user": user_id,
            "date": date_filter,
        }
    })