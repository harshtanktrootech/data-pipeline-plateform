from django.urls import path
from dashboard.views import DashboardStatsAPIView

urlpatterns = [
    path("stats/", DashboardStatsAPIView.as_view(), name="api-dashboard-stats"),
]