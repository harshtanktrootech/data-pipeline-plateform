# from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import IsAdmin, IsOperator, IsViewer


class AdminTestAPIView(APIView):

    permission_classes = [IsAdmin]

    def get(self, request):
        return Response({
            "message": "Welcome Admin"
        })


class OperatorTestAPIView(APIView):

    permission_classes = [IsOperator]

    def get(self, request):
        return Response({
            "message": "Welcome Operator"
        })


class ViewerTestAPIView(APIView):

    permission_classes = [IsViewer]

    def get(self, request):
        return Response({
            "message": "Welcome Viewer"
        })