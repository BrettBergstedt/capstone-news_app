from django.conf import settings
from django.db import migrations


def sync_existing_users(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    Group = apps.get_model("auth", "Group")
    database = schema_editor.connection.alias

    for user in User.objects.using(database).all().iterator():
        group, _ = Group.objects.using(database).get_or_create(name=user.role)
        user.groups.add(group)


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("news", "0001_initial"),
    ]

    operations = [migrations.RunPython(sync_existing_users, migrations.RunPython.noop)]
