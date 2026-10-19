from django.db import migrations


def create_default_roles(apps, schema_editor):
    """
    Ensures standard RBAC roles (Admin, Operator, Viewer) exist in the database.
    Idempotent: uses get_or_create to safely run on both fresh and existing databases.
    """
    Group = apps.get_model("auth", "Group")
    roles = ["Admin", "Operator", "Viewer"]
    for role in roles:
        Group.objects.get_or_create(name=role)


def remove_default_roles(apps, schema_editor):
    """
    Reverse migration to delete default roles if migration is rolled back.
    """
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=["Admin", "Operator", "Viewer"]).delete()


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_default_roles, reverse_code=remove_default_roles),
    ]
