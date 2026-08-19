"""candidates/urls.py — URL patterns for all candidate endpoints."""
from django.urls import path
from . import views

urlpatterns = [
    # Health
    path("health", views.HealthView.as_view(), name="health"),

    # Ingestion
    path("candidates/from-csv", views.IngestCSVView.as_view(), name="ingest-csv"),
    path("candidates/from-resume", views.IngestResumeView.as_view(), name="ingest-resume"),

    # Search (must come BEFORE <candidate_id> to avoid route collision)
    path("candidates/search", views.SemanticSearchView.as_view(), name="candidate-search"),

    # Merge
    path("candidates/merge", views.MergeCandidatesView.as_view(), name="candidate-merge"),

    # List + Clear all
    path("candidates", views.CandidateListView.as_view(), name="candidate-list"),

    # Single candidate CRUD
    path("candidates/<str:candidate_id>", views.CandidateDetailView.as_view(), name="candidate-detail"),
    path("candidates/<str:candidate_id>/confidence", views.CandidateConfidenceView.as_view(), name="candidate-confidence"),
    path("candidates/<str:candidate_id>/enrich", views.EnrichCandidateView.as_view(), name="candidate-enrich"),
]
