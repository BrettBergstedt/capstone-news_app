from django.urls import path

from . import web_views


app_name = "web"

urlpatterns = [
    path("", web_views.article_list, name="article-list"),
    path("articles/", web_views.article_list, name="article-list-all"),
    path("articles/<int:pk>/", web_views.article_detail, name="article-detail"),
    path("articles/submit/", web_views.article_create, name="article-create"),
    path("editor/pending/", web_views.pending_articles, name="pending-articles"),
    path(
        "editor/articles/<int:pk>/approve/",
        web_views.approve_article,
        name="approve-article",
    ),
    path("newsletters/", web_views.newsletter_list, name="newsletter-list"),
    path(
        "newsletters/create/",
        web_views.newsletter_create,
        name="newsletter-create",
    ),
]
