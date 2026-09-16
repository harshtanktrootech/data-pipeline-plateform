from django.urls import path

from pipelines.views import (
    PipelineListCreateAPIView,
    PipelineDetailAPIView,
)


urlpatterns = [
    path("", PipelineListCreateAPIView.as_view(), name="pipeline-list-create"),
    path("<int:pk>/", PipelineDetailAPIView.as_view(), name="pipeline-detail"),
]