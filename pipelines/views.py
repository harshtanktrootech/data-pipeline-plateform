# from django.shortcuts import render

from pipelines.models import Pipeline
from pipelines.serializers import PipelineSerializer

from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView
)

from rest_framework.permissions import IsAuthenticated


class PipelineListCreateAPIView(ListCreateAPIView):

    permission_classes = [IsAuthenticated]

    queryset = Pipeline.objects.all()
    serializer_class = PipelineSerializer


class PipelineDetailAPIView(RetrieveUpdateDestroyAPIView):

    permission_classes = [IsAuthenticated]

    queryset = Pipeline.objects.all()
    serializer_class = PipelineSerializer
