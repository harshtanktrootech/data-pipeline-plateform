from django.urls import path, include
from rest_framework.routers import DefaultRouter
from pipelines.views import PipelineViewSet

router = DefaultRouter()
router.register("", PipelineViewSet, basename="pipeline")

urlpatterns = [
    path("", include(router.urls)),
]