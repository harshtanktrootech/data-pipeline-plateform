import pytest
from django.urls import reverse
from pipelines.models import Pipeline
from audit.models import AuditLog


# 1. Authentication Check (Unauthenticated user is rejected)

@pytest.mark.django_db
def test_list_requires_auth(api_client):
    """Anonymous users cannot access the pipelines API."""
    url = reverse("pipeline-list")
    response = api_client.get(url)

    assert response.status_code == 401


# 2. List & Retrieve (Any authenticated user like Viewer can read)

def test_list_pipelines(api_client, viewer_user, sample_pipeline):
    """Logged-in users (even Viewers) can list pipelines."""
    api_client.force_authenticate(user=viewer_user)

    response = api_client.get(reverse("pipeline-list"))

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == sample_pipeline.name


# 3. Create Pipeline (Admin allowed, Operator blocked, Validation checked)

def test_create_pipeline_admin(api_client, admin_user):
    """Admin can create a pipeline; DB record and AuditLog are created."""
    api_client.force_authenticate(user=admin_user)
    payload = {
        "name": "Orders Ingestion",
        "description": "Hourly orders CSV",
        "status": "active",
    }

    response = api_client.post(reverse("pipeline-list"), payload, format="json")

    assert response.status_code == 201
    assert response.json()["name"] == "Orders Ingestion"
    assert Pipeline.objects.filter(name="Orders Ingestion", created_by=admin_user).exists()
    assert AuditLog.objects.filter(action="PIPELINE_CREATE").exists()


def test_create_pipeline_forbidden(api_client, operator_user):
    """Operator cannot create pipelines (403 Forbidden)."""
    api_client.force_authenticate(user=operator_user)

    response = api_client.post(reverse("pipeline-list"), {"name": "Blocked Pipeline"}, format="json")

    assert response.status_code == 403
    assert Pipeline.objects.count() == 0


def test_create_pipeline_invalid_name(api_client, admin_user):
    """Serializer rejects pipeline names shorter than 3 characters (400 Bad Request)."""
    api_client.force_authenticate(user=admin_user)

    response = api_client.post(reverse("pipeline-list"), {"name": "ab"}, format="json")

    assert response.status_code == 400
    assert "name" in response.json()


# 4. Update & Delete Pipeline (Admin only)

def test_update_and_delete_pipeline(api_client, admin_user, sample_pipeline):
    """Admin can update (PATCH) and delete (DELETE) a pipeline."""
    api_client.force_authenticate(user=admin_user)
    detail_url = reverse("pipeline-detail", args=[sample_pipeline.pk])

    # Update
    patch_resp = api_client.patch(detail_url, {"status": "inactive"}, format="json")
    assert patch_resp.status_code == 200
    sample_pipeline.refresh_from_db()
    assert sample_pipeline.status == "inactive"
    assert AuditLog.objects.filter(action="PIPELINE_UPDATE").exists()

    # Delete
    del_resp = api_client.delete(detail_url)
    assert del_resp.status_code == 204
    assert not Pipeline.objects.filter(pk=sample_pipeline.pk).exists()
    assert AuditLog.objects.filter(action="PIPELINE_DELETE").exists()



# 5. Custom Action Guard: Cannot run an inactive pipeline

def test_run_inactive_pipeline(api_client, operator_user, sample_pipeline):
    """Operator has run permission, but inactive pipelines must return 400."""
    sample_pipeline.status = "inactive"
    sample_pipeline.save()

    api_client.force_authenticate(user=operator_user)
    run_url = reverse("pipeline-run", args=[sample_pipeline.pk])

    response = api_client.post(run_url)

    assert response.status_code == 400
    assert "inactive" in response.json()["error"].lower()



# 6. HTML Frontend View Tests (Using Django's 'client' fixture)

@pytest.mark.django_db
def test_page_redirects_guest(client):
    """Unauthenticated browser request redirects to login page (302)."""
    response = client.get(reverse("pipeline-list-page"))

    assert response.status_code == 302
    assert "/login/" in response.url


def test_page_renders_user(client, user, sample_pipeline):
    """Authenticated browser request renders the HTML page (200)."""
    client.force_login(user)

    response = client.get(reverse("pipeline-list-page"))

    assert response.status_code == 200
    assert sample_pipeline.name.encode() in response.content

