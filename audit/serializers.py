from rest_framework import serializers
from audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    """
    Serializer for the AuditLog model.
    Read-only serializer providing immutable audit trail entries with:
    - username: Username of the user who acted (or 'System' if automated)
    - action_display: Human-readable action label (e.g. 'Pipeline Run Triggered')
    """
    username = serializers.SerializerMethodField()
    action_display = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "user",
            "username",
            "action",
            "action_display",
            "resource",
            "details",
            "timestamp",
        ]
        read_only_fields = fields

    def get_username(self, obj):
        return obj.user.username if obj.user else "System"
