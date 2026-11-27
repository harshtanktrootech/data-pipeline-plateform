from unittest.mock import patch
from executions.models import PipelineExecution
from executions.tasks import execute_pipeline_task
from etl.runner import run_pipeline
from audit.models import AuditLog


# 1. Celery Task: Skips Inactive Pipeline (No mocking needed)

def test_task_skips_inactive(sample_pipeline):
    """Celery task skips execution if the pipeline is inactive."""
    sample_pipeline.status = "inactive"
    sample_pipeline.save()

    result = execute_pipeline_task(sample_pipeline.id)

    assert result["status"] == "SKIPPED"
    assert "inactive" in result["reason"].lower()



# 2. Celery Task: Mocking with unittest.mock.patch

def test_task_runs_pipeline(sample_pipeline, operator_user):
    """
    Use @patch / with patch() when you want to verify:
      - A function was called with the exact expected arguments
      - Without actually reading CSVs or writing PostgreSQL tables
    """
    fake_result = {"status": "SUCCESS", "records_added": 10}

    with patch("executions.tasks.run_pipeline", return_value=fake_result) as mock_run:
        result = execute_pipeline_task(sample_pipeline.id, user_id=operator_user.id)

    assert result == fake_result
    mock_run.assert_called_once_with(pipeline=sample_pipeline, triggered_by=operator_user)



# 3. ETL Runner: Mocking with Pytest's built-in 'monkeypatch' fixture

def test_run_pipeline_success(monkeypatch, sample_pipeline, operator_user):
    """
    Replace extract_data, transform_data, and load_data with lightweight fake functions
    using monkeypatch, then verify PipelineExecution and AuditLog are saved.
    """
    fake_rows = [{"name": "Alice"}, {"name": "Bob"}]

    monkeypatch.setattr("etl.runner.extract_data", lambda source: (fake_rows, []))
    monkeypatch.setattr("etl.runner.transform_data", lambda df: (fake_rows, []))
    monkeypatch.setattr(
        "etl.runner.load_data",
        lambda records, table_name: {
            "records_added": 2,
            "success_rows": records,
            "failed_rows": [],
        },
    )

    result = run_pipeline(sample_pipeline, triggered_by=operator_user)

    assert result["status"] == "SUCCESS"
    assert result["records_added"] == 2
    assert PipelineExecution.objects.filter(pipeline=sample_pipeline, status="SUCCESS").exists()
    assert AuditLog.objects.filter(action="PIPELINE_RUN", status="SUCCESS").exists()



# 4. ETL Runner: PARTIALLY_FAILED outcome

def test_run_pipeline_partial_fail(monkeypatch, sample_pipeline, operator_user):
    """If some rows fail and some succeed, status becomes PARTIALLY_FAILED."""
    extract_errors = [{"row_number": 3, "data": {}, "error": "Wrong column count"}]

    monkeypatch.setattr("etl.runner.extract_data", lambda source: ([{"name": "Alice"}], extract_errors))
    monkeypatch.setattr("etl.runner.transform_data", lambda df: ([{"name": "Alice"}], []))
    monkeypatch.setattr(
        "etl.runner.load_data",
        lambda records, table_name: {
            "records_added": 1,
            "success_rows": records,
            "failed_rows": [],
        },
    )

    result = run_pipeline(sample_pipeline, triggered_by=operator_user)

    assert result["status"] == "PARTIALLY_FAILED"
    assert result["records_added"] == 1
    assert result["records_failed"] == 1
    assert "Row 3: Wrong column count" in result["error"]



# 5. ETL Runner: FileNotFoundError stops immediately (no retry waste)

def test_run_pipeline_missing_file(monkeypatch, sample_pipeline):
    """Missing CSV files should fail in 1 attempt instead of retrying 3 times."""
    def raise_missing_file(source):
        raise FileNotFoundError(f"Missing CSV: {source}")

    monkeypatch.setattr("etl.runner.extract_data", raise_missing_file)

    result = run_pipeline(sample_pipeline, triggered_by=None, max_retries=3)

    assert result["status"] == "FAILED"
    assert result["attempts"] == 1
    assert "Missing CSV" in result["error"]
    assert PipelineExecution.objects.filter(pipeline=sample_pipeline, status="FAILED").exists()
