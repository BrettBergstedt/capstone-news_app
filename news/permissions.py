
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsEditor(BasePermission):
    """Only editors and administrators can approve articles."""

    def has_permission(self, request, view):
        user = request.user

        return bool(
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or getattr(user, "role", None) == "editor"
            )
        )


class IsJournalist(BasePermission):
    """Only journalists and administrators can create articles."""

    def has_permission(self, request, view):
        user = request.user

        return bool(
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or getattr(user, "role", None) == "journalist"
            )
        )


class IsReader(BasePermission):
    """Only readers and administrators can access reader features."""

    def has_permission(self, request, view):
        user = request.user

        return bool(
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or getattr(user, "role", None) == "reader"
            )
        )


class IsOwnerOrReadOnly(BasePermission):
    """Allow read-only access, but restrict edits to the article's author."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        user = request.user

        return bool(
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or getattr(obj, "author", None) == user
            )
        )


class IsNewsletterAuthorOrEditor(BasePermission):
    """Allow newsletter edits by its author, editors, or administrators."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        return bool(
            user.is_superuser
            or user.role == "editor"
            or obj.author_id == user.id
        )


class IsArticleEditorOrJournalist(BasePermission):
    """Readers may view public articles; editors and journalists manage them."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or user.role in ("editor", "journalist"))
        )

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(
            user.is_superuser
            or user.role == "editor"
            or (
                user.role == "journalist"
                and obj.author_id == user.id
                and not obj.approved
            )
        )
