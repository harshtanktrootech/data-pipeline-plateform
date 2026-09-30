import os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)

from rest_framework.permissions import IsAuthenticated
from accounts.permissions import CanManagePipeline
from pipelines.models import Pipeline
from pipelines.serializers import PipelineSerializer
from etl.runner import run_pipeline


class PipelineListCreateAPIView(ListCreateAPIView):

    queryset = Pipeline.objects.all()
    serializer_class = PipelineSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]

        return [CanManagePipeline()]
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    

class PipelineDetailAPIView(RetrieveUpdateDestroyAPIView):

    queryset = Pipeline.objects.all()
    serializer_class = PipelineSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]

        return [CanManagePipeline()]


# ── HTML Page Views ──

@login_required(login_url="/admin/login/")
def pipeline_list_page(request):
    pipelines = Pipeline.objects.select_related("created_by").all().order_by("-created_at")
    return render(request, "pipelines/pipeline_list.html", {"pipelines": pipelines})


@login_required(login_url="/admin/login/")
def pipeline_detail_page(request, pk):
    pipeline = get_object_or_404(Pipeline.objects.select_related("created_by"), pk=pk)
    return render(request, "pipelines/pipeline_details.html", {"pipeline": pipeline})