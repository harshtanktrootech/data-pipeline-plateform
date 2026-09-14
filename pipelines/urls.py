from django.urls import path

from pipelines.views import (
    PipelineDetailView,
    PipelineListView,
)

urlpatterns = [
    path("", PipelineListView.as_view(), name="pipeline-list-create"),
    path("<int:pk>/", PipelineDetailView.as_view(), name="pipeline-detail"),
]
