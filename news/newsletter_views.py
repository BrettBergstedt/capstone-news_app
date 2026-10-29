
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied

from .models import Newsletter, User
from .serializers import NewsletterSerializer
from .permissions import IsNewsletterAuthorOrEditor


class NewsletterListCreateView(generics.ListCreateAPIView):
    serializer_class = NewsletterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Newsletter.objects.select_related("author").prefetch_related(
            "articles"
        )

    def perform_create(self, serializer):
        user = self.request.user

        if user.is_superuser:
            serializer.save(author=user)
            return

        if user.role not in (
            User.Role.EDITOR,
            User.Role.JOURNALIST,
        ):
            raise PermissionDenied(
                "Only editors and journalists can create newsletters."
            )

        serializer.save(author=user)

    def get_serializer(self, *args, **kwargs):
        return super().get_serializer(*args, **kwargs)


class NewsletterDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = NewsletterSerializer
    permission_classes = [IsNewsletterAuthorOrEditor]

    def get_queryset(self):
        return Newsletter.objects.select_related("author").prefetch_related(
            "articles"
        )
