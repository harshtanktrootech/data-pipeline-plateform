import pytest
from django.urls import reverse
from pipelines.models import Pipeline
from executions.models import PipelineExecution
from dashboard.views import get_dashboard_stats


# 1. Empty Database Case (No crashes, clean zero defaults)

@pytest.mark.django_db
def test_stats_empty_db():
    """When no pipelines or executions exist, all KPI metrics default to 0."""
    stats = get_dashboard_stats()

    assert stats["total_pipelines"] == 0
    assert stats["active_pipelines"] == 0
    assert stats["disabled_pipelines"] == 0
    assert stats["successful_executions"] == 0
    assert stats["failed_executions"] == 0
    assert stats["partially_failed_executions"] == 0
    assert stats["running_executions"] == 0
    assert stats["failing_pipelines"] == 0
    assert stats["avg_execution_time"] == 0.0
    assert list(stats["recent_activities"]) == []


# 2. Aggregation Logic (Pipeline counts, execution statuses & avg duration)

def test_stats_counts_and_avg(admin_user, sample_pipeline):
    """Verify total/active/disabled pipelines, execution counts, and rounded avg time."""
    inactive_pipeline = Pipeline.objects.create(
        name="Archived ETL",
        status="inactive",
        created_by=admin_user,
    )

    PipelineExecution.objects.create(pipeline=sample_pipeline, status="SUCCESS", duration_seconds=2.5)
    PipelineExecution.objects.create(pipeline=sample_pipeline, status="FAILED", duration_seconds=1.25)
    PipelineExecution.objects.create(pipeline=inactive_pipeline, status="PARTIALLY_FAILED", duration_seconds=3)
    PipelineExecution.objects.create(pipeline=sample_pipeline, status="RUNNING", duration_seconds=0.5)

    stats = get_dashboard_stats()

    assert stats["total_pipelines"] == 2
    assert stats["active_pipelines"] == 1
    assert stats["disabled_pipelines"] == 1
    assert stats["successful_executions"] == 1
    assert stats["failed_executions"] == 1
    assert stats["partially_failed_executions"] == 1
    assert stats["running_executions"] == 1
    # (2.5 + 1.25 + 3.0 + 0.5) / 4 = 1.8125 -> rounded to 1.81
    assert stats["avg_execution_time"] == 1.81


# 3. Important Business Rule: Failing pipelines count ONLY latest run

def test_failing_clears_on_success(sample_pipeline):
    """
    If a pipeline fails, failing_pipelines is 1.
    Once a newer run succeeds, failing_pipelines drops back to 0.
    """
    # 1. Pipeline fails -> currently failing (1)
    PipelineExecution.objects.create(pipeline=sample_pipeline, status="FAILED")
    assert get_dashboard_stats()["failing_pipelines"] == 1

    # 2. Newer SUCCESS run happens -> pipeline is healthy again (0)
    PipelineExecution.objects.create(pipeline=sample_pipeline, status="SUCCESS")
    assert get_dashboard_stats()["failing_pipelines"] == 0


# 4. REST API Tests (/api/dashboard/stats/)

@pytest.mark.django_db
def test_stats_api_requires_auth(api_client):
    """Anonymous users are rejected with 401 Unauthorized."""
    response = api_client.get(reverse("api-dashboard-stats"))
    assert response.status_code == 401


def test_stats_api_metrics(api_client, viewer_user, operator_user, sample_pipeline):
    """Viewer can read serialized KPI stats for a pipeline run triggered by an Operator."""
    PipelineExecution.objects.create(
        pipeline=sample_pipeline,
        status="SUCCESS",
        triggered_by=operator_user,
        duration_seconds=1.5,
    )
    api_client.force_authenticate(user=viewer_user)

    response = api_client.get(reverse("api-dashboard-stats"))

    assert response.status_code == 200
    data = response.json()
    assert data["total_pipelines"] == 1
    assert data["successful_executions"] == 1
    assert data["avg_execution_time"] == 1.5
    assert len(data["recent_activities"]) == 1
    assert data["recent_activities"][0]["pipeline_name"] == sample_pipeline.name



# 5. HTML Dashboard Page Tests (/dashboard/)

@pytest.mark.django_db
def test_page_redirects_guest(client):
    """Unauthenticated browser requests redirect to login page (302)."""
    response = client.get(reverse("dashboard-page"))
    assert response.status_code == 302
    assert "/login/" in response.url


def test_page_renders_viewer(client, viewer_user, operator_user, sample_pipeline):
    """Authenticated users (like Viewer) see the rendered dashboard page (200)."""
    PipelineExecution.objects.create(pipeline=sample_pipeline, status="SUCCESS", triggered_by=operator_user)
    client.force_login(viewer_user)

    response = client.get(reverse("dashboard-page"))

    assert response.status_code == 200
    assert sample_pipeline.name.encode() in response.content
