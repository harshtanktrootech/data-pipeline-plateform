from django.urls import path
from audit.views import (
    AuditLogListAPIView,
    AuditLogDetailAPIView,
)

urlpatterns = [
    path("", AuditLogListAPIView.as_view(), name="api-audit-list"),
    path("<int:pk>/", AuditLogDetailAPIView.as_view(), name="api-audit-detail"),
]
