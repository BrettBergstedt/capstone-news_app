
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from unittest.mock import patch

from .models import User, Publisher, Article, Newsletter, ApprovedArticleLog


class NewsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.reader = User.objects.create_user(
            username="reader_test",
            password="TestPass123!",
            role=User.Role.READER,
        )

        self.journalist = User.objects.create_user(
            username="journalist_test",
            password="TestPass123!",
            role=User.Role.JOURNALIST,
        )

        self.editor = User.objects.create_user(
            username="editor_test",
            password="TestPass123!",
            role=User.Role.EDITOR,
        )

        self.publisher = Publisher.objects.create(
            name="Test Publisher",
            description="Publisher used for testing.",
        )

    def test_new_users_are_added_to_their_role_group(self):
        self.assertEqual(
            list(self.reader.groups.values_list("name", flat=True)),
            [User.Role.READER],
        )
        self.assertEqual(
            list(self.journalist.groups.values_list("name", flat=True)),
            [User.Role.JOURNALIST],
        )

    def test_changing_role_updates_the_users_group(self):
        self.reader.role = User.Role.JOURNALIST
        self.reader.save()

        self.assertEqual(
            list(self.reader.groups.values_list("name", flat=True)),
            [User.Role.JOURNALIST],
        )

    def test_role_groups_have_the_expected_article_permissions(self):
        reader_permissions = set(
            self.reader.groups.get(name=User.Role.READER)
            .permissions.filter(content_type__app_label="news")
            .values_list("codename", flat=True)
        )
        journalist_permissions = set(
            self.journalist.groups.get(name=User.Role.JOURNALIST)
            .permissions.filter(content_type__app_label="news")
            .values_list("codename", flat=True)
        )

        self.assertEqual(
            reader_permissions,
            {"view_article", "view_newsletter"},
        )
        self.assertIn("add_article", journalist_permissions)
        self.assertIn("delete_newsletter", journalist_permissions)

    def test_user_can_obtain_api_token(self):
        response = self.client.post(
            "/api/token/",
            {
                "username": self.reader.username,
                "password": "TestPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertTrue(
            Token.objects.filter(
                key=response.data["token"],
                user=self.reader,
            ).exists()
        )

    def test_api_token_rejects_invalid_password(self):
        response = self.client.post(
            "/api/token/",
            {
                "username": self.reader.username,
                "password": "wrong-password",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_authenticated_user_can_view_own_profile(self):
        self.client.force_authenticate(user=self.reader)

        response = self.client.get("/api/users/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], self.reader.username)
        self.assertEqual(response.data["role"], User.Role.READER)
        self.assertNotIn("password", response.data)

    def test_public_registration_creates_reader_and_hashes_password(self):
        response = self.client.post(
            "/api/users/register/",
            {
                "username": "new_reader",
                "email": "new@example.com",
                "password": "ReaderPass#2026",
                "role": User.Role.EDITOR,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_user = User.objects.get(username="new_reader")
        self.assertEqual(created_user.role, User.Role.READER)
        self.assertTrue(created_user.check_password("ReaderPass#2026"))
        self.assertNotIn("password", response.data)

    def test_publishers_can_be_listed_publicly(self):
        response = self.client.get("/api/publishers/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["name"], self.publisher.name)

    def test_home_page_displays_only_approved_articles(self):
        Article.objects.create(
            title="Visible Web Story",
            content="This story is public.",
            publisher=self.publisher,
            approved=True,
        )
        Article.objects.create(
            title="Hidden Web Draft",
            content="This story is not approved.",
            publisher=self.publisher,
            approved=False,
        )

        response = self.client.get("/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Visible Web Story")
        self.assertNotContains(response, "Hidden Web Draft")

    def test_journalist_can_submit_article_through_website(self):
        self.client.login(
            username=self.journalist.username,
            password="TestPass123!",
        )

        response = self.client.post(
            "/articles/submit/",
            {"title": "Web Submission", "content": "Submitted for review."},
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertTrue(
            Article.objects.filter(
                title="Web Submission",
                author=self.journalist,
                approved=False,
            ).exists()
        )

    @patch("news.views.requests.post")
    @patch("news.views.send_mail")
    def test_editor_can_approve_article_through_website(
        self, mock_send_mail, mock_requests_post
    ):
        article = Article.objects.create(
            title="Web Approval Story",
            content="Ready for review.",
            author=self.journalist,
        )
        self.client.login(
            username=self.editor.username,
            password="TestPass123!",
        )

        response = self.client.post(f"/editor/articles/{article.pk}/approve/")

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        article.refresh_from_db()
        self.assertTrue(article.approved)
        mock_requests_post.assert_called_once()

    def test_reader_cannot_create_article(self):
        self.client.force_authenticate(user=self.reader)

        response = self.client.post(
            "/api/articles/",
            {
                "title": "Reader Article",
                "content": "This should not be created.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_journalist_can_create_article(self):
        self.client.force_authenticate(user=self.journalist)

        response = self.client.post(
            "/api/articles/",
            {
                "title": "My Test Article",
                "content": "This is test content.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            Article.objects.filter(
                title="My Test Article",
                author=self.journalist,
                approved=False,
            ).exists()
        )

    def test_editor_can_update_and_delete_an_article(self):
        article = Article.objects.create(
            title="Submitted Story",
            content="Waiting for an editor.",
            author=self.journalist,
        )
        self.client.force_authenticate(user=self.editor)

        update_response = self.client.patch(
            f"/api/articles/{article.pk}/",
            {"title": "Edited Story"},
            format="json",
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        article.refresh_from_db()
        self.assertEqual(article.title, "Edited Story")

        delete_response = self.client.delete(f"/api/articles/{article.pk}/")
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Article.objects.filter(pk=article.pk).exists())

    def test_journalist_cannot_update_another_journalists_article(self):
        other_journalist = User.objects.create_user(
            username="other_journalist",
            password="TestPass123!",
            role=User.Role.JOURNALIST,
        )
        article = Article.objects.create(
            title="Someone Else's Draft",
            content="This draft belongs to another journalist.",
            author=other_journalist,
        )
        self.client.force_authenticate(user=self.journalist)

        response = self.client.patch(
            f"/api/articles/{article.pk}/",
            {"title": "Unauthorized edit"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_public_list_shows_only_approved_articles(self):
        Article.objects.create(
            title="Approved Story",
            content="Visible to the public.",
            publisher=self.publisher,
            approved=True,
        )

        Article.objects.create(
            title="Unapproved Story",
            content="Not visible to the public.",
            publisher=self.publisher,
            approved=False,
        )

        response = self.client.get("/api/articles/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        titles = [item["title"] for item in response.data]

        self.assertIn("Approved Story", titles)
        self.assertNotIn("Unapproved Story", titles)

    def test_reader_sees_only_approved_subscribed_articles(self):
        other_publisher = Publisher.objects.create(
            name="Other Publisher",
            description="Not subscribed to.",
        )
        self.reader.subscribed_publishers.add(self.publisher)
        self.reader.subscribed_journalists.add(self.journalist)

        Article.objects.create(
            title="Subscribed Publisher Story",
            content="From a subscribed publisher.",
            publisher=self.publisher,
            approved=True,
        )
        Article.objects.create(
            title="Subscribed Journalist Story",
            content="From a subscribed journalist.",
            author=self.journalist,
            approved=True,
        )
        Article.objects.create(
            title="Unsubscribed Publisher Story",
            content="From another publisher.",
            publisher=other_publisher,
            approved=True,
        )
        Article.objects.create(
            title="Subscribed Draft Story",
            content="Not approved yet.",
            publisher=self.publisher,
            approved=False,
        )

        self.client.force_authenticate(user=self.reader)
        response = self.client.get("/api/articles/subscribed/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = {item["title"] for item in response.data}
        self.assertEqual(
            titles,
            {
                "Subscribed Publisher Story",
                "Subscribed Journalist Story",
            },
        )

    def test_non_reader_cannot_access_subscribed_articles(self):
        self.client.force_authenticate(user=self.journalist)

        response = self.client.get("/api/articles/subscribed/")

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_reader_can_subscribe_to_publisher(self):
        self.client.force_authenticate(user=self.reader)

        response = self.client.post(
            "/api/subscriptions/",
            {
                "type": "publisher",
                "id": self.publisher.id,
                "action": "subscribe",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            self.reader.subscribed_publishers.filter(
                id=self.publisher.id
            ).exists()
        )

    def test_reader_cannot_create_newsletter(self):
        self.client.force_authenticate(user=self.reader)

        response = self.client.post(
            "/api/newsletters/",
            {
                "title": "Reader Newsletter",
                "description": "This should be rejected.",
                "articles": [],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_newsletter_rejects_unapproved_articles(self):
        article = Article.objects.create(
            title="Draft Story",
            content="Not yet approved.",
            publisher=self.publisher,
            approved=False,
        )

        newsletter = Newsletter(
            title="Test Newsletter",
            description="Testing article validation.",
            author=self.editor,
        )

        from .serializers import NewsletterSerializer

        serializer = NewsletterSerializer(
            data={
                "title": newsletter.title,
                "description": newsletter.description,
                "articles": [article.id],
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("articles", serializer.errors)

    @patch("news.views.requests.post")
    @patch("news.views.send_mail")
    def test_editor_can_approve_article_and_notify_subscribers(
        self, mock_send_mail, mock_requests_post
    ):
        reader = User.objects.create_user(
            username="subscriber_test",
            password="TestPass123!",
            email="reader@example.com",
            role=User.Role.READER,
        )
        reader.subscribed_publishers.add(self.publisher)

        article = Article.objects.create(
            title="Approval Test Story",
            content="Test article content.",
            publisher=self.publisher,
            approved=False,
        )

        self.client.force_authenticate(user=self.editor)

        response = self.client.post(
            f"/api/articles/{article.id}/approve/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        article.refresh_from_db()
        self.assertTrue(article.approved)
        mock_send_mail.assert_called_once()
        mock_requests_post.assert_called_once()

    @override_settings(APPROVAL_CALLBACK_TOKEN="test-callback-secret")
    def test_approval_callback_rejects_missing_token(self):
        response = self.client.post(
            "/api/approved/",
            {"article": 1, "article_title": "Test Story"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_newsletter_author_can_update_and_delete_newsletter(self):
        newsletter = Newsletter.objects.create(
            title="My Newsletter",
            description="First version",
            author=self.journalist,
        )
        self.client.force_authenticate(user=self.journalist)

        update_response = self.client.patch(
            f"/api/newsletters/{newsletter.pk}/",
            {"title": "Updated Newsletter"},
            format="json",
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        newsletter.refresh_from_db()
        self.assertEqual(newsletter.title, "Updated Newsletter")

        delete_response = self.client.delete(
            f"/api/newsletters/{newsletter.pk}/"
        )
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Newsletter.objects.filter(pk=newsletter.pk).exists())

    def test_reader_cannot_update_newsletter(self):
        newsletter = Newsletter.objects.create(
            title="Editor Newsletter",
            description="For permission testing",
            author=self.journalist,
        )
        self.client.force_authenticate(user=self.reader)

        response = self.client.patch(
            f"/api/newsletters/{newsletter.pk}/",
            {"title": "Unauthorized change"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(ApprovedArticleLog.objects.count(), 0)

    @override_settings(APPROVAL_CALLBACK_TOKEN="test-callback-secret")
    def test_approval_callback_rejects_invalid_token(self):
        response = self.client.post(
            "/api/approved/",
            {"article": 1, "article_title": "Test Story"},
            format="json",
            HTTP_X_CALLBACK_TOKEN="wrong-token",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(ApprovedArticleLog.objects.count(), 0)

    @override_settings(APPROVAL_CALLBACK_TOKEN="test-callback-secret")
    def test_approval_callback_records_request_with_valid_token(self):
        article = Article.objects.create(
            title="Callback Test Story",
            content="Callback test content.",
            publisher=self.publisher,
        )

        response = self.client.post(
            "/api/approved/",
            {
                "article": article.id,
                "article_title": article.title,
                "source": "test-suite",
            },
            format="json",
            HTTP_X_CALLBACK_TOKEN="test-callback-secret",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ApprovedArticleLog.objects.count(), 1)
        self.assertEqual(
            ApprovedArticleLog.objects.get().article,
            article,
        )

    @override_settings(APPROVAL_CALLBACK_TOKEN="test-callback-secret")
    def test_approval_callback_rejects_missing_fields(self):
        response = self.client.post(
            "/api/approved/",
            {},
            format="json",
            HTTP_X_CALLBACK_TOKEN="test-callback-secret",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
