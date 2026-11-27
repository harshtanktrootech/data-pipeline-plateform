import pytest
from django.urls import reverse
from audit.models import AuditLog
from audit.services import log_action


# 1. Service & Model Properties (log_action, System actor, JSON & fallbacks)

@pytest.mark.django_db
def test_log_action_system():
    """Passing user=None creates a 'System' audit log with default INFO status."""
    log = log_action(
        user=None,
        action="PIPELINE_RUN",
        resource="Pipeline #1",
        details="Automated run",
    )

    assert log.user is None
    assert log.status == "INFO"
    assert "System" in str(log)


@pytest.mark.django_db
def test_audit_log_properties(user):
    """Verify total_processed, row JSON lists, and legacy details fallback parsing."""
    log = AuditLog.objects.create(
        user=user,
        action="PIPELINE_RUN",
        resource="Pipeline #5",
        status="INFO",
        details="Status: PARTIALLY_FAILED | Loaded: 12",
        records_updated=2,
        records_failed=1,
        error_details={
            "success_rows": [{"row_number": 2, "data": {"id": 1}}],
            "failed_rows": [{"row_number": 3, "error": "Invalid value"}],
        },
    )

    assert log.outcome_status == "PARTIALLY_FAILED"
    assert log.display_records_added == 12
    assert log.total_processed == 3  # 0 (records_added field) + 2 + 1
    assert len(log.success_rows_list) == 1
    assert len(log.failed_rows_list) == 1



# 2. REST API Access Control (/api/audit/ — Admin Only & Read-Only)

@pytest.mark.django_db
def test_api_requires_auth(api_client):
    """Anonymous users get 401 Unauthorized."""
    response = api_client.get(reverse("audit-list"))
    assert response.status_code == 401


def test_api_blocks_non_admin(api_client, operator_user, viewer_user):
    """Operators and Viewers are blocked with 403 Forbidden (Admin only)."""
    for non_admin in (operator_user, viewer_user):
        api_client.force_authenticate(user=non_admin)
        response = api_client.get(reverse("audit-list"))
        assert response.status_code == 403


def test_api_read_only(api_client, admin_user):
    """Audit trail is immutable: Admins cannot POST new entries via the API (405)."""
    api_client.force_authenticate(user=admin_user)

    response = api_client.post(
        reverse("audit-list"),
        {"action": "USER_LOGIN", "resource": "Test"},
        format="json",
    )
    assert response.status_code == 405



# 3. REST API Query Filtering (?action= & ?user=)

def test_api_filters(api_client, admin_user, operator_user):
    """Admin can filter audit logs by ?action= (case-insensitive) and ?user=<id>."""
    log_action(admin_user, "PIPELINE_CREATE", "Pipeline #1")
    log_action(operator_user, "PIPELINE_RUN", "Pipeline #1")

    api_client.force_authenticate(user=admin_user)
    url = reverse("audit-list")

    # Filter by action (lowercase input gets normalized to uppercase)
    action_resp = api_client.get(url, {"action": "pipeline_run"})
    assert action_resp.status_code == 200
    assert len(action_resp.json()) == 1
    assert action_resp.json()[0]["username"] == operator_user.username

    # Filter by user ID
    user_resp = api_client.get(url, {"user": admin_user.id})
    assert user_resp.status_code == 200
    assert len(user_resp.json()) == 1
    assert user_resp.json()[0]["action"] == "PIPELINE_CREATE"



# 4. HTML Audit Pages (/audit/ and /audit/<pk>/)

def test_page_redirects_non_admin(client, operator_user):
    """Non-admins visiting /audit/ are redirected back to /pipelines/ (302)."""
    client.force_login(operator_user)

    response = client.get(reverse("audit-log-page"))

    assert response.status_code == 302
    assert reverse("pipeline-list-page") in response.url


def test_pages_for_admin(client, admin_user, sample_pipeline):
    """Admins can view the audit list (with ?user=system filter) and detail page."""
    sys_log = log_action(
        user=None,
        action="PIPELINE_RUN",
        resource=f"Pipeline '{sample_pipeline.name}' (#{sample_pipeline.id})",
        status="FAILED",
        records_failed=1,
        error_details={"failed_rows": [{"row_number": 2, "data": {"col": "bad"}, "error": "Parse error"}]},
    )
    client.force_login(admin_user)

    # List page with system filter
    list_resp = client.get(reverse("audit-log-page"), {"user": "system"})
    assert list_resp.status_code == 200
    assert sample_pipeline.name.encode() in list_resp.content

    # Detail page
    detail_resp = client.get(reverse("audit-log-detail-page", args=[sys_log.pk]))
    assert detail_resp.status_code == 200
    assert b"Parse error" in detail_resp.content
