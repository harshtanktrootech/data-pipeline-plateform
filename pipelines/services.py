import json
from django_celery_beat.models import PeriodicTask, CrontabSchedule
from pipelines.models import Pipeline


def validate_pipeline_can_run(pipeline):
    if pipeline.status != "active":
        raise ValueError("Inactive pipeline cannot be executed.")
    return True


def schedule_pipeline_cron(pipeline: Pipeline, minute="0", hour="*", day_of_week="*", day_of_month="*", month_of_year="*"):
    """
    Creates or updates a dynamic cron schedule for a specific Pipeline.
    """
    # 1. Get or create the cron rule in the DB
    crontab, _ = CrontabSchedule.objects.get_or_create(
        minute=minute,
        hour=hour,
        day_of_week=day_of_week,
        day_of_month=day_of_month,
        month_of_year=month_of_year,
    )

    task_name = f"pipeline_cron_run_{pipeline.id}"

    # 2. Create or update the PeriodicTask
    periodic_task, created = PeriodicTask.objects.update_or_create(
        name=task_name,
        defaults={
            "crontab": crontab,
            "task": "executions.tasks.execute_pipeline_task",
            "args": json.dumps([pipeline.id]),
            "enabled": True,
            "description": f"Automated cron execution for pipeline '{pipeline.name}'",
        }
    )
    return periodic_task


def get_pipeline_schedule(pipeline_id: int):
    """Fetches the existing periodic task for this pipeline if any."""
    task_name = f"pipeline_cron_run_{pipeline_id}"
    return PeriodicTask.objects.filter(name=task_name).select_related("crontab").first()


def toggle_pipeline_schedule(pipeline_id: int, enabled: bool):
    """Enables or disables the cron schedule for a pipeline."""
    task_name = f"pipeline_cron_run_{pipeline_id}"
    PeriodicTask.objects.filter(name=task_name).update(enabled=enabled)


def delete_pipeline_cron(pipeline_id: int):
    """Deletes the scheduled periodic task for a pipeline."""
    task_name = f"pipeline_cron_run_{pipeline_id}"
    PeriodicTask.objects.filter(name=task_name).delete()
