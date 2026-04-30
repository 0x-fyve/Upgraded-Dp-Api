import hashlib
import base64
import secrets
from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import json

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

def github_callback(request):
    code = request.GET.get("code")
    
    stored_state = request.session.get("oauth_state")
    incoming_state = request.GET.get("state")

    if not stored_state or stored_state != incoming_state:
        return JsonResponse(
            {"status": "error", "message": "Invalid state"},
            status=400
        )

    code_verifier = request.session.get("code_verifier")

    github_token = exchange_code_for_token(code, code_verifier)

    if not github_token:
        return JsonResponse({"status": "error", "message": "GitHub auth failed"}, status=502)

    user_data = get_github_user(github_token)
    user = create_or_update_user(user_data)

    access, refresh = create_tokens(user)

    return JsonResponse({
        "status": "success",
        "access_token": access,
        "refresh_token": refresh
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

@csrf_exempt
def github_exchange(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    body = json.loads(request.body)
    code = body.get("code")
    code_verifier = body.get("code_verifier")

    if not code or not code_verifier:
        return JsonResponse({"status": "error", "message": "Missing params"}, status=400)

    # 1. exchange code with GitHub
    # 2. get user info
    # 3. create/update user
    # 4. issue tokens

    access, refresh = create_tokens(user)

    return JsonResponse({
        "status": "success",
        "access_token": access,
        "refresh_token": refresh
    })