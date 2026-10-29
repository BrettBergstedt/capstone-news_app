"""Database models for The Daily Brief news application.

Defines the tables the app runs on and, more importantly, the rules that keep
their data consistent. Validation lives in `clean()` and `save()` rather than
only in forms, so the constraints hold however a row is written - admin
dashboard, web form, API request or the shell.
"""

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class Publisher(models.Model):
    """A news organisation that employs editors and journalists.

    Editors and journalists are separate many-to-many relations rather than one
    combined list, because a person may work for several publishers and the two
    roles must stay distinguishable when deciding who may approve an article.
    """

    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)

    editors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="publisher_editor_roles",
        blank=True,
    )

    journalists = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="publisher_journalist_roles",
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """Return the publisher name shown in the admin and templates."""
        return self.name


class User(AbstractUser):
    """The project's user account, extended with a news-app role.

    Subclassing `AbstractUser` is what lets `AUTH_USER_MODEL` point here. It
    is also why every relation to a user references `settings.AUTH_USER_MODEL`
    instead of importing `User` - Django needs that indirection to resolve the
    swapped model.
    """

    class Role(models.TextChoices):
        """The three roles an account can hold.

        `READER` is the default, so a freshly registered account can neither
        publish nor approve until someone promotes it.
        """

        READER = "reader", "Reader"
        EDITOR = "editor", "Editor"
        JOURNALIST = "journalist", "Journalist"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.READER,
    )

    subscribed_publishers = models.ManyToManyField(
        Publisher,
        related_name="subscribers",
        blank=True,
    )

    subscribed_journalists = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="journalist_subscribers",
        blank=True,
        limit_choices_to={"role": "journalist"},
    )

    def save(self, *args, **kwargs):
        """Save the account, then remove subscriptions it should not hold.

        Only readers subscribe. The `clear()` calls must come *after*
        `super().save()` because many-to-many relations live in their own table
        keyed on this row's primary key, which does not exist until the save
        has run.
        """
        super().save(*args, **kwargs)

        # Only readers should have subscriptions.
        if self.role != self.Role.READER:
            self.subscribed_publishers.clear()
            self.subscribed_journalists.clear()

    def __str__(self):
        """Return the username with its role, e.g. `brett (Editor)`."""
        return f"{self.username} ({self.get_role_display()})"


class Article(models.Model):
    """A single news article, pending or approved.

    An article belongs either to a journalist working alone or to a publisher
    as an organisation, never both - so `author` and `publisher` are both
    nullable and `clean()` enforces the either/or rule.

    Both foreign keys use `on_delete=SET_NULL`: a journalist leaving or a
    publisher being deleted must not take already-published articles with them.
    `approved` defaults to `False`, making publication an explicit editor
    decision.
    """

    title = models.CharField(max_length=250)
    content = models.TextField()

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
    )

    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        """Reject impossible ownership combinations.

        `bool(self.author_id) == bool(self.publisher_id)` is true when both are
        set or neither is - precisely the invalid pair, since the rule is
        "exactly one owner".

        The test reads `author_id`, the raw key value, rather than `author`.
        Following the relation would issue a database query on every
        validation and would raise on an unsaved instance.
        """
        super().clean()

        # An article must belong to a journalist OR a publisher.
        if bool(self.author_id) == bool(self.publisher_id):
            raise ValidationError(
                "Choose exactly one: a journalist author or a publisher."
            )

        if self.author_id and self.author.role != User.Role.JOURNALIST:
            raise ValidationError(
                {"author": "Only journalists can author independent articles."}
            )

    def save(self, *args, **kwargs):
        """Validate before every write.

        Django only runs `full_clean()` inside forms, never automatically on
        `save()`. Calling it here keeps the "exactly one owner" rule enforcing
        itself for objects created straight through the ORM or the API.
        """
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        """Return the article title."""
        return self.title


class Newsletter(models.Model):
    """A collection of articles issued to subscribers.

    `author` cascades, since an edition without its owner has no meaning, while
    `articles` is many-to-many so one article can feature in several
    newsletters and deleting an edition never deletes the articles inside it.
    """

    title = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="newsletters",
    )

    articles = models.ManyToManyField(
        Article,
        related_name="newsletters",
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        """Restrict newsletter authorship to journalists and editors.

        A reader must not be able to send editions to subscribers. Enforcing it
        on the model means no form, serializer or admin edit can bypass the
        rule.
        """
        super().clean()

        if self.author_id and self.author.role not in (
            User.Role.JOURNALIST,
            User.Role.EDITOR,
        ):
            raise ValidationError(
                {
                    "author": (
                        "Only journalists and editors "
                        "can create newsletters."
                    )
                }
            )

    def __str__(self):
        """Return the newsletter title."""
        return self.title


class ApprovedArticleLog(models.Model):
    """An audit entry written each time an article is approved.

    `article_title` is copied onto the log instead of being read through the
    relation, so the entry stays legible in the admin if the article is later
    renamed. The log cascades with its article, making it a record of current
    content rather than a permanent history.
    """

    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="approval_logs",
    )
    article_title = models.CharField(max_length=250)
    received_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(
        max_length=100,
        default="internal-approval-workflow",
    )

    def __str__(self):
        """Return a summary line naming the approved article."""
        return f"Approval received: {self.article_title}"
