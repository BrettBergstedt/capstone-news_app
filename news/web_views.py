from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ArticleSubmissionForm, NewsletterForm
from .models import Article, Newsletter, User
from .views import ApproveArticleView


def article_list(request):
    articles = Article.objects.filter(approved=True).select_related(
        "author", "publisher"
    )
    return render(request, "news/article_list.html", {"articles": articles})


def article_detail(request, pk):
    article = get_object_or_404(
        Article.objects.filter(approved=True).select_related("author", "publisher"),
        pk=pk,
    )
    return render(request, "news/article_detail.html", {"article": article})


@login_required
def article_create(request):
    if request.user.role != User.Role.JOURNALIST and not request.user.is_superuser:
        raise PermissionDenied("Only journalists can submit articles.")

    form = ArticleSubmissionForm(request.POST or None)
    if request.method == "POST":
        form.instance.author = request.user
    if request.method == "POST" and form.is_valid():
        article = form.save(commit=False)
        article.author = request.user
        article.save()
        messages.success(request, "Your article was submitted for editor review.")
        return redirect("web:article-list")
    return render(request, "news/article_form.html", {"form": form})


@login_required
def pending_articles(request):
    if request.user.role != User.Role.EDITOR and not request.user.is_superuser:
        raise PermissionDenied("Only editors can review articles.")
    articles = Article.objects.filter(approved=False).select_related(
        "author", "publisher"
    )
    return render(
        request,
        "news/pending_articles.html",
        {"articles": articles},
    )


@login_required
@require_POST
def approve_article(request, pk):
    if request.user.role != User.Role.EDITOR and not request.user.is_superuser:
        raise PermissionDenied("Only editors can approve articles.")

    # Reuse the API workflow so email and the secured callback stay consistent.
    response = ApproveArticleView.as_view()(request, pk=pk)
    if response.status_code == 200:
        messages.success(request, "Article approved and subscribers notified.")
    else:
        messages.error(request, response.data.get("detail", "Approval failed."))
    return redirect("web:pending-articles")


def newsletter_list(request):
    newsletters = Newsletter.objects.select_related("author").prefetch_related(
        "articles"
    )
    return render(
        request,
        "news/newsletter_list.html",
        {"newsletters": newsletters},
    )


@login_required
def newsletter_create(request):
    if request.user.role not in (User.Role.JOURNALIST, User.Role.EDITOR):
        raise PermissionDenied("Only journalists and editors can create newsletters.")

    form = NewsletterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        newsletter = form.save(commit=False)
        newsletter.author = request.user
        newsletter.save()
        form.save_m2m()
        messages.success(request, "Your newsletter was saved.")
        return redirect("web:newsletter-list")
    return render(request, "news/newsletter_form.html", {"form": form})
