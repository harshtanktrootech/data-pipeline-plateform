from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and (request.user.is_superuser or request.user.groups.filter(name="Admin").exists())
        )


class IsOperator(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.groups.filter(name="Operator").exists()
        )


class IsViewer(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.groups.filter(name="Viewer").exists()
        )


class CanManagePipeline(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.groups.filter(name__in=["Admin", "Operator"]).exists()
            )
        )

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser or request.user.groups.filter(name="Admin").exists():
            return True
        return obj.created_by == request.user