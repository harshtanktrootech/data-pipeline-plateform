import time
from django.utils import timezone
from etl.extractor import extract_data
from etl.transformer import transform_data
from etl.loader import load_data
from pipelines.models import Pipeline
from executions.models import PipelineExecution
from audit.services import log_action


def run_pipeline(pipeline: Pipeline, triggered_by=None, max_retries=3):
    """
    Main ETL Pipeline Runner:
    Coordinates the 3 stages:
      1. EXTRACT  : Reads CSV file into a DataFrame.
      2. TRANSFORM: Cleans column names and normalizes cell values.
      3. LOAD     : Inserts clean records into PostgreSQL table.

    Also records execution history and audit log in the database.
    """
    start_time = time.time()
    started_at = timezone.now()
    trigger_type = f"Manual ({triggered_by.username})" if triggered_by else "Automated Celery Cron"

    status = "FAILED"
    error_summary = None
    total_extracted = 0
    records_added = 0
    records_failed = 0
    all_failed_rows = []
    success_rows = []

    attempt = 0
    while attempt < max_retries:
        attempt += 1
        try:
            # --------------------------------------------------
            # Step 1: EXTRACT
            # --------------------------------------------------
            raw_data = extract_data(pipeline.source)
            total_extracted = len(raw_data)

            # --------------------------------------------------
            # Step 2: TRANSFORM
            # --------------------------------------------------
            valid_records, transform_failed = transform_data(raw_data)

            # --------------------------------------------------
            # Step 3: LOAD
            # --------------------------------------------------
            load_result = load_data(valid_records, table_name=pipeline.table_name)

            records_added = load_result["records_added"]
            success_rows = load_result["success_rows"]
            all_failed_rows = transform_failed + load_result["failed_rows"]
            records_failed = len(all_failed_rows)

            # Determine execution outcome status
            if records_failed == 0 and records_added > 0:
                status = "SUCCESS"
            elif records_failed > 0 and records_added > 0:
                status = "PARTIALLY_FAILED"
            else:
                status = "FAILED"

            if all_failed_rows:
                sample_errors = [f"Row {r['row_number']}: {r['error']}" for r in all_failed_rows[:3]]
                error_summary = "; ".join(sample_errors)

            # Success, exit retry loop
            break

        except Exception as e:
            error_summary = str(e)
            all_failed_rows = [{"row_number": 0, "data": {}, "error": str(e)}]
            records_failed = 1
            status = "FAILED"

            # Do not retry on missing or invalid files
            if isinstance(e, (FileNotFoundError, ValueError)):
                break

            time.sleep(0.5)

    duration = round(time.time() - start_time, 4)
    completed_at = timezone.now()

    error_details = {
        "status": status,
        "total_extracted": total_extracted,
        "records_added": records_added,
        "records_updated": 0,
        "records_failed": records_failed,
        "failed_rows": all_failed_rows,
        "success_rows": success_rows,
        "error": error_summary,
    }

    # --------------------------------------------------
    # Step 4: Record Execution History in Database
    # --------------------------------------------------
    execution = PipelineExecution.objects.create(
        pipeline=pipeline,
        status=status,
        triggered_by=triggered_by,
        records_extracted=total_extracted,
        records_processed=records_added,
        records_loaded=records_added,
        records_added=records_added,
        records_updated=0,
        records_failed=records_failed,
        duration_seconds=duration,
        attempts=attempt,
        error_message=error_summary,
        error_details=error_details,
        started_at=started_at,
        completed_at=completed_at,
    )

    # --------------------------------------------------
    # Step 5: Save Audit Log Entry
    # --------------------------------------------------
    details_str = (
        f"Status: {status}, Extracted: {total_extracted}, "
        f"Added: {records_added}, Failed: {records_failed} rows in {duration}s via {trigger_type}"
    )

    log_action(
        user=triggered_by,
        action="PIPELINE_RUN",
        resource=f"Pipeline '{pipeline.name}' (#{pipeline.id})",
        details=details_str,
        status=status,
        records_added=records_added,
        records_updated=0,
        records_failed=records_failed,
        error_details=error_details,
        execution=execution,
    )

    return {
        "status": status,
        "records_extracted": total_extracted,
        "records_processed": records_added,
        "records_loaded": records_added,
        "records_added": records_added,
        "records_updated": 0,
        "records_failed": records_failed,
        "failed_rows": all_failed_rows,
        "duration_seconds": duration,
        "attempts": attempt,
        "execution_id": execution.id,
        "error": error_summary,
    }

