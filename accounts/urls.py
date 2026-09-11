from django.urls import path

from rest_framework_simplejwt.views import(
    TokenObtainPairView,
    TokenRefreshView,
)
from accounts.views import AdminTestAPIView, OperatorTestAPIView, ViewerTestAPIView 


urlpatterns = [
    path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # path("me/", ProfileAPIView.as_view(), name="profil"),

    path("admin-test/", AdminTestAPIView.as_view()),
    path("operator-test/", OperatorTestAPIView.as_view()),
    path("viewer-test/", ViewerTestAPIView.as_view()),
]
