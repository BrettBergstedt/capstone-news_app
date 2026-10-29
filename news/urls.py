
from django.urls import path
from .subscription_views import SubscriptionView
from .newsletter_views import NewsletterListCreateView, NewsletterDetailView

from .views import (
    ArticleListView,
    SubscribedArticleListView,
    ArticleDetailView,
    ApproveArticleView,
    ApprovedArticleCallbackView,
    PublisherListView,
    CurrentUserView,
    UserRegistrationView,
)

urlpatterns = [
    path("users/register/", UserRegistrationView.as_view(), name="user-register"),
    path("users/me/", CurrentUserView.as_view(), name="current-user"),
    path("publishers/", PublisherListView.as_view(), name="publisher-list"),
    path("articles/", ArticleListView.as_view(), name="article-list"),
    path(
        "articles/subscribed/",
        SubscribedArticleListView.as_view(),
        name="subscribed-articles",
    ),
    path(
        "articles/<int:pk>/",
        ArticleDetailView.as_view(),
        name="article-detail",
    ),
    path(
        "articles/create/",
        ArticleListView.as_view(),
        name="article-create",
    ),
    path(
        "articles/<int:pk>/update/",
        ArticleDetailView.as_view(),
        name="article-update",
    ),
    path(
        "articles/<int:pk>/delete/",
        ArticleDetailView.as_view(),
        name="article-delete",
    ),
    path(
        "articles/<int:pk>/approve/",
        ApproveArticleView.as_view(),
        name="article-approve",
    ),
    path(
        "approved/",
        ApprovedArticleCallbackView.as_view(),
        name="approved-callback",
    ),
    path(
        "subscriptions/",
        SubscriptionView.as_view(),
        name="subscriptions",
    ),
    path(
        "newsletters/",
        NewsletterListCreateView.as_view(),
        name="newsletter-list-create",
    ),
    path(
        "newsletters/<int:pk>/",
        NewsletterDetailView.as_view(),
        name="newsletter-detail",
    ),

]
