from django.urls import path
from . import views


urlpatterns = [
    path("api/profiles", views.get_profiles),
    path("api/profiles/search", views.search_profiles),
    path("profiles", views.profile),
    path("api/profiles/export", views.export_profiles),
    path("api/profiles/<uuid:id>/delete", views.delete_profile),
]