import os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import connection
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import CanManagePipeline
from pipelines.models import Pipeline
from pipelines.serializers import PipelineSerializer
from etl.runner import run_pipeline
from pipelines.forms import PipelineCreateForm


# ── REST API Views ──

class PipelineListCreateAPIView(ListCreateAPIView):
    queryset = Pipeline.objects.all()
    serializer_class = PipelineSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [CanManagePipeline()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class PipelineDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Pipeline.objects.all()
    serializer_class = PipelineSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [CanManagePipeline()]


# ── HTML Page Views (Frontend) ──

@login_required(login_url="/admin/login/")
def pipeline_list_page(request):
    """Lists all pipelines with RBAC actions."""
    pipelines = Pipeline.objects.select_related("created_by").all().order_by("-created_at")
    return render(request, "pipelines/pipeline_list.html", {"pipelines": pipelines})


@login_required(login_url="/login/")
def pipeline_detail_page(request, pk):
    """Displays pipeline details, dynamic DB table preview, and execution history."""
    pipeline = get_object_or_404(Pipeline.objects.select_related("created_by"), pk=pk)
    
    # 1. Fetch live data preview from the dynamic DB table
    preview_headers = []
    preview_rows = []
    total_db_rows = 0
    if pipeline.table_name:
        try:
            with connection.cursor() as cursor:
                cursor.execute(f'SELECT count(*) FROM "{pipeline.table_name}";')
                total_db_rows = cursor.fetchone()[0]
                cursor.execute(f'SELECT * FROM "{pipeline.table_name}" LIMIT 5;')
                preview_headers = [col[0] for col in cursor.description]
                preview_rows = cursor.fetchall()
        
        except Exception:
            total_db_rows = 0

    # 2. Fetch the 10 most recent execution runs for this pipeline
    executions = pipeline.executions.select_related("triggered_by").all()[:10]
    
    return render(
        request,
        "pipelines/pipeline_details.html",
        {
            "pipeline": pipeline,
            "preview_headers": preview_headers,
            "preview_rows": preview_rows,
            "total_db_rows": total_db_rows,
            "executions": executions,  # <-- Passed to template!
        },
    )

@login_required(login_url="/login/")
def run_pipeline_page_view(request, pk):
    """Executes the pipeline and records the user who triggered it."""
    pipeline = get_object_or_404(Pipeline, pk=pk)
    
    if request.method == "POST":
        # RBAC Check: Admins and Operators only
        is_admin = request.user.is_superuser or request.user.groups.filter(name="Admin").exists()
        is_operator = request.user.groups.filter(name="Operator").exists()

        if not (is_admin or is_operator):
            messages.error(request, "Permission Denied: Viewer role cannot execute pipelines.")
            return redirect("pipeline-detail-page", pk=pk)
        
        if not os.path.exists(pipeline.source):
            messages.error(request, f"Source file not found at: '{pipeline.source}'")
            return redirect("pipeline-detail-page", pk=pk)
        
        # Pass triggered_by=request.user to attribute the run to the logged-in user
        result = run_pipeline(pipeline, triggered_by=request.user)
        
        if result["status"] == "SUCCESS":
            messages.success(
                request,
                f"Pipeline '{pipeline.name}' executed successfully! "
                f"Extracted: {result['records_extracted']} | "
                f"Loaded: {result['records_loaded']} records in {result['duration_seconds']}s."
            )
        
        else:
            messages.error(request, f"Pipeline execution failed: {result['error']}")
    
    return redirect("pipeline-detail-page", pk=pk)


@login_required(login_url="/login/")
def pipeline_create_page(request):
    """Allows Admins to create a new pipeline with predefined source file selection."""
    # RBAC Check: Only Admin can create pipelines
    is_admin = request.user.is_superuser or request.user.groups.filter(name="Admin").exists()
    
    if not is_admin:
        messages.error(request, "Permission Denied: Only Admins can create new pipelines.")
        return redirect("pipeline-list-page")

    if request.method == "POST":
        form = PipelineCreateForm(request.POST)
        if form.is_valid():
            pipeline = form.save(commit=False)
            pipeline.created_by = request.user

            if not pipeline.table_name:
                base_name = pipeline.name.lower().strip().replace(" ", "_").replace("-", "_")
                pipeline.table_name = f"{base_name}_data"
            pipeline.save()

            messages.success(request, f"Pipeline '{pipeline.name}' created successfully! You can now review and execute it.")
            
            return redirect("pipeline-detail-page", pk=pipeline.pk)


    else:
        form = PipelineCreateForm()
    
    return render(request, "pipelines/pipeline_form.html", {"form": form})

    