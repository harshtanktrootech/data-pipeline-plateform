import pytest
from django.contrib.auth.models import AnonymousUser
from accounts.permissions import IsAdmin, IsOperator, IsViewer, CanManagePipeline
from accounts.context_processors import user_roles
from pipelines.models import Pipeline


# ============================================================================
# Concept 1: The 'rf' (RequestFactory) Fixture
# ============================================================================
# 'rf' is built into pytest-django. It creates a dummy HTTP request in memory
# so you can test permissions and views without running a full HTTP server.


def test_anonymous_user_denied_all_permissions(rf):
    """
    Ensure an unauthenticated (anonymous) visitor is denied by all permission classes.
    """
    request = rf.get("/api/pipelines/")
    request.user = AnonymousUser()

    assert IsAdmin().has_permission(request, view=None) is False
    assert IsOperator().has_permission(request, view=None) is False
    assert IsViewer().has_permission(request, view=None) is False
    assert CanManagePipeline().has_permission(request, view=None) is False


# ============================================================================
# Concept 2: Role-Based Permissions (Admin, Operator, Viewer)
# ============================================================================
def test_is_admin_permission(rf, admin_user, operator_user, user):
    """
    Test that IsAdmin allows superusers/admins and blocks everyone else.
    """
    request = rf.get("/")
    permission = IsAdmin()

    # Admin user -> Allowed
    request.user = admin_user
    assert permission.has_permission(request, view=None) is True

    # Operator user -> Denied
    request.user = operator_user
    assert permission.has_permission(request, view=None) is False

    # Standard user -> Denied
    request.user = user
    assert permission.has_permission(request, view=None) is False


def test_is_operator_permission(rf, operator_user, viewer_user):
    """
    Test that IsOperator allows only members of the Operator group.
    """
    request = rf.get("/")
    permission = IsOperator()

    request.user = operator_user
    assert permission.has_permission(request, view=None) is True

    request.user = viewer_user
    assert permission.has_permission(request, view=None) is False


def test_is_viewer_permission(rf, viewer_user, user):
    """
    Test that IsViewer allows only members of the Viewer group.
    """
    request = rf.get("/")
    permission = IsViewer()

    request.user = viewer_user
    assert permission.has_permission(request, view=None) is True

    request.user = user
    assert permission.has_permission(request, view=None) is False
