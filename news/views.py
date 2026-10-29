
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction

import requests
import hmac

from django.db.models import Q

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Article, ApprovedArticleLog, Publisher
from .serializers import (
    ArticleSerializer,
    PublisherSerializer,
    UserSerializer,
    UserRegistrationSerializer,
)
from .permissions import IsArticleEditorOrJournalist, IsEditor, IsJournalist, IsReader


class PublisherListView(generics.ListAPIView):
    serializer_class = PublisherSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Publisher.objects.all().order_by("name")


class CurrentUserView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]


class ArticleListView(generics.ListCreateAPIView):
    """List approved articles and allow journalists to submit articles."""
    serializer_class = ArticleSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsJournalist()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        return Article.objects.filter(approved=True).select_related(
            "author", "publisher"
        )

    def perform_create(self, serializer):
        serializer.save(author=self.request.user, publisher=None)


class SubscribedArticleListView(generics.ListAPIView):
    """List approved articles from the reader's subscriptions."""

    serializer_class = ArticleSerializer
    permission_classes = [permissions.IsAuthenticated, IsReader]

    def get_queryset(self):
        user = self.request.user
        publisher_ids = user.subscribed_publishers.values_list(
            "id", flat=True
        )
        journalist_ids = user.subscribed_journalists.values_list(
            "id", flat=True
        )

        return (
            Article.objects.filter(approved=True)
            .filter(
                Q(publisher_id__in=publisher_ids)
                | Q(author_id__in=journalist_ids)
            )
            .select_related("author", "publisher")
            .distinct()
        )


class ArticleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Read approved stories; editors and journalists manage permitted stories."""
    serializer_class = ArticleSerializer
    permission_classes = [IsArticleEditorOrJournalist]

    def get_queryset(self):
        queryset = Article.objects.select_related("author", "publisher")
        user = self.request.user
        if self.request.method in permissions.SAFE_METHODS:
            if user.is_authenticated and (
                user.is_superuser or user.role == "editor"
            ):
                return queryset
            return queryset.filter(approved=True)
        if user.is_authenticated and (user.is_superuser or user.role == "editor"):
            return queryset
        return queryset.filter(author=user, approved=False)

class ApproveArticleView(APIView):
    """Editors approve articles and trigger notifications."""

    permission_classes = [permissions.IsAuthenticated, IsEditor]

    @transaction.atomic
    def post(self, request, pk):
        article = get_object_or_404(
            Article.objects.select_for_update(),
            pk=pk,
        )

        if article.approved:
            return Response(
                {"detail": "Article is already approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        article.approved = True
        article.save()

        # Save a log that can be received by the local callback endpoint.
        try:
            response = requests.post(
                request.build_absolute_uri("/api/approved/"),
                headers={
                    "X-Callback-Token": settings.APPROVAL_CALLBACK_TOKEN,
                },
                json={
                    "article": article.pk,
                    "article_title": article.title,
                    "source": "internal-approval-workflow",
                },
                timeout=5,
            )
            response.raise_for_status()
        except requests.RequestException:
            # Keep the approval even if the callback is temporarily unavailable.
            pass

        # Notify readers who subscribe to this publisher or journalist.
        from .models import User

        readers = User.objects.filter(role=User.Role.READER)

        if article.publisher_id:
            readers = readers.filter(
                subscribed_publishers=article.publisher
            )
        elif article.author_id:
            readers = readers.filter(
                subscribed_journalists=article.author
            )

        recipient_emails = list(
            readers.exclude(email="")
            .values_list("email", flat=True)
            .distinct()
        )

        if recipient_emails:
            send_mail(
                subject=f"New approved article: {article.title}",
                message=(
                    f"The article '{article.title}' has been approved.\n\n"
                    f"{article.content}"
                ),
                from_email=getattr(
                    settings, "DEFAULT_FROM_EMAIL", None
                ),
                recipient_list=recipient_emails,
                fail_silently=True,
            )

        return Response(
            {
                "detail": "Article approved.",
                "article": ArticleSerializer(article).data,
            },
            status=status.HTTP_200_OK,
        )


class ApprovedArticleCallbackView(APIView):
    """Receive approval callbacks and record them."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        expected_token = settings.APPROVAL_CALLBACK_TOKEN
        if not expected_token:
            return Response(
                {"detail": "Approval callback is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        supplied_token = request.headers.get("X-Callback-Token", "")
        if not hmac.compare_digest(supplied_token, expected_token):
            return Response(
                {"detail": "Invalid callback token."},
                status=status.HTTP_403_FORBIDDEN,
            )

        article_id = request.data.get("article")
        title = request.data.get("article_title")
        source = request.data.get(
            "source", "internal-approval-workflow"
        )

        if not article_id or not title:
            return Response(
                {"detail": "article and article_title are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        log = ApprovedArticleLog.objects.create(
            article_id=article_id,
            article_title=title,
            source=source,
        )

        return Response(
            {"detail": "Approval callback recorded.", "id": log.pk},
            status=status.HTTP_201_CREATED,
        )
