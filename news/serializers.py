"""Serializers that define the shape of the News API's JSON responses.

Each class converts a Django model instance to and from JSON for the
REST endpoints, and controls which fields a client may write. The
`read_only_fields` lists are the security boundary of the API: anything not
listed there can be set by whoever calls the endpoint.
"""

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from .models import Article, Publisher, Newsletter, ApprovedArticleLog, User


class UserSerializer(serializers.ModelSerializer):
    """Public, read-only view of a user account.

    Every field is read-only, so this serializer can expose a user's role in a
    response without allowing a client to change it through the API.
    """

    class Meta:
        model = User
        fields = ["id", "username", "email", "role"]
        read_only_fields = fields


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Accepts new reader sign-ups and creates the account safely.

    `password` is write-only, so it is never echoed back in a response, and is
    checked against Django's password validators before saving.
    """

    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        """Create the user with a hashed password and the default reader role.

        Uses `create_user`, not `create`, so Django hashes the password;
        writing through `create` would store it in plain text.
        """
        return User.objects.create_user(
            role=User.Role.READER,
            **validated_data,
        )


class PublisherSerializer(serializers.ModelSerializer):
    """Read and write representation of a publisher."""

    class Meta:
        model = Publisher
        fields = ["id", "name", "description", "created_at"]


class ArticleSerializer(serializers.ModelSerializer):
    """Article representation used by the API.

    Adds flattened `author_username` and `publisher_name` so clients do not
    have to follow related objects themselves. The approval flag and authorship
    are read-only: a journalist cannot approve their own article or reassign
    who wrote it by posting a different value.
    """

    author_username = serializers.CharField(
        source="author.username",
        read_only=True,
        default=None,
    )
    publisher_name = serializers.CharField(
        source="publisher.name",
        read_only=True,
        default=None,
    )

    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "content",
            "author",
            "author_username",
            "publisher",
            "publisher_name",
            "created_at",
            "updated_at",
            "approved",
        ]
        read_only_fields = [
            "id",
            "author",
            "created_at",
            "updated_at",
            "approved",
        ]


class NewsletterSerializer(serializers.ModelSerializer):
    """Newsletter representation for the API.

    `author` and `created_at` are read-only so a client cannot claim someone
    else's newsletter.
    """

    class Meta:
        model = Newsletter
        fields = [
            "id",
            "title",
            "description",
            "author",
            "articles",
            "created_at",
        ]
        read_only_fields = ["id", "author", "created_at"]

    def validate_articles(self, articles):
        """Reject the submission if any chosen article is still unapproved.

        This is the API's only guarantee that unreviewed work cannot be
        published, so it is enforced here rather than relying on the form or
        view to filter the list first.
        """
        for article in articles:
            if not article.approved:
                raise serializers.ValidationError(
                    f"Article '{article.title}' has not been approved."
                )
        return articles


class ApprovedArticleLogSerializer(serializers.ModelSerializer):
    """Read-only audit trail of articles approved by the editor.

    Every field is read-only because the log is written by the application
    when an approval happens; allowing clients to post to it would defeat its
    purpose as evidence.
    """

    class Meta:
        model = ApprovedArticleLog
        fields = ["id", "article", "article_title", "received_at", "source"]
        read_only_fields = fields
