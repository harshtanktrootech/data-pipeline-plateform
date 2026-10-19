from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from accounts.views import (
    UserListCreateAPIView,
    UserDetailAPIView,
)

urlpatterns = [
    # JWT Authentication
    path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # User Management & RBAC REST APIs (Admin Only)
    path("users/", UserListCreateAPIView.as_view(), name="api-user-list-create"),
    path("users/<int:pk>/", UserDetailAPIView.as_view(), name="api-user-detail"),
]
