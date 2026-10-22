from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from executions.models import PipelineExecution
from executions.serializers import PipelineExecutionSerializer
from pipelines.models import Pipeline

from datetime import datetime
from django.contrib.auth.models import User

# ── REST API Views ──l

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

    executions = PipelineExecution.objects.select_related("pipeline", "triggered_by").all()
    
    # 1. Status Filter (SUCCESS, FAILED, RUNNING)
    status_filter = request.GET.get("status", "").strip().upper()
    if status_filter in ["SUCCESS", "FAILED", "RUNNING"]:
        executions = executions.filter(status=status_filter)
    
    # 2. Pipeline Filter
    pipeline_id = request.GET.get("pipeline", "").strip()
    if pipeline_id.isdigit():
        executions = executions.filter(pipeline_id=int(pipeline_id))
    
    # 3. User Filter (Specific user OR System/Celery Cron)
    user_id = request.GET.get("user", "").strip()
    
    if user_id == "system":
        executions = executions.filter(triggered_by__isnull=True)
    
    elif user_id.isdigit():
        executions = executions.filter(triggered_by_id=int(user_id))
    
    # 4. Date-wise Filter (e.g., 2026-10-20 to 2026-10-22)
    start_date = request.GET.get("start_date", "").strip()
    end_date = request.GET.get("end_date", "").strip()
    
    if start_date:
        executions = executions.filter(started_at__date__gte=start_date)
    if end_date:
        executions = executions.filter(started_at__date__lte=end_date)
    
    # 5. Time-wise Filter (e.g., 09:00 to 11:00 regardless of date, or within dates)
    start_time = request.GET.get("start_time", "").strip()  # Format: "09:00"
    end_time = request.GET.get("end_time", "").strip()      # Format: "11:00"
    
    if start_time:
        executions = executions.filter(started_at__time__gte=start_time)
    if end_time:
        executions = executions.filter(started_at__time__lte=end_time)
    
    return render(request, "executions/execution_list.html", {
        "executions": executions[:100],
        "pipelines": Pipeline.objects.all(),
        "users": User.objects.all(),
        "filters": {
            "status": status_filter,
            "pipeline": pipeline_id,
            "user": user_id,
            "start_date": start_date,
            "end_date": end_date,
            "start_time": start_time,
            "end_time": end_time,
        }
    })