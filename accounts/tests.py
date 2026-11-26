import pytest
from django.contrib.auth.models import AnonymousUser
from accounts.permissions import (
    IsAdmin,
    IsOperator,
    IsViewer,
    CanManagePipeline,
    CanExecutePipeline,
)
from accounts.context_processors import user_roles


# Reusable helper: creates a request with a user attached in 1 line

@pytest.fixture
def req(rf):
    """Helper fixture: returns a request with user attached (defaults to AnonymousUser)."""
    def _create(user=None):
        request = rf.get("/")
        request.user = user if user is not None else AnonymousUser()
        return request
    return _create



# 1. IsAdmin Permission (Admin / Superuser only)

def test_is_admin(req, admin_user, user):
    perm = IsAdmin()

    assert perm.has_permission(req(admin_user), None) is True
    assert perm.has_permission(req(user), None) is False
    assert perm.has_permission(req(), None) is False  # Anonymous



# 2. IsOperator Permission (Operator group only)

def test_is_operator(req, operator_user, admin_user, user):
    perm = IsOperator()

    assert perm.has_permission(req(operator_user), None) is True
    assert perm.has_permission(req(admin_user), None) is False
    assert perm.has_permission(req(user), None) is False



# 3. IsViewer Permission (Viewer group only)

def test_is_viewer(req, viewer_user, operator_user, user):
    perm = IsViewer()

    assert perm.has_permission(req(viewer_user), None) is True
    assert perm.has_permission(req(operator_user), None) is False
    assert perm.has_permission(req(user), None) is False



# 4. CanManagePipeline (Admin can create/edit pipelines, Operators cannot)

def test_can_manage_pipeline(req, admin_user, operator_user, sample_pipeline):
    perm = CanManagePipeline()

    # Admin is allowed
    assert perm.has_permission(req(admin_user), None) is True
    assert perm.has_object_permission(req(admin_user), None, sample_pipeline) is True

    # Operator is blocked
    assert perm.has_permission(req(operator_user), None) is False
    assert perm.has_object_permission(req(operator_user), None, sample_pipeline) is False



# 5. CanExecutePipeline (Both Admin and Operator can run pipelines)

def test_can_execute_pipeline(req, admin_user, operator_user, viewer_user, user):
    perm = CanExecutePipeline()

    # Allowed
    assert perm.has_permission(req(admin_user), None) is True
    assert perm.has_permission(req(operator_user), None) is True

    # Denied
    assert perm.has_permission(req(viewer_user), None) is False
    assert perm.has_permission(req(user), None) is False



# 6. Context Processor (Template Navbar Roles)

def test_user_roles_context(req, admin_user, operator_user, viewer_user):
    # Guest
    guest_context = user_roles(req())
    assert guest_context["user_role"] == "Guest"
    assert guest_context["is_admin"] is False
    assert guest_context["is_operator"] is False

    # Admin
    admin_context = user_roles(req(admin_user))
    assert admin_context["user_role"] == "Admin"
    assert admin_context["is_admin"] is True
    assert admin_context["is_operator"] is True

    # Operator
    operator_context = user_roles(req(operator_user))
    assert operator_context["user_role"] == "Operator"
    assert operator_context["is_admin"] is False
    assert operator_context["is_operator"] is True

    # Viewer
    viewer_context = user_roles(req(viewer_user))
    assert viewer_context["user_role"] == "Viewer"
    assert viewer_context["is_admin"] is False
    assert viewer_context["is_operator"] is False
