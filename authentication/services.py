import requests
from django.conf import settings
from users.models import User


def exchange_code_for_token(code, code_verifier=None):
    data = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "client_secret": settings.GITHUB_CLIENT_SECRET,
        "code": code,
    }

    if code_verifier:
        data["code_verifier"] = code_verifier

    headers = {"Accept": "application/json"}

    res = requests.post(
        "https://github.com/login/oauth/access_token",
        data=data,
        headers=headers
    )

    return res.json().get("access_token")


def get_github_user(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    user_res = requests.get("https://api.github.com/user", headers=headers)
    user_data = user_res.json()

    return user_data


def create_or_update_user(data):
    user, _ = User.objects.update_or_create(
        github_id=str(data["id"]),
        defaults={
            "username": data["login"],
            "email": data.get("email"),
            "avatar_url": data.get("avatar_url"),
        }
    )
    return user