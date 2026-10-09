import os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import connection
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from django_celery_beat.models import PeriodicTask

from accounts.permissions import CanManagePipeline
from pipelines.models import Pipeline
from pipelines.serializers import PipelineSerializer
from etl.runner import run_pipeline
from pipelines.forms import PipelineCreateForm
from pipelines.services import (
    schedule_pipeline_cron,
    get_pipeline_schedule,
    toggle_pipeline_schedule,
    delete_pipeline_cron,
)
from audit.services import log_action


# ── REST API Views ──

class PipelineListCreateAPIView(ListCreateAPIView):
    queryset = Pipeline.objects.all()
    serializer_class = PipelineSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [CanManagePipeline()]

    def perform_create(self, serializer):
        pipeline = serializer.save(created_by=self.request.user)
        log_action(
            self.request.user,
            "PIPELINE_CREATE",
            f"Pipeline '{pipeline.name}' (#{pipeline.id})",
            "Created via REST API",
            self.request
        )


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
    """Lists all pipelines with RBAC actions and their live schedule status."""
    pipelines = list(Pipeline.objects.select_related("created_by").all().order_by("-created_at"))
    
    # 1. Fetch all scheduled periodic tasks from the DB in a single query
    scheduled_tasks = {
        task.name: task
        for task in PeriodicTask.objects.filter(task="executions.tasks.execute_pipeline_task").select_related("crontab")
    }

    # 2. Attach live schedule object to each pipeline
    for pipeline in pipelines:
        task_name = f"pipeline_cron_run_{pipeline.id}"
        pipeline.schedule_task = scheduled_tasks.get(task_name)

    return render(request, "pipelines/pipeline_list.html", {"pipelines": pipelines})


@login_required(login_url="/login/")
def pipeline_detail_page(request, pk):
    """Displays pipeline details, dynamic DB table preview, execution history, and cron schedule."""
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

    # 3. Fetch current cron schedule for this pipeline
    schedule_task = get_pipeline_schedule(pipeline.id)
    
    return render(
        request,
        "pipelines/pipeline_details.html",
        {
            "pipeline": pipeline,
            "preview_headers": preview_headers,
            "preview_rows": preview_rows,
            "total_db_rows": total_db_rows,
            "executions": executions,
            "schedule_task": schedule_task,
        },
    )


@login_required(login_url="/login/")
def run_pipeline_page_view(request, pk):
    """Executes the pipeline on-demand and records the user who triggered it."""
    pipeline = get_object_or_404(Pipeline, pk=pk)
    
    if request.method == "POST":
        is_admin = request.user.is_superuser or request.user.groups.filter(name="Admin").exists()
        is_operator = request.user.groups.filter(name="Operator").exists()

        if not (is_admin or is_operator):
            messages.error(request, "Permission Denied: Viewer role cannot execute pipelines.")
            return redirect("pipeline-detail-page", pk=pk)
        
        if pipeline.status != "active":
            messages.error(request, f"Cannot execute pipeline '{pipeline.name}': Pipeline is inactive. Please activate it first.")
            return redirect("pipeline-detail-page", pk=pk)
        
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
def schedule_pipeline_view(request, pk):
    """Updates or toggles the cron schedule for a pipeline."""
    pipeline = get_object_or_404(Pipeline, pk=pk)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "save_schedule":
            frequency = request.POST.get("frequency")
            
            # Map presets to cron expressions
            cron_presets = {
                "every_1_min": {"minute": "*", "hour": "*"},
                "every_5_mins": {"minute": "*/5", "hour": "*"},
                "every_hour": {"minute": "0", "hour": "*"},
                "daily_midnight": {"minute": "0", "hour": "0"},
                "weekly_monday": {"minute": "0", "hour": "9", "day_of_week": "mon"},
            }

            if frequency in cron_presets:
                schedule_pipeline_cron(pipeline, **cron_presets[frequency])
                log_action(
                    request.user,
                    "SCHEDULE_UPDATE",
                    f"Pipeline '{pipeline.name}' (#{pipeline.id})",
                    f"Cron frequency set to: '{frequency}'",
                    request
                )
                messages.success(request, f"Cron schedule updated successfully for '{pipeline.name}'!")
            else:
                messages.error(request, "Invalid schedule preset selected.")

        elif action == "toggle":
            task = get_pipeline_schedule(pipeline.id)
            if task:
                new_state = not task.enabled
                toggle_pipeline_schedule(pipeline.id, new_state)
                status_text = "Enabled" if new_state else "Paused"
                log_action(
                    request.user,
                    "SCHEDULE_TOGGLE",
                    f"Pipeline '{pipeline.name}' (#{pipeline.id})",
                    f"Schedule state changed to: {status_text}",
                    request
                )
                messages.success(request, f"Schedule for '{pipeline.name}' is now {status_text}.")

        elif action == "delete":
            delete_pipeline_cron(pipeline.id)
            log_action(
                request.user,
                "SCHEDULE_DELETE",
                f"Pipeline '{pipeline.name}' (#{pipeline.id})",
                "Removed cron schedule",
                request
            )
            messages.info(request, f"Schedule removed for '{pipeline.name}'.")

    return redirect("pipeline-detail-page", pk=pk)


@login_required(login_url="/login/")
def pipeline_create_page(request):
    """Allows Admins to create a new pipeline with predefined source file selection."""
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

            log_action(
                request.user,
                "PIPELINE_CREATE",
                f"Pipeline '{pipeline.name}' (#{pipeline.pk})",
                f"Source: {pipeline.source}, Table: {pipeline.table_name}",
                request
            )

            messages.success(request, f"Pipeline '{pipeline.name}' created successfully! You can now review and execute it.")
            return redirect("pipeline-detail-page", pk=pipeline.pk)
    else:
        form = PipelineCreateForm()
    
    return render(request, "pipelines/pipeline_form.html", {"form": form})



@login_required(login_url="/login/")
def pipeline_edit_page(request, pk):
    """Allows Admins to edit an existing pipeline and logs changes to Audit Log."""
    pipeline = get_object_or_404(Pipeline, pk=pk)

    # 1. RBAC Check: Only Admin can edit pipelines
    is_admin = request.user.is_superuser or request.user.groups.filter(name="Admin").exists()
    if not is_admin:
        messages.error(request, "Permission Denied: Only Admins can edit pipelines.")
        return redirect("pipeline-detail-page", pk=pk)

    if request.method == "POST":
        # Keep track of old values to record in Audit Log
        old_name = pipeline.name
        old_source = pipeline.source
        old_table = pipeline.table_name
        old_status = pipeline.status

        form = PipelineCreateForm(request.POST, instance=pipeline)
        if form.is_valid():
            updated_pipeline = form.save()

            # Record what changed for Audit Trail
            changes = []
            if old_name != updated_pipeline.name:
                changes.append(f"Name: '{old_name}' → '{updated_pipeline.name}'")
            if old_source != updated_pipeline.source:
                changes.append(f"Source: '{old_source}' → '{updated_pipeline.source}'")
            if old_table != updated_pipeline.table_name:
                changes.append(f"Table: '{old_table}' → '{updated_pipeline.table_name}'")
            if old_status != updated_pipeline.status:
                changes.append(f"Status: '{old_status}' → '{updated_pipeline.status}'")

            change_summary = ", ".join(changes) if changes else "Updated metadata/description"

            # 2. Save Audit Log
            log_action(
                request.user,
                "PIPELINE_UPDATE",
                f"Pipeline '{updated_pipeline.name}' (#{updated_pipeline.id})",
                change_summary,
                request
            )

            messages.success(request, f"Pipeline '{updated_pipeline.name}' updated successfully!")
            return redirect("pipeline-detail-page", pk=updated_pipeline.pk)
    else:
        form = PipelineCreateForm(instance=pipeline)

    return render(
        request,
        "pipelines/pipeline_form.html",
        {
            "form": form,
            "pipeline": pipeline,
            "is_edit": True,  # Flags template that we are editing
        }
    )


@login_required(login_url="/login/")
def pipeline_delete_page(request, pk):
    """Allows Admins to delete a pipeline, cleans up Celery Beat schedules, and logs audit action."""
    pipeline = get_object_or_404(Pipeline, pk=pk)

    # 1. RBAC Check: Only Admin can delete pipelines
    is_admin = request.user.is_superuser or request.user.groups.filter(name="Admin").exists()
    if not is_admin:
        messages.error(request, "Permission Denied: Only Admins can delete pipelines.")
        return redirect("pipeline-detail-page", pk=pk)

    if request.method == "POST":
        pipeline_name = pipeline.name
        pipeline_id = pipeline.id

        # Clean up any scheduled cron job in Celery Beat
        delete_pipeline_cron(pipeline_id)

        # Delete the pipeline (executions cascade delete automatically)
        pipeline.delete()

        # Record Audit Log
        log_action(
            request.user,
            "PIPELINE_DELETE",
            f"Pipeline '{pipeline_name}' (#{pipeline_id})",
            "Deleted pipeline and associated cron schedules",
            request
        )

        messages.success(request, f"Pipeline '{pipeline_name}' has been deleted successfully.")
        return redirect("pipeline-list-page")

    return redirect("pipeline-detail-page", pk=pk)


@login_required(login_url="/login/")
def pipeline_toggle_status_page(request, pk):
    """Allows Admins to quickly toggle a pipeline between active and inactive status."""
    pipeline = get_object_or_404(Pipeline, pk=pk)

    # 1. RBAC Check: Only Admin can toggle pipeline status
    is_admin = request.user.is_superuser or request.user.groups.filter(name="Admin").exists()
    if not is_admin:
        messages.error(request, "Permission Denied: Only Admins can change pipeline status.")
        return redirect("pipeline-detail-page", pk=pk)

    if request.method == "POST":
        old_status = pipeline.status
        new_status = "inactive" if old_status == "active" else "active"
        pipeline.status = new_status
        pipeline.save()

        # Record Audit Log
        log_action(
            request.user,
            "PIPELINE_STATUS_CHANGE",
            f"Pipeline '{pipeline.name}' (#{pipeline.id})",
            f"Status changed from '{old_status.upper()}' to '{new_status.upper()}'",
            request,
        )

        status_label = "Activated" if new_status == "active" else "Deactivated"
        messages.success(request, f"Pipeline '{pipeline.name}' has been {status_label.lower()} successfully (Status: {new_status.title()}).")

        next_url = request.POST.get("next")
        if next_url == "pipeline-list-page":
            return redirect("pipeline-list-page")
        return redirect("pipeline-detail-page", pk=pk)

    return redirect("pipeline-detail-page", pk=pk)


