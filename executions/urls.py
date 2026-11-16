from django.urls import path, include
from rest_framework.routers import DefaultRouter
from executions.views import PipelineExecutionViewSet

router = DefaultRouter()
router.register("", PipelineExecutionViewSet, basename="execution")

urlpatterns = [
    path("", include(router.urls)),
]
