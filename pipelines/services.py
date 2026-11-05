import json
from django_celery_beat.models import PeriodicTask, CrontabSchedule
from pipelines.models import Pipeline
from django.conf import settings
from django.utils import timezone
import datetime


def schedule_pipeline_cron(pipeline: Pipeline, minute="0", hour="*", day_of_week="*", day_of_month="*", month_of_year="*"):
    """
    Creates or updates a dynamic cron schedule for a specific Pipeline.
    """
    tz = getattr(settings, "TIME_ZONE", "Asia/Kolkata")

    # 1. Get or create the cron rule in the DB with matching timezone
    crontab, created = CrontabSchedule.objects.get_or_create(
        minute=minute,
        hour=hour,
        day_of_week=day_of_week,
        day_of_month=day_of_month,
        month_of_year=month_of_year,
        timezone=tz,
    )
    if not created and str(crontab.timezone) != str(tz):
        crontab.timezone = tz
        crontab.save(update_fields=["timezone"])

    task_name = f"pipeline_cron_run_{pipeline.id}"

    # 2. Create or update the PeriodicTask
    periodic_task, _ = PeriodicTask.objects.update_or_create(
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


def calculate_next_run(periodic_task):
    """
    Calculates the exact upcoming execution datetime for a PeriodicTask.
    Uses the task schedule's timezone-aware now() and aligns to the top of the target minute boundary,
    preventing microsecond truncation from displaying the current minute instead of the next run.
    """
    if not periodic_task or not periodic_task.enabled:
        return None
    
    try:
        s = periodic_task.schedule
        now = s.now() if hasattr(s, "now") else timezone.now()
        rem_delta = s.remaining_estimate(now)

        # Celery's remaining_estimate calculates delta to the tail end of the interval (:59.999).
        # We add 1 second and clear microseconds to align with the top of the upcoming minute (e.g. 14:15:00 instead of 14:14:59).
        next_run = (now + rem_delta + datetime.timedelta(seconds=1)).replace(microsecond=0)
        return next_run
    except Exception:
        return None


def format_next_run_display(next_run_at):
    """
    Formats the estimated next execution datetime into a clean, human-friendly string matching Photo 9
    e.g. '11:00 AM', 'Tomorrow 10:00 AM', '--'.
    """
    if not next_run_at:
        return "--"
    
    try:
        local_next = timezone.localtime(next_run_at)
        local_today = timezone.localtime(timezone.now()).date()
        if local_next.date() == local_today:
            return local_next.strftime("%I:%M %p")
        elif local_next.date() == local_today + datetime.timedelta(days=1):
            return f"Tomorrow {local_next.strftime('%I:%M %p')}"
        else:
            return local_next.strftime("%a, %d %b %I:%M %p")
    except Exception:
        return "--"


def format_schedule_display(schedule_task):
    """
    Returns the simple dropdown option name for a pipeline schedule.
    Cron star patterns are kept in comments for easy understanding.
    """
    if not schedule_task or not getattr(schedule_task, "crontab", None):
        return "--"

    minute = str(schedule_task.crontab.minute).strip()
    hour = str(schedule_task.crontab.hour).strip()

    # Option 1: Every 1 Minute (* * * * *)
    if minute == "*" and hour == "*":
        return "Every 1 Minute"

    # Option 2: Every 5 Minutes (*/5 * * * *)
    if minute == "*/5" and hour == "*":
        return "Every 5 Minutes"

    # Option 3: Every Hour (0 * * * *)
    if minute == "0" and hour == "*":
        return "Every Hour"

    # Option 4: Every Day at 10:00 AM (0 10 * * *)
    if minute == "0" and hour == "10":
        return "Every Day at 10:00 AM"

    # Option 5: Every Day at Midnight (0 0 * * *)
    if minute == "0" and hour == "0":
        return "Every Day at Midnight"

    # Option 6: Weekly on Monday at 9:00 AM (0 9 * * mon)
    if minute == "0" and hour == "9":
        return "Weekly on Monday at 9:00 AM"

    return "Custom Schedule"


def format_last_run_display(last_execution):
    """
    Formats the last execution datetime into a clean string (e.g. '02:41 PM', 'Yesterday 03:15 PM', '15 Oct, 09:53 AM').
    """
    if not last_execution or not last_execution.started_at:
        return "--"

    try:
        local_time = timezone.localtime(last_execution.started_at)
        local_today = timezone.localtime(timezone.now()).date()
        if local_time.date() == local_today:
            return local_time.strftime("%I:%M %p")
        elif local_time.date() == local_today - datetime.timedelta(days=1):
            return f"Yesterday {local_time.strftime('%I:%M %p')}"
        else:
            return local_time.strftime("%d %b, %I:%M %p")
    except Exception:
        return "--"



