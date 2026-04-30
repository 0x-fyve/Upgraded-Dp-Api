import jwt
import datetime
from django.conf import settings
from users.models import User

SECRET = settings.SECRET_KEY

ACCESS_EXP = 18000000 # 3 minutes
REFRESH_EXP = 300  # 5 minutes

# In-memory blacklist (replace with Redis in prod)
BLACKLIST = set()


def create_tokens(user):
    now = datetime.datetime.utcnow()

    access_payload = {
        "user_id": str(user.id),
        "exp": now + datetime.timedelta(seconds=ACCESS_EXP),
        "type": "access"
    }

    refresh_payload = {
        "user_id": str(user.id),
        "exp": now + datetime.timedelta(seconds=REFRESH_EXP),
        "type": "refresh"
    }

    access = jwt.encode(access_payload, SECRET, algorithm="HS256")
    refresh = jwt.encode(refresh_payload, SECRET, algorithm="HS256")

    return access, refresh



def verify_token(token, expected_type):

    if token in BLACKLIST:
        return None

    try:
        payload = jwt.decode(
            token,
            SECRET,
            algorithms=["HS256"],
            leeway=10
        )

        if payload.get("type") != expected_type:
            return None

        user_id = payload.get("user_id")

        if not user_id:
            return None

        return User.objects.get(id=user_id)

    except Exception as e:
        print("JWT ERROR:", repr(e))
        return None


def blacklist_token(token):
    BLACKLIST.add(token)