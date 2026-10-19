from django.urls import path
from pipelines.views import (
    PipelineListCreateAPIView,
    PipelineDetailAPIView,
    PipelineRunAPIView,
)

urlpatterns = [
    path("", PipelineListCreateAPIView.as_view(), name="pipeline-list-create"),
    path("<int:pk>/", PipelineDetailAPIView.as_view(), name="pipeline-detail"),
    path("<int:pk>/run/", PipelineRunAPIView.as_view(), name="api-pipeline-run"),
]