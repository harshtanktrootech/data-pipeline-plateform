from django.urls import path
from pipelines.views import (
    PipelineDetailAPIView,
    PipelineListCreateAPIView,
)

urlpatterns = [
    path("", PipelineListCreateAPIView.as_view(), name="pipeline-list-create"),
    path("<int:pk>/", PipelineDetailAPIView.as_view(), name="pipeline-detail"),
]


# Therefore the final URLs become:

# GET     /api/pipelines/
# POST    /api/pipelines/

# GET     /api/pipelines/1/
# PUT     /api/pipelines/1/
# PATCH   /api/pipelines/1/
# DELETE  /api/pipelines/1/