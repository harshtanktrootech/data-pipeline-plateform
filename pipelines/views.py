from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from pipelines.models import Pipeline
from pipelines.serializers import PipelineSerializer

from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView
)
from rest_framework.permissions import IsAuthenticated



# REST API VIEWS
# URL: /api/pipelines/

class PipelineListView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    queryset = Pipeline.objects.all()
    serializer_class = PipelineSerializer

    def get_queryset(self):
        return self.queryset.filter(created_by=self.request.user)


class PipelineDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]

    queryset = Pipeline.objects.all()
    serializer_class = PipelineSerializer



# HTML / BOOTSTRAP VIEWS
# URL: /pipelines/

@login_required
def pipeline_list_page(request):
    pipelines = Pipeline.objects.all().order_by("-created_at")

    return render(
        request, "pipelines/pipeline_list.html", {"pipelines": pipelines},
    )


@login_required
def pipeline_detail_page(request, pk):
    pipeline = get_object_or_404(Pipeline, pk=pk)

    return render(
        request,
        "pipelines/pipeline_details.html",
        {"pipeline": pipeline},
    )