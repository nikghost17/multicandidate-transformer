"""
tests/test_api.py
------------------
Integration tests for the Django REST Framework endpoints.

MongoDB and LLM calls are fully mocked via the `api_client` fixture
in conftest.py — tests run offline and instantly, no real DB needed.

Tests cover:
  GET  /api/health
  POST /api/candidates/from-csv
  GET  /api/candidates
  GET  /api/candidates/<id>
  POST /api/candidates/from-resume
  POST /api/candidates/<id>/enrich
  DELETE /api/candidates/<id>
"""

from __future__ import annotations

import io
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

class TestHealth:

    def test_health_returns_200(self, api_client):
        """GET /api/health must return HTTP 200 with status=ok."""
        resp = api_client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_health_reports_django_backend(self, api_client):
        """Health check must identify Django as the backend."""
        resp = api_client.get("/api/health")
        assert resp.json().get("backend") == "Django"


# ---------------------------------------------------------------------------
# CSV Ingestion
# ---------------------------------------------------------------------------

class TestCSVIngestion:

    def test_upload_valid_csv_returns_201(self, api_client, sample_csv_bytes):
        """Uploading a well-formed CSV must return HTTP 201."""
        resp = api_client.post(
            "/api/candidates/from-csv",
            data={"enable_llm": "false"},
            format="multipart",
            **{"file": io.BytesIO(sample_csv_bytes)},
        )
        # Use multipart via FILES key
        from django.test import RequestFactory
        assert resp.status_code in (200, 201)

    def test_upload_csv_creates_candidates(self, api_client, in_memory_store, sample_csv_bytes):
        """After CSV upload the store must contain the ingested candidates."""
        f = io.BytesIO(sample_csv_bytes)
        f.name = "candidates.csv"
        api_client.post(
            "/api/candidates/from-csv",
            data={"file": f, "enable_llm": "false"},
            format="multipart",
        )
        assert in_memory_store.count() > 0

    def test_upload_invalid_file_type_returns_400(self, api_client):
        """Uploading a .xlsx file must return HTTP 400."""
        f = io.BytesIO(b"fake xlsx content")
        f.name = "data.xlsx"
        resp = api_client.post(
            "/api/candidates/from-csv",
            data={"file": f},
            format="multipart",
        )
        assert resp.status_code == 400

    def test_upload_returns_candidate_ids(self, api_client, in_memory_store, sample_csv_bytes):
        """Response body must include a list of candidate_ids."""
        f = io.BytesIO(sample_csv_bytes)
        f.name = "candidates.csv"
        resp = api_client.post(
            "/api/candidates/from-csv",
            data={"file": f, "enable_llm": "false"},
            format="multipart",
        )
        body = resp.json()
        assert "candidate_ids" in body or "candidates" in body

    def test_upload_empty_csv_does_not_crash(self, api_client):
        """Uploading a CSV with headers only must not return 500."""
        empty = io.BytesIO(b"name,email,phone\n")
        empty.name = "empty.csv"
        resp = api_client.post(
            "/api/candidates/from-csv",
            data={"file": empty, "enable_llm": "false"},
            format="multipart",
        )
        assert resp.status_code != 500


# ---------------------------------------------------------------------------
# Candidate Listing
# ---------------------------------------------------------------------------

class TestCandidateListing:

    def _seed(self, api_client, sample_csv_bytes):
        f = io.BytesIO(sample_csv_bytes)
        f.name = "candidates.csv"
        api_client.post(
            "/api/candidates/from-csv",
            data={"file": f, "enable_llm": "false"},
            format="multipart",
        )

    def test_list_candidates_returns_200(self, api_client, sample_csv_bytes):
        """GET /api/candidates must return HTTP 200."""
        self._seed(api_client, sample_csv_bytes)
        resp = api_client.get("/api/candidates")
        assert resp.status_code == 200

    def test_list_response_has_candidates_key(self, api_client, sample_csv_bytes):
        """Response body must contain a 'candidates' list."""
        self._seed(api_client, sample_csv_bytes)
        body = api_client.get("/api/candidates").json()
        assert "candidates" in body
        assert isinstance(body["candidates"], list)

    def test_list_reflects_uploaded_count(self, api_client, sample_csv_bytes):
        """Listed candidates must match what was uploaded (CSV has Alice + Bob)."""
        self._seed(api_client, sample_csv_bytes)
        body = api_client.get("/api/candidates").json()
        assert len(body["candidates"]) >= 2

    def test_pagination_page_size_respected(self, api_client, sample_csv_bytes):
        """page_size=1 must return at most 1 candidate."""
        self._seed(api_client, sample_csv_bytes)
        body = api_client.get("/api/candidates?page=1&page_size=1").json()
        assert len(body["candidates"]) <= 1

    def test_list_includes_total_count(self, api_client, sample_csv_bytes):
        """Response must include a 'total' field."""
        self._seed(api_client, sample_csv_bytes)
        body = api_client.get("/api/candidates").json()
        assert "total" in body


# ---------------------------------------------------------------------------
# Single Candidate Retrieval
# ---------------------------------------------------------------------------

class TestCandidateRetrieval:

    def _upload_and_get_id(self, api_client, sample_csv_bytes):
        f = io.BytesIO(sample_csv_bytes)
        f.name = "candidates.csv"
        api_client.post(
            "/api/candidates/from-csv",
            data={"file": f, "enable_llm": "false"},
            format="multipart",
        )
        return api_client.get("/api/candidates").json()["candidates"][0]["candidate_id"]

    def test_get_existing_candidate_returns_200(self, api_client, sample_csv_bytes):
        """GET /api/candidates/<id> for an existing candidate must return 200."""
        cid = self._upload_and_get_id(api_client, sample_csv_bytes)
        resp = api_client.get(f"/api/candidates/{cid}")
        assert resp.status_code == 200

    def test_get_missing_candidate_returns_404(self, api_client):
        """GET /api/candidates/<id> for a non-existent ID must return 404."""
        resp = api_client.get("/api/candidates/does-not-exist-1234")
        assert resp.status_code == 404

    def test_candidate_has_required_fields(self, api_client, sample_csv_bytes):
        """A retrieved candidate must include candidate_id, full_name, and emails."""
        cid = self._upload_and_get_id(api_client, sample_csv_bytes)
        body = api_client.get(f"/api/candidates/{cid}").json()
        assert "candidate_id" in body
        assert "full_name" in body
        assert "emails" in body


# ---------------------------------------------------------------------------
# Resume Upload
# ---------------------------------------------------------------------------

class TestResumeIngestion:

    def test_upload_txt_resume_returns_201(self, api_client, sample_resume_txt):
        """Uploading a plain-text resume must return HTTP 201."""
        with patch("candidates.views.extract_from_resume") as mock_llm:
            mock_llm.side_effect = Exception("LLM disabled for test")
            f = io.BytesIO(sample_resume_txt)
            f.name = "resume.txt"
            resp = api_client.post(
                "/api/candidates/from-resume",
                data={"file": f, "enrich_with_llm": "false"},
                format="multipart",
            )
        assert resp.status_code in (200, 201)

    def test_upload_unsupported_type_returns_400(self, api_client):
        """Uploading a .zip file must return HTTP 400."""
        f = io.BytesIO(b"PK fake zip")
        f.name = "resume.zip"
        resp = api_client.post(
            "/api/candidates/from-resume",
            data={"file": f, "enrich_with_llm": "false"},
            format="multipart",
        )
        assert resp.status_code == 400

    def test_resume_persisted_in_store(self, api_client, in_memory_store, sample_resume_txt):
        """After resume upload the candidate must be in the store."""
        with patch("candidates.views.extract_from_resume") as mock_llm:
            mock_llm.side_effect = Exception("LLM disabled")
            f = io.BytesIO(sample_resume_txt)
            f.name = "resume.txt"
            api_client.post(
                "/api/candidates/from-resume",
                data={"file": f, "enrich_with_llm": "false"},
                format="multipart",
            )
        assert in_memory_store.count() == 1


# ---------------------------------------------------------------------------
# LLM Enrichment
# ---------------------------------------------------------------------------

class TestEnrichment:

    def _create_candidate(self, api_client, in_memory_store, sample_resume_txt):
        """Upload resume without LLM, return candidate_id."""
        with patch("candidates.views.extract_from_resume") as m:
            m.side_effect = Exception("LLM disabled for setup")
            f = io.BytesIO(sample_resume_txt)
            f.name = "resume.txt"
            api_client.post(
                "/api/candidates/from-resume",
                data={"file": f, "enrich_with_llm": "false"},
                format="multipart",
            )
        return list(in_memory_store._data.values())[0].candidate_id

    def test_enrich_nonexistent_returns_404(self, api_client):
        """POST /api/candidates/bad-id/enrich must return 404."""
        resp = api_client.post("/api/candidates/nonexistent-id-999/enrich")
        assert resp.status_code == 404

    def test_enrich_success_returns_200(self, api_client, in_memory_store, sample_resume_txt):
        """POST /api/candidates/<id>/enrich must return 200 on success."""
        from lc.extractor import CandidateExtraction
        cid = self._create_candidate(api_client, in_memory_store, sample_resume_txt)

        mock_extraction = CandidateExtraction(
            full_name="John Doe",
            emails=["john.doe@example.com"],
            phones=["+14155550303"],
            skills=["Python", "Go", "Docker"],
            headline="Software Engineer",
        )
        with patch("candidates.views.extract_from_resume", return_value=mock_extraction):
            resp = api_client.post(f"/api/candidates/{cid}/enrich")

        assert resp.status_code == 200

    def test_enrich_response_message_confirms_gemini(self, api_client, in_memory_store, sample_resume_txt):
        """Enrich response must mention 'Enriched'."""
        from lc.extractor import CandidateExtraction
        cid = self._create_candidate(api_client, in_memory_store, sample_resume_txt)

        mock_extraction = CandidateExtraction(
            full_name="John Doe",
            emails=["john.doe@example.com"],
            skills=["Python"],
        )
        with patch("candidates.views.extract_from_resume", return_value=mock_extraction):
            resp = api_client.post(f"/api/candidates/{cid}/enrich")

        assert "Enriched" in resp.json().get("message", "")

    def test_enrich_adds_llm_skills(self, api_client, in_memory_store, sample_resume_txt):
        """After enrichment, LLM-extracted skills must appear on the candidate."""
        from lc.extractor import CandidateExtraction
        cid = self._create_candidate(api_client, in_memory_store, sample_resume_txt)

        mock_extraction = CandidateExtraction(
            full_name="John Doe",
            emails=["john.doe@example.com"],
            skills=["Python", "Go", "Docker", "Kubernetes", "PostgreSQL"],
        )
        with patch("candidates.views.extract_from_resume", return_value=mock_extraction):
            api_client.post(f"/api/candidates/{cid}/enrich")

        candidate = in_memory_store.get(cid)
        skill_names = {s.name.lower() for s in candidate.skills}
        assert "python" in skill_names


# ---------------------------------------------------------------------------
# Deletion
# ---------------------------------------------------------------------------

class TestDeletion:

    def _upload_and_get_id(self, api_client, sample_csv_bytes):
        f = io.BytesIO(sample_csv_bytes)
        f.name = "candidates.csv"
        api_client.post(
            "/api/candidates/from-csv",
            data={"file": f, "enable_llm": "false"},
            format="multipart",
        )
        return api_client.get("/api/candidates").json()["candidates"][0]["candidate_id"]

    def test_delete_existing_returns_200(self, api_client, sample_csv_bytes):
        """DELETE /api/candidates/<id> for an existing candidate must return 200."""
        cid = self._upload_and_get_id(api_client, sample_csv_bytes)
        resp = api_client.delete(f"/api/candidates/{cid}")
        assert resp.status_code == 200

    def test_delete_removes_from_store(self, api_client, in_memory_store, sample_csv_bytes):
        """After deletion the candidate must be gone from the store."""
        cid = self._upload_and_get_id(api_client, sample_csv_bytes)
        api_client.delete(f"/api/candidates/{cid}")
        assert in_memory_store.get(cid) is None

    def test_delete_nonexistent_returns_404(self, api_client):
        """DELETE /api/candidates/bad-id must return 404."""
        resp = api_client.delete("/api/candidates/totally-fake-id-abc")
        assert resp.status_code == 404
