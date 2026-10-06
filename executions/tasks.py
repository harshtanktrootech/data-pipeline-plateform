from celery import shared_task
import logging
from pipelines.models import Pipeline
from etl.runner import run_pipeline

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def execute_pipeline_task(self, pipeline_id: int):
    """
    Celery task that loads the pipeline and executes the ETL process.
    """
    try:
        pipeline = Pipeline.objects.get(id=pipeline_id, status='active')
    except Pipeline.DoesNotExist:
        logger.warning(f"Pipeline {pipeline_id} not found or inactive. Skipping.")
        return {"status": "SKIPPED", "reason": "Pipeline not found or inactive"}

    logger.info(f"Starting scheduled execution for pipeline: {pipeline.name} (ID: {pipeline_id})")
    
    result = run_pipeline(pipeline=pipeline, triggered_by=None)
    return result
