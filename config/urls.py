# config/urls.py
from django.contrib import admin
from django.urls import include, path
from accounts.views import login_view, register_view, logout_view
from pipelines.views import (
    pipeline_list_page,
    pipeline_detail_page,
    run_pipeline_page_view,
    pipeline_create_page,
    pipeline_edit_page,
    schedule_pipeline_view,
)
from audit.views import audit_log_list_page

urlpatterns = [
    path("admin/", admin.site.urls),

    # Authentication Routes
    path("login/", login_view, name="login-page"),
    path("register/", register_view, name="register-page"),
    path("logout/", logout_view, name="logout-page"),

    # REST APIs
    path("api/accounts/", include("accounts.urls")),
    path("api/pipelines/", include("pipelines.urls")),

    # Frontend HTML Routes
    path("", pipeline_list_page, name="home"),
    path("pipelines/", pipeline_list_page, name="pipeline-list-page"),
    path("pipelines/create/", pipeline_create_page, name="pipeline-create-page"),
    path("pipelines/<int:pk>/edit/", pipeline_edit_page, name="pipeline-edit-page"),
    path("pipelines/<int:pk>/", pipeline_detail_page, name="pipeline-detail-page"),
    path("pipelines/<int:pk>/run/", run_pipeline_page_view, name="pipeline-run-page"),
    path("pipelines/<int:pk>/schedule/", schedule_pipeline_view, name="pipeline-schedule"),
    path("audit/", audit_log_list_page, name="audit-log-page"),
]
