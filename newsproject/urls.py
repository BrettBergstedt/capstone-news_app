
from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views as auth_views
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path("", include("news.web_urls", namespace="web")),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("admin/", admin.site.urls),
    path("api/token/", obtain_auth_token, name="api-token"),
    path("api/", include("news.urls")),
    path("api-auth/", include("rest_framework.urls")),
]
