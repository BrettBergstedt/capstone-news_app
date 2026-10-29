"""Server-rendered HTML views for the Daily Brief website.

These function-based views power the pages a reader sees in a browser, while
`views.py` supplies the JSON API. Where a page must behave identically to the
API, it calls the API view instead of duplicating the logic, so the two cannot
drift apart.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ArticleSubmissionForm, NewsletterForm
from .models import Article, Newsletter, User
from .views import ApproveArticleView


def article_list(request):
    """Render every approved article.

    `select_related` pulls each article's author and publisher into the same
    query; without it the template would run an extra query per row.
    """
    articles = Article.objects.filter(approved=True).select_related(
        "author", "publisher"
    )
    return render(request, "news/article_list.html", {"articles": articles})


def article_detail(request, pk):
    """Render one approved article, or return a 404 if there is none.

    The approval filter is part of the query rather than a check afterwards, so
    an unapproved article cannot be reached even by guessing its primary key.
    """
    article = get_object_or_404(
        Article.objects.filter(approved=True).select_related("author", "publisher"),
        pk=pk,
    )
    return render(request, "news/article_detail.html", {"article": article})


@login_required
def article_create(request):
    """Let a journalist submit an article for editorial review.

    The role check is done here as well as in the form, and `author` is taken
    from the logged-in session twice over - on `form.instance` and on the saved
    object - so a crafted POST cannot claim to be written by someone else.
    """
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
    """Show an editor the articles still waiting for a decision."""
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
    """Approve a pending article by delegating to the API view.

    `@require_POST` matters: approving sends email to every subscriber, so a
    GET request must never trigger it. Without the decorator a browser
    prefetch, a link scanner or an image proxy could publish an article by
    loading the page.
    """
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
    """Render every newsletter with its articles.

    `prefetch_related` is used rather than `select_related` because `articles`
    is a many-to-many relation, which cannot be joined in a single query.
    """
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
    """Let a journalist or editor assemble and save a newsletter.

    `commit=False` saves the newsletter without its many-to-many articles,
    because the author must be set from the session before the row is written;
    `save_m2m()` then attaches the chosen articles afterwards. Omitting that
    second call would silently create a newsletter with no content.
    """
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
