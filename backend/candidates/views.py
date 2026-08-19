"""
candidates/views.py
--------------------
Django REST Framework views that mirror every FastAPI endpoint in
multisource_candidate_platform/api/main.py  — using the SAME
underlying pipeline, lc, and models packages (imported via sys.path
injection in config/settings.py).

Endpoints implemented:
  GET    /api/health
  POST   /api/candidates/from-csv
  POST   /api/candidates/from-resume
  GET    /api/candidates
  GET    /api/candidates/search
  GET    /api/candidates/<id>
  GET    /api/candidates/<id>/confidence
  POST   /api/candidates/<id>/enrich
  POST   /api/candidates/merge
  DELETE /api/candidates/<id>
  DELETE /api/candidates
"""

from __future__ import annotations

import os
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

# ── Domain layer — imported from multisource project via sys.path ────────────
from models.candidate import Candidate
from pipeline.merger.merge import CandidateMerger
from pipeline.confidence.explainer import explain_candidate
from api.mongo_storage import MongoStorage

# ── LangChain layer ───────────────────────────────────────────────────────────
from lc.loaders import load_resume, get_full_text, extract_quick_fields
from lc.section_splitter import split_into_sections
from lc import mongo_vectorstore as lc_vs
from lc.extractor import extract_from_resume, extraction_to_raw_record
from lc.retriever import search_candidates, build_candidate_context

# ── Singletons ────────────────────────────────────────────────────────────────
_store: Optional[MongoStorage] = None


def get_store() -> MongoStorage:
    global _store
    if _store is None:
        _store = MongoStorage()
    return _store


# ── Helpers ────────────────────────────────────────────────────────────────────

def _c(candidate: Candidate, strip_raw: bool = True) -> Dict[str, Any]:
    """Serialise Candidate → dict, optionally stripping large raw fields."""
    data = candidate.model_dump()
    if strip_raw:
        data.pop("resume_raw_text", None)
        data.pop("rag_context", None)
    return data


def _candidate_to_docs(candidate: Candidate) -> List:
    """Build searchable Document chunks from CSV-imported candidate fields."""
    from langchain_core.documents import Document
    from datetime import datetime, timezone

    docs = []
    now_iso = datetime.now(timezone.utc).isoformat()
    base = {
        "original_filename": "csv_import",
        "extraction_method": "structured_fields",
        "source_type": "csv",
        "indexed_at": now_iso,
    }

    # Header / contact chunk
    header_parts = []
    if candidate.full_name:
        header_parts.append(candidate.full_name)
    if candidate.headline:
        header_parts.append(candidate.headline)
    if candidate.emails:
        header_parts.append("Email: " + ", ".join(candidate.emails))
    loc = candidate.location
    if loc:
        loc_str = ", ".join(filter(None, [loc.city, loc.region, loc.country]))
        if loc_str:
            header_parts.append("Location: " + loc_str)
    if header_parts:
        docs.append(Document(
            page_content="\n".join(header_parts),
            metadata={**base, "section_type": "header", "section_title": "Contact / Header"},
        ))

    if candidate.skills:
        docs.append(Document(
            page_content="Skills: " + ", ".join(s.name for s in candidate.skills),
            metadata={**base, "section_type": "skills", "section_title": "Skills"},
        ))

    if candidate.experience:
        exp_lines = []
        for exp in candidate.experience:
            line = f"{exp.title} at {exp.company}"
            if exp.start:
                line += f" ({exp.start} – {exp.end or 'Present'})"
            if exp.summary:
                line += f"\n  {exp.summary}"
            exp_lines.append(line)
        docs.append(Document(
            page_content="Experience:\n" + "\n".join(exp_lines),
            metadata={**base, "section_type": "experience", "section_title": "Experience"},
        ))

    if candidate.education:
        edu_lines = []
        for edu in candidate.education:
            line = edu.institution
            if edu.degree:
                line += f" — {edu.degree}"
            if edu.field_of_study:
                line += f" ({edu.field_of_study})"
            edu_lines.append(line)
        docs.append(Document(
            page_content="Education:\n" + "\n".join(edu_lines),
            metadata={**base, "section_type": "education", "section_title": "Education"},
        ))

    for i, doc in enumerate(docs):
        doc.metadata["chunk_index"] = i

    return docs


def _dedup_against_store(candidates: List[Candidate], store: MongoStorage) -> List[Candidate]:
    """
    Cross-upload deduplication: if an existing candidate shares any
    email or phone with a new one, merge the new data INTO the existing
    record (preserving its ID) instead of creating a duplicate.
    """
    result = []
    for new_c in candidates:
        existing = store.find_by_identity(emails=new_c.emails, phones=new_c.phones)
        if existing:
            for email in new_c.emails:
                if email not in existing.emails:
                    existing.emails.append(email)
            for phone in new_c.phones:
                if phone not in existing.phones:
                    existing.phones.append(phone)
            for skill in new_c.skills:
                if not any(s.name == skill.name for s in existing.skills):
                    existing.skills.append(skill)
            for exp in new_c.experience:
                if not any(e.company == exp.company and e.title == exp.title
                           for e in existing.experience):
                    existing.experience.append(exp)
            for edu in new_c.education:
                if not any(e.institution == edu.institution for e in existing.education):
                    existing.education.append(edu)
            if new_c.overall_confidence > existing.overall_confidence:
                if new_c.full_name:   existing.full_name   = new_c.full_name
                if new_c.headline:    existing.headline    = new_c.headline
                if new_c.location:    existing.location    = new_c.location
                if new_c.llm_summary: existing.llm_summary = new_c.llm_summary
            if new_c.headline and not existing.headline:
                existing.headline = new_c.headline
            if new_c.location and not existing.location:
                existing.location = new_c.location
            if new_c.llm_summary and not existing.llm_summary:
                existing.llm_summary = new_c.llm_summary
            if new_c.llm_enriched:
                existing.llm_enriched = True
            for prov in new_c.provenance:
                if not any(p.field_name == prov.field_name and p.source == prov.source
                           for p in existing.provenance):
                    existing.provenance.append(prov)
            if new_c.overall_confidence > existing.overall_confidence:
                existing.overall_confidence = new_c.overall_confidence
            if new_c.resume_raw_text and not existing.resume_raw_text:
                existing.resume_raw_text = new_c.resume_raw_text
            if new_c.embedding_id and not existing.embedding_id:
                existing.embedding_id = new_c.embedding_id
            if new_c.years_experience and not existing.years_experience:
                existing.years_experience = new_c.years_experience
            result.append(existing)
            print(f"[Dedup] Merged into existing {existing.candidate_id[:8]}… ({existing.full_name})")
        else:
            result.append(new_c)
    return result


# ════════════════════════════════════════════════════════════════════════════════
# Views
# ════════════════════════════════════════════════════════════════════════════════

class HealthView(APIView):
    """GET /api/health"""

    def get(self, request: Request) -> Response:
        return Response({"status": "ok", "version": "1.0.0", "backend": "Django"})


class IngestCSVView(APIView):
    """POST /api/candidates/from-csv — Upload recruiter CSV."""

    def post(self, request: Request) -> Response:
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "No file uploaded."}, status=400)
        if not file.name.endswith(".csv"):
            return Response({"error": "Only .csv files accepted."}, status=400)

        enable_llm = request.data.get("enable_llm", "false").lower() == "true"

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            for chunk in file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            from pipeline.parsers.recruiter_csv import RecruiterCSVParser

            records = RecruiterCSVParser(tmp_path).parse()
            merger = CandidateMerger(enable_llm_conflict_resolution=enable_llm)
            candidates = merger.process_records(records)

            store = get_store()
            candidates = _dedup_against_store(candidates, store)
            store.upsert_many(candidates)

            # Index in vector store
            total_chunks = 0
            for cand in candidates:
                docs = _candidate_to_docs(cand)
                if docs:
                    n = lc_vs.index_resume(cand.candidate_id, docs)
                    cand.embedding_id = cand.candidate_id
                    total_chunks += n
            if total_chunks:
                store.upsert_many(candidates)
                print(f"[API] Indexed {total_chunks} chunks for {len(candidates)} CSV candidates")

            return Response({
                "message": f"Ingested {len(candidates)} candidates.",
                "candidate_ids": [c.candidate_id for c in candidates],
                "candidates": [_c(c) for c in candidates],
            }, status=201)
        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)
        finally:
            os.unlink(tmp_path)


class IngestResumeView(APIView):
    """POST /api/candidates/from-resume — Upload PDF / DOCX / TXT resume."""

    def post(self, request: Request) -> Response:
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "No file uploaded."}, status=400)

        suffix = Path(file.name).suffix.lower()
        if suffix not in (".pdf", ".docx", ".txt", ".text"):
            return Response(
                {"error": f"Unsupported type '{suffix}'. Use PDF, DOCX, or TXT."},
                status=400,
            )

        enrich_with_llm = request.data.get("enrich_with_llm", "true").lower() != "false"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            for chunk in file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            docs = load_resume(tmp_path, original_filename=file.name)
            raw_text = get_full_text(docs)
            if not raw_text.strip():
                return Response({"error": "No text could be extracted."}, status=422)

            quick = extract_quick_fields(raw_text)
            quick["raw_text"] = raw_text
            raw_records = [{"source_name": "resume_parsed", "source_type": "unstructured", "raw_data": quick}]
            llm_status = "skipped"

            if enrich_with_llm:
                try:
                    extraction = extract_from_resume(raw_text)
                    rec = extraction_to_raw_record(extraction)
                    rec["raw_data"]["raw_text"] = raw_text
                    raw_records.append(rec)
                    llm_status = "success"
                    print(f"[API] LLM enrichment: skills={len(extraction.skills)}, "
                          f"exp={len(extraction.experience)}, edu={len(extraction.education)}")
                except Exception as e:
                    llm_status = f"failed: {e}"
                    print(f"[API] ⚠ LLM enrichment FAILED: {e}")
                    traceback.print_exc()

            candidates = CandidateMerger().process_records(raw_records)
            if not candidates:
                return Response({"error": "Could not create candidate profile."}, status=422)

            candidate = candidates[0]
            store = get_store()
            [candidate] = _dedup_against_store([candidate], store)

            chunks = split_into_sections(docs, original_filename=file.name)
            n_chunks = lc_vs.index_resume(candidate.candidate_id, chunks)
            candidate.embedding_id = candidate.candidate_id
            print(f"[API] Indexed {n_chunks} chunks for {candidate.candidate_id[:8]}")

            store.upsert(candidate)

            return Response({
                "message": "Resume ingested successfully.",
                "candidate_id": candidate.candidate_id,
                "candidate": _c(candidate),
                "llm_enrichment": llm_status,
            }, status=201)
        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)
        finally:
            os.unlink(tmp_path)


class CandidateListView(APIView):
    """GET /api/candidates — Paginated list sorted by confidence desc."""

    def get(self, request: Request) -> Response:
        try:
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 20))
            page = max(1, page)
            page_size = min(max(1, page_size), 100)
        except ValueError:
            return Response({"error": "Invalid pagination params."}, status=400)

        store = get_store()
        return Response({
            "total": store.count(),
            "page": page,
            "page_size": page_size,
            "candidates": [_c(c) for c in store.list_all(page, page_size)],
        })

    def delete(self, request: Request) -> Response:
        """DELETE /api/candidates — Clear all candidates."""
        count = get_store().clear()
        try:
            vs = lc_vs.get_vectorstore()
            vs._collection.delete(where={"chunk_index": {"$gte": 0}})
        except Exception:
            pass
        return Response({"message": f"Cleared {count} candidates.", "deleted": count})


class SemanticSearchView(APIView):
    """GET /api/candidates/search?q=<query>"""

    def get(self, request: Request) -> Response:
        q = request.query_params.get("q", "").strip()
        if len(q) < 2:
            return Response({"error": "Query must be at least 2 characters."}, status=400)

        try:
            top_k = int(request.query_params.get("top_k", 10))
            top_k = min(max(1, top_k), 50)
        except ValueError:
            top_k = 10

        section = request.query_params.get("section") or None

        hits = search_candidates(q, top_k=top_k, section_type=section)
        store = get_store()
        results = []
        for hit in hits:
            cid = hit.get("candidate_id")
            if cid:
                c = store.get(cid)
                if c:
                    results.append({
                        "candidate": _c(c),
                        "relevance_score": hit.get("similarity", 0.0),
                        "matched_chunk": hit.get("text", "")[:300],
                        "section_type": hit.get("section_type"),
                        "section_title": hit.get("section_title"),
                    })

        return Response({"query": q, "section_filter": section, "results": results})


class CandidateDetailView(APIView):
    """GET /api/candidates/<candidate_id>  |  DELETE /api/candidates/<candidate_id>"""

    def get(self, request: Request, candidate_id: str) -> Response:
        c = get_store().get(candidate_id)
        if not c:
            return Response({"error": f"Candidate {candidate_id!r} not found."}, status=404)
        return Response(_c(c))

    def delete(self, request: Request, candidate_id: str) -> Response:
        if not get_store().delete(candidate_id):
            return Response({"error": f"Candidate {candidate_id!r} not found."}, status=404)
        lc_vs.delete_candidate(candidate_id)
        return Response({"message": f"Candidate {candidate_id} deleted."})


class CandidateConfidenceView(APIView):
    """GET /api/candidates/<candidate_id>/confidence"""

    def get(self, request: Request, candidate_id: str) -> Response:
        c = get_store().get(candidate_id)
        if not c:
            return Response({"error": f"Candidate {candidate_id!r} not found."}, status=404)
        return Response(explain_candidate(c))


class EnrichCandidateView(APIView):
    """POST /api/candidates/<candidate_id>/enrich — Re-run Gemini RAG."""

    def post(self, request: Request, candidate_id: str) -> Response:
        store = get_store()
        c = store.get(candidate_id)
        if not c:
            return Response({"error": f"Candidate {candidate_id!r} not found."}, status=404)
        if not c.resume_raw_text:
            return Response(
                {"error": "No resume text stored. Upload the resume first."}, status=422
            )
        if c.llm_enriched:
            return Response({"message": "Already enriched.", "candidate": _c(c)})

        try:
            rag_ctx = build_candidate_context(candidate_id)
            extraction = extract_from_resume(c.resume_raw_text, rag_context=rag_ctx or None)
            rec = extraction_to_raw_record(extraction)
            rec["raw_data"]["raw_text"] = c.resume_raw_text

            if c.emails: rec["raw_data"]["email"] = c.emails[0]
            if c.phones: rec["raw_data"]["phone"] = c.phones[0]

            temp_cands = CandidateMerger().process_records([rec])
            if not temp_cands:
                return Response({"error": "Enrichment produced no candidate."}, status=500)

            extracted_cand = temp_cands[0]
            extracted_cand.llm_enriched = True

            [enriched] = _dedup_against_store([extracted_cand], store)
            store.upsert(enriched)

            return Response({"message": "Enriched with Gemini.", "candidate": _c(enriched)})
        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)


class MergeCandidatesView(APIView):
    """POST /api/candidates/merge — Merge secondary into primary."""

    def post(self, request: Request) -> Response:
        pid = request.data.get("primary_id")
        sid = request.data.get("secondary_id")
        if not pid or not sid:
            return Response(
                {"error": "Both 'primary_id' and 'secondary_id' required."}, status=400
            )
        if pid == sid:
            return Response({"error": "Cannot merge a candidate with itself."}, status=400)

        store = get_store()
        p = store.get(pid)
        s = store.get(sid)
        if not p:
            return Response({"error": f"Primary {pid!r} not found."}, status=404)
        if not s:
            return Response({"error": f"Secondary {sid!r} not found."}, status=404)

        for email in s.emails:
            if email not in p.emails: p.emails.append(email)
        for phone in s.phones:
            if phone not in p.phones: p.phones.append(phone)
        for skill in s.skills:
            if not any(sk.name == skill.name for sk in p.skills): p.skills.append(skill)
        for exp in s.experience:
            if not any(e.company == exp.company and e.title == exp.title for e in p.experience):
                p.experience.append(exp)
        for edu in s.education:
            if not any(e.institution == edu.institution for e in p.education):
                p.education.append(edu)

        store.upsert(p)
        store.delete(sid)
        lc_vs.delete_candidate(sid)

        return Response({"message": f"Merged into {pid[:8]}…", "merged_candidate": _c(p)})
