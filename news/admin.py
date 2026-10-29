"""Django admin registrations for the news app.

Declares which models administrators can manage through the built-in admin
dashboard, and extends the default user edit form with the app's own `role`
field so an administrator can change someone's role without editing the
database directly.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, Publisher, Article, Newsletter, ApprovedArticleLog


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Django's user admin, extended with the news app's role field.

    `fieldsets` controls the edit form for an existing account and
    `add_fieldsets` the form used when creating one. Both append a "News App
    Details" section, because replacing the tuple outright would hide Django's
    built-in username and password fields.
    """

    fieldsets = UserAdmin.fieldsets + (
        ("News App Details", {"fields": ("role",)}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ("News App Details", {"fields": ("role",)}),
    )


admin.site.register(Publisher)
admin.site.register(Article)
admin.site.register(Newsletter)
admin.site.register(ApprovedArticleLog)
