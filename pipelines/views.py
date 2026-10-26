from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import connection
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_celery_beat.models import PeriodicTask

from accounts.permissions import CanManagePipeline
from pipelines.models import Pipeline
from pipelines.serializers import PipelineSerializer
from etl.runner import run_pipeline
from executions.models import PipelineExecution
from pipelines.forms import PipelineCreateForm
from pipelines.services import (
    schedule_pipeline_cron,
    get_pipeline_schedule,
    toggle_pipeline_schedule,
    delete_pipeline_cron,
    calculate_next_run,
    format_next_run_display,
    format_last_run_display,
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
        )


class PipelineDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Pipeline.objects.all()
    serializer_class = PipelineSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [CanManagePipeline()]


class PipelineRunAPIView(APIView):
    """
    POST /api/pipelines/<pk>/run/
    Executes the ETL pipeline immediately via REST API (Admin and Operator only).
    """
    permission_classes = [CanManagePipeline]

    def post(self, request, pk):
        pipeline = get_object_or_404(Pipeline, pk=pk)

        if pipeline.status != "active":
            return Response(
                {"error": f"Cannot execute pipeline '{pipeline.name}': Pipeline is inactive."},
                status=400,
            )

        result = run_pipeline(pipeline, triggered_by=request.user)
        if result["status"] == "SUCCESS":
            status_code = 200
        elif result["status"] == "PARTIALLY_FAILED":
            status_code = 207  # Multi-Status / Partial
        else:
            status_code = 500
        return Response(result, status=status_code)


# ── HTML Page Views (Frontend) ──

@login_required(login_url="/login/")
def pipeline_list_page(request):
    """Lists all pipelines with RBAC actions, last run info, and live schedule status."""
    queryset = Pipeline.objects.select_related("created_by").all().order_by("-created_at")

    # 1. Status Filter (active / inactive)
    status_filter = request.GET.get("status", "").strip().lower()
    if status_filter in ["active", "inactive"]:
        queryset = queryset.filter(status=status_filter)
    else:
        status_filter = ""

    # 2. User Filter (Created By)
    user_id = request.GET.get("user", "").strip()
    if user_id.isdigit():
        queryset = queryset.filter(created_by_id=int(user_id))
    else:
        user_id = ""

    # 3. Date Filter (Specific Created Date)
    date_filter = request.GET.get("date", "").strip()
    if date_filter:
        queryset = queryset.filter(created_at__date=date_filter)

    pipelines = list(queryset)
    total_pipelines = len(pipelines)
    
    # 1. Fetch all scheduled periodic tasks from the DB in a single query
    scheduled_tasks = {
        task.name: task
        for task in PeriodicTask.objects.filter(task="executions.tasks.execute_pipeline_task").select_related("crontab")
    }

    # 2. Fetch the latest execution for each pipeline in a single query
    latest_executions = {}
    if pipelines:
        for execution in PipelineExecution.objects.filter(pipeline__in=pipelines).order_by("started_at"):
            latest_executions[execution.pipeline_id] = execution

    # 3. Attach live schedule object, next run time, and last run info to each pipeline
    for pipeline in pipelines:
        task_name = f"pipeline_cron_run_{pipeline.id}"
        pipeline.schedule_task = scheduled_tasks.get(task_name)
        pipeline.next_run_at = calculate_next_run(pipeline.schedule_task)
        if pipeline.schedule_task and pipeline.schedule_task.enabled and pipeline.status == "active" and pipeline.next_run_at:
            pipeline.next_run_display = format_next_run_display(pipeline.next_run_at)
        else:
            pipeline.next_run_display = "--"

        pipeline.last_execution = latest_executions.get(pipeline.id)
        pipeline.last_run_display = format_last_run_display(pipeline.last_execution)

    return render(
        request,
        "pipelines/pipeline_list.html",
        {
            "pipelines": pipelines,
            "users": User.objects.all(),
            "total_pipelines": total_pipelines,
            "filters": {
                "status": status_filter,
                "user": user_id,
                "date": date_filter,
            },
        },
    )


@login_required(login_url="/login/")
def pipeline_detail_page(request, pk):
    """Displays pipeline details, dynamic DB table preview, execution history, and cron schedule."""
    pipeline = get_object_or_404(Pipeline.objects.select_related("created_by"), pk=pk)
    
    # 1. Check if destination table exists and count total rows loaded
    table_exists = False
    total_db_rows = 0
    if pipeline.table_name:
        try:
            with connection.cursor() as cursor:
                cursor.execute(f'SELECT count(*) FROM "{pipeline.table_name}";')
                total_db_rows = cursor.fetchone()[0]
                table_exists = True
        except Exception:
            table_exists = False
            total_db_rows = 0

    # 2. Fetch the 10 most recent execution runs for this pipeline
    executions = list(pipeline.executions.select_related("triggered_by").all()[:10])
    last_execution = executions[0] if executions else None
    last_run_display = format_last_run_display(last_execution)

    # 3. Fetch current cron schedule for this pipeline
    schedule_task = get_pipeline_schedule(pipeline.id)
    next_run_at = calculate_next_run(schedule_task)
    next_run_display = format_next_run_display(next_run_at) if (schedule_task and schedule_task.enabled and pipeline.status == "active") else "--"
    
    return render(
        request,
        "pipelines/pipeline_details.html",
        {
            "pipeline": pipeline,
            "table_exists": table_exists,
            "total_db_rows": total_db_rows,
            "executions": executions,
            "last_execution": last_execution,
            "last_run_display": last_run_display,
            "schedule_task": schedule_task,
            "next_run_at": next_run_at,
            "next_run_display": next_run_display,
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
                f"Added: {result['records_added']} | Updated: {result['records_updated']} in {result['duration_seconds']}s."
            )
        elif result["status"] == "PARTIALLY_FAILED":
            messages.warning(
                request,
                f"Pipeline '{pipeline.name}' finished with partial failures! "
                f"Added: {result['records_added']} | Updated: {result['records_updated']} | "
                f"Failed: {result['records_failed']} rows. View Audit Log for row-level error breakdown."
            )
        else:
            messages.error(request, f"Pipeline execution failed: {result['error']}")
    
    return redirect("pipeline-detail-page", pk=pk)


@login_required(login_url="/login/")
def schedule_pipeline_view(request, pk):
    """Updates or toggles the cron schedule for a pipeline."""
    pipeline = get_object_or_404(Pipeline, pk=pk)

    if request.method == "POST":
        is_admin = request.user.is_superuser or request.user.groups.filter(name="Admin").exists()
        is_operator = request.user.groups.filter(name="Operator").exists()

        if not (is_admin or is_operator):
            messages.error(request, "Permission Denied: Viewer role cannot configure or modify schedules.")
            return redirect("pipeline-detail-page", pk=pk)

        action = request.POST.get("action")

        if action == "save_schedule":
            frequency = request.POST.get("frequency")
            
            # Map presets to cron expressions
            cron_presets = {
                "every_1_min": {"minute": "*", "hour": "*"},
                "every_5_mins": {"minute": "*/5", "hour": "*"},
                "every_hour": {"minute": "0", "hour": "*"},
                "daily_10am": {"minute": "0", "hour": "10"},
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
                )
                messages.success(request, f"Schedule for '{pipeline.name}' is now {status_text}.")

        elif action == "delete":
            delete_pipeline_cron(pipeline.id)
            log_action(
                request.user,
                "SCHEDULE_DELETE",
                f"Pipeline '{pipeline.name}' (#{pipeline.id})",
                "Removed cron schedule",
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
        )

        status_label = "Activated" if new_status == "active" else "Deactivated"
        messages.success(request, f"Pipeline '{pipeline.name}' has been {status_label.lower()} successfully (Status: {new_status.title()}).")

        next_url = request.POST.get("next")
        if next_url == "pipeline-list-page":
            return redirect("pipeline-list-page")
        return redirect("pipeline-detail-page", pk=pk)

    return redirect("pipeline-detail-page", pk=pk)




