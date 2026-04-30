import json
from django.http import JsonResponse
from .models import Profile
from core.permissions import admin_required
from core.permissions import analyst_or_admin
import requests
import csv
from django.http import HttpResponse
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from users.models import User
import pycountry
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

def get_country_name(code):
    try:
        country = pycountry.countries.get(alpha_2=code)
        return country.name if country else None
    except:
        return None
    

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
    

def get_age_group(age):
    if age <= 12:
        return "child"
    elif age <= 19:
        return "teenager"
    elif age <= 59:
        return "adult"
    return "senior"


def get_top_country(countries):
    if not countries:
        return None, None

    top = max(countries, key=lambda x: x["probability"])
    return top["country_id"], top["probability"]     


# -------------------------
# GET /api/profiles
# -------------------------
@csrf_exempt
@analyst_or_admin
def get_profiles(request):

    if request.method == "HEAD":
        return JsonResponse({}, status=200)

    if request.method == "GET":
        

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
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 10))

        if limit > 50:
            limit = 50

        start = (page - 1) * limit
        end = start + limit

        total = qs.count()
        total_pages = (total + limit - 1) // limit

        data = qs[start:end]

        return JsonResponse({
            "status": "success",
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
            "links": {
            "self": f"/api/profiles?page={page}&limit={limit}",
            "next": f"/api/profiles?page={page+1}&limit={limit}" if page < total_pages else None,
            "prev": f"/api/profiles?page={page-1}&limit={limit}" if page > 1 else None,
            },
            "data": [serialize(p) for p in data]
        })
    

    if request.method == "POST":
        
        role = User.objects.filter(id=request.user.id).values_list("role", flat=True).first()

        if role != "admin":
            return JsonResponse({"status": "error", "message": "Forbidden"}, status=403)

        
        data = json.loads(request.body)
        name = data.get("name")

        # validation
        if not name or not isinstance(name, str):
            return JsonResponse(
            {"status": "error", "message": "Missing or invalid name"},
                status=400
                )

        name = name.lower()

        # idempotency check (single query)
        profile = Profile.objects.filter(name=name).first()
        if profile:
            return JsonResponse({
                "status": "success",
                "message": "Profile already exists",
                "data": serialize(profile)
            }, status=200)

        # -------------------
        # EXTERNAL API CALLS
        # -------------------
        try:
            gender_res = requests.get(
                "https://api.genderize.io",
                params={"name": name},
                timeout=5
            )

            age_res = requests.get(
                "https://api.agify.io",
                params={"name": name},
                timeout=5
            )

            nat_res = requests.get(
                "https://api.nationalize.io",
                params={"name": name},
                timeout=5
            )

        except requests.exceptions.RequestException:
            return JsonResponse(
                {"status": "error", "message": "Failed to reach external service"},
                status=502
            )

        gender_data = gender_res.json()
        age_data = age_res.json()
        nat_data = nat_res.json()

        # -------------------
        # VALIDATION
        # -------------------
        if not gender_data.get("gender") or not gender_data.get("count"):
            return JsonResponse(
                {"status": "error", "message": "Genderize returned an invalid response"},
                status=502
            )

        if age_data.get("age") is None:
            return JsonResponse(
                {"status": "error", "message": "Agify returned an invalid response"},
                status=502
            )

        if not nat_data.get("country"):
            return JsonResponse(
                {"status": "error", "message": "Nationalize returned an invalid response"},
                status=502
            )

        # -------------------
        # PROCESS DATA
        # -------------------
        gender = gender_data["gender"]
        gender_probability = gender_data["probability"]
        sample_size = gender_data["count"]
        
    

        age = age_data["age"]
        age_group = get_age_group(age)

        country_id, country_probability = get_top_country(nat_data["country"])
        country_name = get_country_name(country_id)

        # -------------------
        # SAVE
        # -------------------
        profile = Profile.objects.create(
            name=name,
            gender=gender,
            gender_probability=gender_probability,
            age=age,
            age_group=age_group,
            country_id=country_id,
            country_name=country_name,
            country_probability=country_probability
        )

        return JsonResponse({
            "status": "success",
            "data": serialize(profile)
        }, status=201)

    


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
@csrf_exempt
@analyst_or_admin
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

   
    if "age_group" in filters:
        qs = qs.filter(age_group=filters["age_group"])
    if "min_age" in filters:
        qs = qs.filter(age__gte=filters["min_age"])
    if "max_age" in filters:
        qs = qs.filter(age__lte=filters["max_age"])
    if "country_id" in filters:
        qs = qs.filter(country_id=filters["country_id"])
    if "gender" in filters:
        qs = qs.filter(gender__in=filters["gender"])    


    # pagination

    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 10))

    if limit > 50:
        limit = 50

    start = (page - 1) * limit
    end = start + limit

    total = qs.count()
    total_pages = (total + limit - 1) // limit

    data = qs[start:end]

    return JsonResponse({
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
        "links": {
        "self": f"/api/profiles?page={page}&limit={limit}",
        "next": f"/api/profiles?page={page+1}&limit={limit}" if page < total_pages else None,
        "prev": f"/api/profiles?page={page-1}&limit={limit}" if page > 1 else None,
         },
        "data": [serialize(p) for p in data]
    })


@csrf_exempt
@analyst_or_admin
def profile(request):
    print("USER:", request.user)
    print("ROLE:", getattr(request.user, "role", None))

    if request.method == "POST":
        

        role = User.objects.filter(id=request.user.id).values_list("role", flat=True).first()

        if role != "admin":
            return JsonResponse({"status": "error", "message": "Forbidden"}, status=403)

        data = json.loads(request.body)
        name = data.get("name")

        # validation
        if not name or not isinstance(name, str):
            return JsonResponse(
            {"status": "error", "message": "Missing or invalid name"},
                status=400
                )

        name = name.lower()

        # idempotency check (single query)
        profile = Profile.objects.filter(name=name).first()
        if profile:
            return JsonResponse({
                "status": "success",
                "message": "Profile already exists",
                "data": serialize(profile)
            }, status=200)

        # -------------------
        # EXTERNAL API CALLS
        # -------------------
        try:
            gender_res = requests.get(
                "https://api.genderize.io",
                params={"name": name},
                timeout=5
            )

            age_res = requests.get(
                "https://api.agify.io",
                params={"name": name},
                timeout=5
            )

            nat_res = requests.get(
                "https://api.nationalize.io",
                params={"name": name},
                timeout=5
            )

        except requests.exceptions.RequestException:
            return JsonResponse(
                {"status": "error", "message": "Failed to reach external service"},
                status=502
            )

        gender_data = gender_res.json()
        age_data = age_res.json()
        nat_data = nat_res.json()

        # -------------------
        # VALIDATION
        # -------------------
        if not gender_data.get("gender") or not gender_data.get("count"):
            return JsonResponse(
                {"status": "error", "message": "Genderize returned an invalid response"},
                status=502
            )

        if age_data.get("age") is None:
            return JsonResponse(
                {"status": "error", "message": "Agify returned an invalid response"},
                status=502
            )

        if not nat_data.get("country"):
            return JsonResponse(
                {"status": "error", "message": "Nationalize returned an invalid response"},
                status=502
            )

        # -------------------
        # PROCESS DATA
        # -------------------
        gender = gender_data["gender"]
        gender_probability = gender_data["probability"]
        sample_size = gender_data["count"]

        age = age_data["age"]
        age_group = get_age_group(age)

        country_id, country_probability = get_top_country(nat_data["country"])

        # -------------------
        # SAVE
        # -------------------
        profile = Profile.objects.create(
            name=name,
            gender=gender,
            gender_probability=gender_probability,
            sample_size=sample_size,
            age=age,
            age_group=age_group,
            country_id=country_id,
            country_probability=country_probability
        )

        return JsonResponse({
            "status": "success",
            "data": serialize(profile)
        }, status=201)


@csrf_exempt
@admin_required
def delete_profile(request, id):

    if request.method != "DELETE":
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    profile = Profile.objects.filter(id=id).first()

    if not profile:
        return JsonResponse(
            {"status": "error", "message": "Profile not found"},
            status=404
        )

    profile.delete()

    return JsonResponse({"status": "success"}, status=204)

@csrf_exempt
@analyst_or_admin
def export_profiles(request):

    if request.GET.get("format") != "csv":
        return JsonResponse(
            {"status": "error", "message": "Invalid format"},
            status=400
        )

    profiles = Profile.objects.all()

    # apply SAME filters as GET (reuse your logic)

    response = HttpResponse(content_type="text/csv")
    filename = f'profiles_{datetime.utcnow().isoformat()}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    writer.writerow([
        "id", "name", "gender", "gender_probability",
        "age", "age_group", "country_id", "country_name",
        "country_probability", "created_at"
    ])

    for p in profiles:
        writer.writerow([
            str(p.id),
            p.name,
            p.gender,
            p.gender_probability,
            p.age,
            p.age_group,
            p.country_id,
            p.country_name,
            p.country_probability,
            p.created_at.isoformat()
        ])

    return response
