from django.db import migrations


ROLE_PERMISSIONS = {
    "reader": ["view_article", "view_newsletter"],
    "editor": [
        "view_article",
        "change_article",
        "delete_article",
        "view_newsletter",
        "change_newsletter",
        "delete_newsletter",
    ],
    "journalist": [
        "view_article",
        "add_article",
        "change_article",
        "delete_article",
        "view_newsletter",
        "add_newsletter",
        "change_newsletter",
        "delete_newsletter",
    ],
}


def configure_role_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    database = schema_editor.connection.alias
    permission_names = {
        "view_article": "Can view article",
        "add_article": "Can add article",
        "change_article": "Can change article",
        "delete_article": "Can delete article",
        "view_newsletter": "Can view newsletter",
        "add_newsletter": "Can add newsletter",
        "change_newsletter": "Can change newsletter",
        "delete_newsletter": "Can delete newsletter",
    }

    role_permissions = {}
    for model_name in ("article", "newsletter"):
        content_type, _ = ContentType.objects.using(database).get_or_create(
            app_label="news",
            model=model_name,
        )
        for codename, name in permission_names.items():
            if codename.endswith("_" + model_name):
                permission, _ = Permission.objects.using(database).get_or_create(
                    content_type=content_type,
                    codename=codename,
                    defaults={"name": name},
                )
                role_permissions[codename] = permission

    for role, codenames in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.using(database).get_or_create(name=role)
        group.permissions.set([role_permissions[name] for name in codenames])


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0002_sync_user_role_groups"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [migrations.RunPython(configure_role_groups, migrations.RunPython.noop)]
