import time
from django.utils import timezone
from etl.extractor import extract_data
from etl.transformer import transform_data
from etl.loader import load_data
from pipelines.models import Pipeline
from executions.models import PipelineExecution


from audit.services import log_action


def run_pipeline(pipeline: Pipeline, triggered_by=None, source_type=None, max_retries=3):
    """
    Executes the ETL pipeline and automatically persists
    an Execution History record and Audit Log in the database.
    """
    attempt = 0
    start_time = time.time()
    started_at = timezone.now()

    while attempt < max_retries:
        attempt += 1

        try:
            # 1. Extract
            raw_data = extract_data(pipeline.source, source_type)

            # 2. Transform
            clean_data = transform_data(raw_data)
             
            # 3. Load dynamically into database table
            records_loaded = load_data(clean_data, table_name=pipeline.table_name)

            duration = round(time.time() - start_time, 4)
            completed_at = timezone.now()

            # 4. Save SUCCESS Execution in DB
            execution = PipelineExecution.objects.create(
                pipeline=pipeline,
                status="SUCCESS",
                triggered_by=triggered_by,
                records_extracted=raw_data.shape[0],
                records_processed=len(clean_data),
                records_loaded=records_loaded,
                duration_seconds=duration,
                attempts=attempt,
                started_at=started_at,
                completed_at=completed_at,
            )

            # 5. Save Audit Log
            trigger_type = f"Manual ({triggered_by.username})" if triggered_by else "Automated Celery Cron"
            log_action(
                user=triggered_by,
                action="PIPELINE_RUN",
                resource=f"Pipeline '{pipeline.name}' (#{pipeline.id})",
                details=f"Status: SUCCESS, Extracted: {raw_data.shape[0]}, Loaded: {records_loaded} rows in {duration}s via {trigger_type}",
            )

            return {
                "status": "SUCCESS",
                "records_extracted": raw_data.shape[0],
                "records_processed": len(clean_data),
                "records_loaded": records_loaded,
                "duration_seconds": duration,
                "attempts": attempt,
                "execution_id": execution.id,
                "error": None,
            }

        except Exception as e:
            if attempt >= max_retries:
                duration = round(time.time() - start_time, 4)
                completed_at = timezone.now()

                # Save FAILED Execution in DB
                execution = PipelineExecution.objects.create(
                    pipeline=pipeline,
                    status="FAILED",
                    triggered_by=triggered_by,
                    records_extracted=0,
                    records_processed=0,
                    records_loaded=0,
                    duration_seconds=duration,
                    attempts=attempt,
                    error_message=str(e),
                    started_at=started_at,
                    completed_at=completed_at,
                )

                # Save Audit Log for Failure
                trigger_type = f"Manual ({triggered_by.username})" if triggered_by else "Automated Celery Cron"
                log_action(
                    user=triggered_by,
                    action="PIPELINE_RUN",
                    resource=f"Pipeline '{pipeline.name}' (#{pipeline.id})",
                    details=f"Status: FAILED, Error: {str(e)} via {trigger_type}",
                )

                return {
                    "status": "FAILED",
                    "records_extracted": 0,
                    "records_processed": 0,
                    "records_loaded": 0,
                    "duration_seconds": duration,
                    "attempts": attempt,
                    "execution_id": execution.id,
                    "error": str(e),
                }
            time.sleep(0.5)
