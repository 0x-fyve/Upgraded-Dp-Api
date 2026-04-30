from django.http import JsonResponse
from authentication.tokens import verify_token


class AuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # Only protect API routes
        if request.path.startswith("/api/") and not request.path.startswith("/api/auth/"):

            auth_header = request.headers.get("Authorization")

            if not auth_header:
                return JsonResponse(
                    {"status": "error", "message": "Authentication required"},
                    status=401
                )

            try:
                token = auth_header.split(" ")[1]
            except Exception:
                return JsonResponse(
                    {"status": "error", "message": "Invalid token format"},
                    status=401
                )

            user = verify_token(token, "access")

            if not user:
                return JsonResponse(
                    {"status": "error", "message": "Invalid or expired token"},
                    status=401
                )

            if not user.is_active:
                return JsonResponse(
                    {"status": "error", "message": "User inactive"},
                    status=403
                )

            # 🔥 IMPORTANT: FORCE REAL USER (NO LAZY OBJECT)
            if request.path.startswith("/api/"):
                request.user = user

        # API version check
        if request.path.startswith("/api/"):
            version = request.headers.get("X-API-Version")

            if version != "1":
                return JsonResponse(
                    {"status": "error", "message": "API version header required"},
                    status=400
                )

        return self.get_response(request)