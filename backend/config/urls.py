"""URL configuration for candidate_platform_django."""
from django.urls import path, include

urlpatterns = [
    path("api/", include("candidates.urls")),
]
