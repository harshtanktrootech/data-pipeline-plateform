import pytest
from django.contrib.auth.models import User, Group
from rest_framework.test import APIClient
from pipelines.models import Pipeline


@pytest.fixture
def api_client():
    """Returns a Django REST Framework API test client."""
    return APIClient()


@pytest.fixture
def user(db):
    """A standard authenticated user with no special roles."""
    return User.objects.create_user(
        username="standard_user",
        email="standard@example.com",
        password="password123",
    )


@pytest.fixture
def admin_user(db):
    """A superuser with full admin privileges."""
    return User.objects.create_superuser(
        username="admin_user",
        email="admin@example.com",
        password="password123",
    )


@pytest.fixture
def operator_user(db):
    """A user assigned to the 'Operator' group."""
    group, _ = Group.objects.get_or_create(name="Operator")
    usr = User.objects.create_user(
        username="operator_user",
        email="operator@example.com",
        password="password123",
    )
    usr.groups.add(group)
    return usr


@pytest.fixture
def viewer_user(db):
    """A user assigned to the 'Viewer' group."""
    group, _ = Group.objects.get_or_create(name="Viewer")
    usr = User.objects.create_user(
        username="viewer_user",
        email="viewer@example.com",
        password="password123",
    )
    usr.groups.add(group)
    return usr


@pytest.fixture
def sample_pipeline(db, user):
    """A sample active pipeline owned by the standard user."""
    return Pipeline.objects.create(
        name="Sales Analytics Pipeline",
        description="Daily sales ingestion pipeline",
        source="data/sales.csv",
        status="active",
        created_by=user,
    )
