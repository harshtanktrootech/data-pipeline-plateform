from celery import shared_task
import logging
from django.contrib.auth.models import User
from pipelines.models import Pipeline
from etl.runner import run_pipeline

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def execute_pipeline_task(self, pipeline_id: int, user_id: int = None):
    """
    Celery background task:
    Executes the ETL pipeline asynchronously via Celery Worker.
    - user_id: ID of the user who manually triggered the run (None if triggered by Celery Beat).
    """
    try:
        pipeline = Pipeline.objects.get(id=pipeline_id, status="active")
    except Pipeline.DoesNotExist:
        logger.warning(f"Pipeline {pipeline_id} not found or inactive. Skipping.")
        return {"status": "SKIPPED", "reason": "Pipeline not found or inactive"}

    triggered_by = None
    if user_id:
        try:
            triggered_by = User.objects.get(id=user_id)
        except User.DoesNotExist:
            triggered_by = None

    trigger_label = triggered_by.username if triggered_by else "Celery Cron"
    logger.info(f"Worker picked up Pipeline '{pipeline.name}' (ID: {pipeline_id}) | Triggered By: {trigger_label}")

    result = run_pipeline(pipeline=pipeline, triggered_by=triggered_by)
    return result

