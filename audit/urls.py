from django.urls import path
from audit.views import audit_log_list_page

urlpatterns = [
    path("audit/", audit_log_list_page, name="audit-log-page"),
]
