from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):

    def has_permission(self, request, view):     #  DRF calls this method when a request reaches the API.
        return(
            request.user.is_authenticated
            and request.user.groups.filter(name="Admin").exists()
        )


class IsOperator(BasePermission):

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.groups.filter(name="Operator").exists()
        )


class IsViewer(BasePermission):

    def has_permission(self, request, view):
        return(
            request.user.is_authenticated
            and request.user.groups.filter(name="Viewer").exists()
        )