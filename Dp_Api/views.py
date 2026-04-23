import json
from django.http import JsonResponse
from .models import Profile

# -------------------------
# Serialize
# -------------------------
def serialize(p):
    return {
        "id": str(p.id),
        "name": p.name,
        "gender": p.gender,
        "gender_probability": p.gender_probability,
        "age": p.age,
        "age_group": p.age_group,
        "country_id": p.country_id,
        "country_name": p.country_name,
        "country_probability": p.country_probability,
        "created_at": p.created_at.isoformat().replace("+00:00", "Z"),
    }

# -------------------------
# Helpers
# -------------------------
def to_int(v):
    try:
        return int(v)
    except:
        return None

def to_float(v):
    try:
        return float(v)
    except:
        return None


# -------------------------
# GET /api/profiles
# -------------------------
def get_profiles(request):

    if request.method == "HEAD":
        return JsonResponse({}, status=200)

    if request.method != "GET":
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    qs = Profile.objects.all()

    # filters
    gender = request.GET.get("gender")
    age_group = request.GET.get("age_group")
    country_id = request.GET.get("country_id")

    if gender:
        qs = qs.filter(gender__iexact=gender)

    if age_group:
        qs = qs.filter(age_group__iexact=age_group)

    if country_id:
        qs = qs.filter(country_id__iexact=country_id)

    min_age = to_int(request.GET.get("min_age"))
    max_age = to_int(request.GET.get("max_age"))

    if min_age is not None:
        qs = qs.filter(age__gte=min_age)

    if max_age is not None:
        qs = qs.filter(age__lte=max_age)

    min_gp = to_float(request.GET.get("min_gender_probability"))
    if min_gp is not None:
        qs = qs.filter(gender_probability__gte=min_gp)

    min_cp = to_float(request.GET.get("min_country_probability"))
    if min_cp is not None:
        qs = qs.filter(country_probability__gte=min_cp)

    # sorting
    sort_by = request.GET.get("sort_by", "created_at")
    order = request.GET.get("order", "asc")

    allowed = ["age", "created_at", "gender_probability"]
    if sort_by not in allowed:
        return JsonResponse({"status": "error", "message": "Invalid query parameters"}, status=422)

    if order == "desc":
        sort_by = f"-{sort_by}"

    qs = qs.order_by(sort_by)

    # pagination
    page = to_int(request.GET.get("page")) or 1
    limit = to_int(request.GET.get("limit")) or 10
    if limit > 50:
        limit = 50

    start = (page - 1) * limit
    end = start + limit

    total = qs.count()
    data = qs[start:end]

    return JsonResponse({
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "data": [serialize(p) for p in data]
    })


# -------------------------
# NLP Parser
# -------------------------
COUNTRIES = {
    "nigeria": "NG",
    "kenya": "KE",
    "angola": "AO",
    "ghana": "GH",
    "usa": "US",
}

def parse_query(q):
    q = q.lower()
    filters = {}

    # -------- GENDER --------
    genders = []
    if "male" in q:
        genders.append("male")
    if "female" in q:
        genders.append("female")

    if genders:
        filters["gender"] = genders  # supports multiple

    # -------- AGE GROUP --------
    if "child" in q:
        filters["age_group"] = "child"
    elif "teenager" in q:
        filters["age_group"] = "teenager"
    elif "adult" in q:
        filters["age_group"] = "adult"
    elif "senior" in q:
        filters["age_group"] = "senior"

    # -------- "young" --------
    if "young" in q:
        filters["min_age"] = 16
        filters["max_age"] = 24

    # -------- "above X" --------
    words = q.split()
    for i, w in enumerate(words):
        if w == "above" and i + 1 < len(words):
            try:
                filters["min_age"] = int(words[i + 1])
            except:
                pass

    # -------- COUNTRY --------
    COUNTRIES = {
        "nigeria": "NG",
        "kenya": "KE",
        "angola": "AO",
        "ghana": "GH",
        "uganda": "UG",
        "tanzania": "TZ",
        "usa": "US",
        "united states": "US",
        "uk": "GB",
        "united kingdom": "GB",
    }

    for name, code in COUNTRIES.items():
        if name in q:
            filters["country_id"] = code

    return filters if filters else None
    

# -------------------------
# GET /api/profiles/search
# -------------------------
def search_profiles(request):

    if request.method != "GET":
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    q = request.GET.get("q")
    if not q:
        return JsonResponse({"status": "error", "message": "Missing query"}, status=400)

    filters = parse_query(q)
    if not filters:
        return JsonResponse({"status": "error", "message": "Unable to interpret query"}, status=400)
    
    

    qs = Profile.objects.all()

    if "gender" in filters:
        qs = qs.filter(gender=filters["gender"])
    if "age_group" in filters:
        qs = qs.filter(age_group=filters["age_group"])
    if "min_age" in filters:
        qs = qs.filter(age__gte=filters["min_age"])
    if "max_age" in filters:
        qs = qs.filter(age__lte=filters["max_age"])
    if "country_id" in filters:
        qs = qs.filter(country_id=filters["country_id"])
    if "gender" in filters:
        rqs = qs.filter(gender__in=filters["gender"])    


    # pagination
    page = to_int(request.GET.get("page")) or 1
    limit = to_int(request.GET.get("limit")) or 10
    if limit > 50:
        limit = 50

    start = (page - 1) * limit
    end = start + limit

    total = qs.count()
    data = qs[start:end]

    return JsonResponse({
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "data": [serialize(p) for p in data]
    })