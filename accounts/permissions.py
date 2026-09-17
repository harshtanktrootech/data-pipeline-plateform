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


class IsAdminOrOperator(BasePermission):

    def has_permission(self, request, view):
        return(
            request.user.is_authenticated
            and request.user.groups.filter(
                name__in=["Admin", "Operator"]
            ).exists()
        )



class IsPipelineOwnerOrAdmin(BasePermission):

    def has_object_permission(self, request, view, obj):

        if request.user.groups.filter(name="Admin").exists():
            return True

        return obj.created_by == request.user



class CanManagePipeline(BasePermission):

    def has_permission(self, request, view):        # Is user Admin or Operator?

        return (
            request.user.is_authenticated
            and request.user.groups.filter(
                name__in=["Admin", "Operator"]
            ).exists()
        )

    def has_object_permission(self, request, view, obj):        # Is Admin? OR Is Owner?

        if request.user.groups.filter(name="Admin").exists():
            return True

        return obj.created_by == request.user