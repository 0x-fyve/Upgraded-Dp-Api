from django.http import JsonResponse
from users.models import User


def analyst_or_admin(view_func):

    def wrapper(request, *args, **kwargs):

        user = getattr(request, "user", None)

        if not user or not getattr(user, "id", None):
            return JsonResponse({"status": "error", "message": "Auth required"}, status=401)

        role = User.objects.filter(id=user.id).values_list("role", flat=True).first()

        if role not in ["admin", "analyst"]:
            return JsonResponse({"status": "error", "message": "Forbidden"}, status=403)

        return view_func(request, *args, **kwargs)

    return wrapper


def admin_required(view_func):

    def wrapper(request, *args, **kwargs):

        user = getattr(request, "user", None)

        if not user or not getattr(user, "id", None):
            return JsonResponse({"status": "error", "message": "Auth required"}, status=401)

        role = User.objects.filter(id=user.id).values_list("role", flat=True).first()

        if role != "admin":
            return JsonResponse({"status": "error", "message": "Forbidden"}, status=403)

        return view_func(request, *args, **kwargs)

    return wrapper