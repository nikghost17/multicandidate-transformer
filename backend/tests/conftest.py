"""
tests/conftest.py
------------------
Shared pytest fixtures for the Candidate Intelligence Platform (Django).

All MongoDB and LLM calls are fully mocked so tests run instantly,
offline, and deterministically — no real API keys or DB needed.
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path
from typing import List, Optional
from unittest.mock import patch

import django
import pytest

# ── Point to backend/ so all imports resolve ────────────────────────────────
_backend = str(Path(__file__).resolve().parent.parent)
if _backend not in sys.path:
    sys.path.insert(0, _backend)

# ── Dummy env vars BEFORE Django boots ───────────────────────────────────────
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("GEMINI_API_KEY",         "test-api-key-dummy")
os.environ.setdefault("GEMINI_MODEL",           "gemini-1.5-flash")
os.environ.setdefault("MONGODB_URI",            "mongodb://localhost:27017")
os.environ.setdefault("MONGODB_DB",             "test_candidate_platform")
os.environ.setdefault("EMBEDDING_PROVIDER",     "sentence_transformers")
os.environ.setdefault("DJANGO_SECRET_KEY",      "test-secret-key")

django.setup()

# ── In-memory store (replaces MongoStorage for tests) ───────────────────────
from models.candidate import Candidate


class InMemoryStore:
    """Lightweight in-memory store that mirrors MongoStorage's full interface."""

    def __init__(self):
        self._data: dict[str, Candidate] = {}

    def upsert(self, candidate: Candidate) -> None:
        self._data[candidate.candidate_id] = candidate

    def upsert_many(self, candidates: List[Candidate]) -> None:
        for c in candidates:
            self.upsert(c)

    def get(self, candidate_id: str) -> Optional[Candidate]:
        return self._data.get(candidate_id)

    def list_all(self, page: int = 1, page_size: int = 20) -> List[Candidate]:
        items = sorted(
            self._data.values(),
            key=lambda c: c.overall_confidence,
            reverse=True,
        )
        start = (page - 1) * page_size
        return items[start : start + page_size]

    def count(self) -> int:
        return len(self._data)

    def delete(self, candidate_id: str) -> bool:
        if candidate_id in self._data:
            del self._data[candidate_id]
            return True
        return False

    def clear(self) -> int:
        count = len(self._data)
        self._data.clear()
        return count

    def find_by_identity(
        self,
        emails: List[str] = None,
        phones: List[str] = None,
    ) -> Optional[Candidate]:
        emails = [e.lower() for e in (emails or [])]
        for c in self._data.values():
            for e in c.emails:
                if e.lower() in emails:
                    return c
            for p in c.phones:
                if p in (phones or []):
                    return c
        return None


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def in_memory_store():
    """Fresh in-memory store per test."""
    return InMemoryStore()


@pytest.fixture
def api_client(in_memory_store):
    """
    Django REST Framework APIClient with:
      - MongoStorage swapped for InMemoryStore
      - Vector-store calls no-op'd
      - Gemini LLM calls no-op'd
    """
    from rest_framework.test import APIClient

    client = APIClient()

    with (
        patch("candidates.views.get_store", return_value=in_memory_store),
        patch("candidates.views.lc_vs.index_resume",      return_value=3),
        patch("candidates.views.lc_vs.delete_candidate",  return_value=None),
        patch("candidates.views.search_candidates",        return_value=[]),
        patch("candidates.views.build_candidate_context",  return_value="mock rag context"),
    ):
        yield client


@pytest.fixture
def sample_csv_bytes():
    """A minimal recruiter CSV with two candidates."""
    content = (
        "name,email,phone,skills\n"
        "Alice Johnson,alice@example.com,+14155550101,\"Python,AWS,Docker\"\n"
        "Bob Smith,bob@example.com,+14155550202,\"Java,Kubernetes\"\n"
    )
    return content.encode()


@pytest.fixture
def sample_resume_txt():
    """A plain-text resume for upload tests."""
    return b"""John Doe
john.doe@example.com | +14155550303

EXPERIENCE
Software Engineer at Acme Corp (2020-2023)
  - Built microservices in Python and Go

SKILLS
Python, Go, Docker, Kubernetes, PostgreSQL

EDUCATION
B.S. Computer Science, MIT, 2020
"""
