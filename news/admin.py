from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, Publisher, Article, Newsletter, ApprovedArticleLog


@admin.register(User)
class CustomUserAdmin(UserAdmin):
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