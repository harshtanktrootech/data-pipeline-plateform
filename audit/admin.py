from django.contrib import admin
from audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "timestamp", "user", "action", "resource", "ip_address")
    list_filter = ("action", "user", "timestamp")
    search_fields = ("resource", "details", "user__username", "ip_address")
    readonly_fields = ("user", "action", "resource", "details", "ip_address", "timestamp")
    ordering = ("-timestamp",)

    def has_add_permission(self, request):
        return False  # Audit logs should only be created systemically, not manually added

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Only superuser can delete audit logs
