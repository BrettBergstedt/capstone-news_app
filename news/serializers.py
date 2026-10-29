
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from .models import Article, Publisher, Newsletter, ApprovedArticleLog, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role"]
        read_only_fields = fields


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        return User.objects.create_user(
            role=User.Role.READER,
            **validated_data,
        )


class PublisherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publisher
        fields = ["id", "name", "description", "created_at"]


class ArticleSerializer(serializers.ModelSerializer):
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
        for article in articles:
            if not article.approved:
                raise serializers.ValidationError(
                    f"Article '{article.title}' has not been approved."
                )
        return articles


class ApprovedArticleLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovedArticleLog
        fields = ["id", "article", "article_title", "received_at", "source"]
        read_only_fields = fields
