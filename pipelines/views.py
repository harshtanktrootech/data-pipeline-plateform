from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import CanManagePipeline

from pipelines.models import Pipeline
from pipelines.serializers import PipelineSerializer



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