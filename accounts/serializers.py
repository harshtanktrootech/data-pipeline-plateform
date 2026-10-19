from rest_framework import serializers
from django.contrib.auth.models import User, Group


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model with RBAC role handling.
    Exposes username, email, active status, date joined, and computed role.
    """
    role = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False, min_length=4)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "role",
            "is_active",
            "date_joined",
            "password",
        ]
        read_only_fields = ["id", "date_joined"]

    def get_role(self, obj):
        group_names = set(obj.groups.values_list("name", flat=True))
        if obj.is_superuser or "Admin" in group_names:
            return "Admin"
        if "Operator" in group_names:
            return "Operator"
        return "Viewer"

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        role = self.initial_data.get("role", "Viewer")

        if not password:
            raise serializers.ValidationError({"password": "Password is required when creating a user."})

        user = User.objects.create_user(**validated_data)
        user.set_password(password)

        # Assign Role Group
        group, _ = Group.objects.get_or_create(name=role)
        user.groups.add(group)
        if role == "Admin":
            user.is_staff = True
        user.save()

        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        if password:
            instance.set_password(password)

        role = self.initial_data.get("role")
        if role and role in ["Admin", "Operator", "Viewer"]:
            instance.groups.clear()
            group, _ = Group.objects.get_or_create(name=role)
            instance.groups.add(group)
            instance.is_staff = (role == "Admin")

        return super().update(instance, validated_data)
