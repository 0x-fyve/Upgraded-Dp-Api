import hashlib
import base64
import secrets
from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import json
import requests
from .services import exchange_code_for_token, get_github_user, create_or_update_user
from .tokens import create_tokens, verify_token, blacklist_token

def github_login(request):
    state = secrets.token_urlsafe(16)
    code_verifier = secrets.token_urlsafe(64)

    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip("=")

    request.session["oauth_state"] = state
    request.session["code_verifier"] = code_verifier

    request.session.save()   # ✅ VERY IMPORTANT

    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&state={state}"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
    )

    return redirect(url)

import requests
import json
from django.http import JsonResponse
from django.conf import settings
from users.models import User
from authentication.tokens import create_tokens


def github_callback(request):
    # GitHub sends code via GET
    code = request.GET.get("code")

    # CLI sends verifier via POST body
    body = json.loads(request.body or "{}")
    code_verifier = body.get("code_verifier")

    if not code or not code_verifier:
        return JsonResponse({
            "status": "error",
            "message": "Missing code or code_verifier"
        }, status=400)

    # Exchange code for GitHub access token
    token_res = requests.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": code,
            "code_verifier": code_verifier,
        }
    ).json()

    github_access_token = token_res.get("access_token")

    if not github_access_token:
        return JsonResponse({
            "status": "error",
            "message": "GitHub token exchange failed"
        }, status=400)

    # Get user info
    user_data = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {github_access_token}"}
    ).json()

    github_id = user_data["id"]
    username = user_data["login"]
    email = user_data.get("email")

    # Create or update user
    user, _ = User.objects.get_or_create(
        github_id=github_id,
        defaults={
            "username": username,
            "email": email,
            "role": "analyst"
        }
    )

    # Issue YOUR system tokens
    access, refresh = create_tokens(user)

    return JsonResponse({
        "status": "success",
        "access_token": access,
        "refresh_token": refresh,
        "username": user.username
    })



@csrf_exempt
def refresh_token(request):

    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "Method not allowed"},
            status=405
        )

    if not request.body:
        return JsonResponse(
            {"status": "error", "message": "Request body required"},
            status=400
        )

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"status": "error", "message": "Invalid JSON"},
            status=400
        )

    old_refresh = body.get("refresh_token")

    if not old_refresh:
        return JsonResponse(
            {"status": "error", "message": "Refresh token required"},
            status=400
        )

    user = verify_token(old_refresh, "refresh")

    if not user:
        return JsonResponse(
            {"status": "error", "message": "Invalid or expired token"},
            status=401
        )

    # 🔥 rotate token (required by spec)
    blacklist_token(old_refresh)

    access, new_refresh = create_tokens(user)

    return JsonResponse({
        "status": "success",
        "access_token": access,
        "refresh_token": new_refresh
    })

@csrf_exempt
def logout(request):

    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "Method not allowed"},
            status=405
        )

    if not request.body:
        return JsonResponse(
            {"status": "error", "message": "Request body required"},
            status=400
        )

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"status": "error", "message": "Invalid JSON"},
            status=400
        )

    refresh = body.get("refresh_token")

    if not refresh:
        return JsonResponse(
            {"status": "error", "message": "Refresh token required"},
            status=400
        )

    # optional: validate before blacklist
    user = verify_token(refresh, "refresh")
    if not user:
        return JsonResponse(
            {"status": "error", "message": "Invalid token"},
            status=401
        )

    blacklist_token(refresh)

    return JsonResponse({"status": "success"})
