from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class Publisher(models.Model):
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
        return self.name


class User(AbstractUser):
    class Role(models.TextChoices):
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
        super().save(*args, **kwargs)

        # Only readers should have subscriptions.
        if self.role != self.Role.READER:
            self.subscribed_publishers.clear()
            self.subscribed_journalists.clear()

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Article(models.Model):
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
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Newsletter(models.Model):
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
        return self.title


class ApprovedArticleLog(models.Model):
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
        return f"Approval received: {self.article_title}"
