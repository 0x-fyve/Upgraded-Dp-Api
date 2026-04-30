from django.urls import path
from .views import github_login, github_callback, refresh_token, logout

urlpatterns = [
    path("github", github_login),
    path("github/callback", github_callback),
    path("refresh", refresh_token),
    path("logout", logout),
]