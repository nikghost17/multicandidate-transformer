"""
lc/section_splitter.py
-----------------------
Section-aware resume chunking with rich metadata.

Instead of blindly splitting at every 1000 characters, this module:
  1. Detects resume section headers (EXPERIENCE, SKILLS, EDUCATION, etc.)
  2. Splits text at section boundaries
  3. Sub-chunks large sections using RecursiveCharacterTextSplitter
  4. Attaches rich metadata to every chunk (section_type, section_title, etc.)
  5. Falls back to character-based chunking if no sections detected

Usage:
    from lc.section_splitter import split_into_sections
    chunks = split_into_sections(docs)
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from langchain_core.documents import Document


# ---------------------------------------------------------------------------
# Section header detection
# ---------------------------------------------------------------------------

# Canonical section types mapped from common header variants.
# Each key is the canonical type; the value is a list of regex patterns
# that match common resume headers for that section.

_SECTION_PATTERNS: Dict[str, List[str]] = {
    "summary": [
        r"summary",
        r"profile",
        r"objective",
        r"about\s*me",
        r"professional\s+summary",
        r"career\s+summary",
        r"executive\s+summary",
        r"personal\s+statement",
        r"career\s+objective",
        r"professional\s+profile",
        r"overview",
    ],
    "experience": [
        r"experience",
        r"work\s+experience",
        r"professional\s+experience",
        r"employment\s+history",
        r"employment",
        r"professional\s+background",
        r"career\s+history",
        r"work\s+history",
        r"relevant\s+experience",
        r"internship(?:s)?",
    ],
    "education": [
        r"education",
        r"academic\s+background",
        r"academic\s+qualifications",
        r"qualifications",
        r"academic\s+credentials",
        r"educational\s+background",
    ],
    "skills": [
        r"skills",
        r"technical\s+skills",
        r"core\s+competencies",
        r"competencies",
        r"technologies",
        r"tools?\s+(?:and|&)\s+technologies",
        r"technical\s+proficiency",
        r"areas?\s+of\s+expertise",
        r"key\s+skills",
        r"programming\s+languages",
        r"tech\s+stack",
    ],
    "projects": [
        r"projects",
        r"personal\s+projects",
        r"key\s+projects",
        r"academic\s+projects",
        r"notable\s+projects",
        r"selected\s+projects",
        r"side\s+projects",
    ],
    "certifications": [
        r"certifications?",
        r"licenses?\s+(?:and|&)\s+certifications?",
        r"awards?\s+(?:and|&)\s+(?:honors?|achievements?)",
        r"awards?",
        r"honors?",
        r"achievements?",
        r"accomplishments?",
        r"publications?",
    ],
    "other": [
        r"interests?",
        r"hobbies?",
        r"volunteer(?:ing)?(?:\s+experience)?",
        r"community\s+(?:service|involvement)",
        r"references?",
        r"languages?",
        r"extracurricular(?:\s+activities)?",
        r"activities",
        r"leadership",
        r"memberships?",
        r"affiliations?",
        r"additional\s+information",
    ],
}

# Compile all patterns into a single lookup.
# Pattern matches lines that look like section headers:
#   - Line starts with optional bullets/numbers
#   - Header text (one of our patterns)
#   - Optional colon or dash after
#   - Line is mostly just the header (not a long paragraph)

_COMPILED_PATTERNS: List[Tuple[str, re.Pattern]] = []
for section_type, patterns in _SECTION_PATTERNS.items():
    for pat in patterns:
        # Match: start-of-line, optional whitespace/bullet, the header, optional colon/dash, end
        regex = re.compile(
            rf"^\s*(?:[\u2022\u25cf\u25cb\u2023\-\*●]?\s*)"  # optional bullet
            rf"(?:\d+[\.\)]\s*)?"                              # optional numbering
            rf"({pat})"                                        # the header text
            rf"\s*[:\-—]?\s*$",                                # optional colon/dash
            re.IGNORECASE,
        )
        _COMPILED_PATTERNS.append((section_type, regex))


# Maximum chunk size before sub-chunking a section
_MAX_SECTION_CHARS = 1500


# ---------------------------------------------------------------------------
# Section detection
# ---------------------------------------------------------------------------

def detect_sections(text: str) -> List[Tuple[str, str, int]]:
    """
    Detect section boundaries in resume text.

    Returns a list of (section_type, section_title, line_index) tuples,
    sorted by line_index.

    Parameters
    ----------
    text : str — full resume text

    Returns
    -------
    list[(section_type, original_header_text, line_index)]
    """
    lines = text.split("\n")
    sections: List[Tuple[str, str, int]] = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) > 80:
            # Skip empty lines and lines too long to be headers
            continue

        for section_type, pattern in _COMPILED_PATTERNS:
            if pattern.match(stripped):
                sections.append((section_type, stripped, i))
                break  # first match wins for this line

    return sections


def _split_text_by_sections(
    text: str,
    sections: List[Tuple[str, str, int]],
) -> List[Tuple[str, str, str]]:
    """
    Split text into (section_type, section_title, section_content) tuples
    based on detected section boundaries.

    If there's text before the first section header, it's assigned type "header"
    (usually contains the candidate's name, contact info, headline).
    """
    lines = text.split("\n")
    result: List[Tuple[str, str, str]] = []

    # Text before first section → "header" section
    if sections and sections[0][2] > 0:
        pre_header_lines = lines[:sections[0][2]]
        pre_text = "\n".join(pre_header_lines).strip()
        if pre_text:
            result.append(("header", "Contact / Header", pre_text))

    # Each section runs from its header to the next section's header
    for idx, (sec_type, sec_title, line_idx) in enumerate(sections):
        if idx + 1 < len(sections):
            next_line_idx = sections[idx + 1][2]
        else:
            next_line_idx = len(lines)

        section_lines = lines[line_idx + 1 : next_line_idx]  # exclude the header line itself
        section_text = "\n".join(section_lines).strip()

        if section_text:
            result.append((sec_type, sec_title, section_text))

    return result


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def split_into_sections(
    docs: List[Document],
    original_filename: str = None,
) -> List[Document]:
    """
    Section-aware chunking with rich metadata.

    Strategy:
      1. Merge all page text into one string
      2. Detect section headers
      3. Split at section boundaries
      4. Sub-chunk large sections (>1500 chars) preserving section metadata
      5. If no sections detected → fallback to character-based chunking

    Parameters
    ----------
    docs : list[Document]
        Output from load_resume() — one Document per page/file.
    original_filename : str, optional
        Override the filename in metadata.

    Returns
    -------
    list[Document] — chunked Documents with rich metadata, ready for embedding.
    """
    if not docs:
        return []

    # Inherit metadata from parent docs
    base_metadata = dict(docs[0].metadata) if docs[0].metadata else {}
    fname = original_filename or base_metadata.get("source", "unknown")
    extraction_method = base_metadata.get("extraction_method", "unknown")
    source_type = base_metadata.get("source_type", "resume")
    now_iso = datetime.now(timezone.utc).isoformat()

    # Merge all pages into one text for section detection
    full_text = "\n\n".join(d.page_content for d in docs if d.page_content.strip())

    if not full_text.strip():
        return []

    # Detect sections
    sections = detect_sections(full_text)

    if not sections:
        # No sections detected → fallback to character-based chunking
        print(f"[Section Splitter] No section headers detected — using character-based fallback")
        return _fallback_split(docs, fname, extraction_method, source_type, now_iso)

    # Split text at section boundaries
    section_chunks = _split_text_by_sections(full_text, sections)
    print(f"[Section Splitter] Detected {len(sections)} sections: "
          f"{[s[0] for s in section_chunks]}")

    # Build final Document list with rich metadata
    result: List[Document] = []
    global_idx = 0

    for sec_type, sec_title, sec_text in section_chunks:
        if len(sec_text) > _MAX_SECTION_CHARS:
            # Sub-chunk large sections
            sub_chunks = _sub_chunk(sec_text)
            for sub_idx, sub_text in enumerate(sub_chunks):
                result.append(Document(
                    page_content=sub_text,
                    metadata={
                        "section_type":      sec_type,
                        "section_title":     sec_title,
                        "chunk_index":       global_idx,
                        "section_chunk":     sub_idx,
                        "section_chunk_total": len(sub_chunks),
                        "original_filename": fname,
                        "extraction_method": extraction_method,
                        "source_type":       source_type,
                        "indexed_at":        now_iso,
                    },
                ))
                global_idx += 1
        else:
            # Small section → one chunk
            result.append(Document(
                page_content=sec_text,
                metadata={
                    "section_type":      sec_type,
                    "section_title":     sec_title,
                    "chunk_index":       global_idx,
                    "section_chunk":     0,
                    "section_chunk_total": 1,
                    "original_filename": fname,
                    "extraction_method": extraction_method,
                    "source_type":       source_type,
                    "indexed_at":        now_iso,
                },
            ))
            global_idx += 1

    # Also include any table Documents that were passed in
    # (tables from pdfplumber already have section_type="table" in metadata)
    for doc in docs:
        if doc.metadata.get("section_type") == "table":
            doc.metadata["chunk_index"] = global_idx
            doc.metadata["indexed_at"] = now_iso
            result.append(doc)
            global_idx += 1

    total = len(result)
    print(f"[Section Splitter] {len(docs)} doc(s) → {total} section-aware chunks")
    return result


# ---------------------------------------------------------------------------
# Sub-chunking for large sections
# ---------------------------------------------------------------------------

def _sub_chunk(text: str) -> List[str]:
    """
    Sub-chunk a large section using RecursiveCharacterTextSplitter.
    Uses the same settings as splitter.py for consistency.
    """
    from lc.splitter import get_splitter
    splitter = get_splitter()
    return splitter.split_text(text)


# ---------------------------------------------------------------------------
# Fallback: character-based chunking with basic metadata
# ---------------------------------------------------------------------------

def _fallback_split(
    docs: List[Document],
    fname: str,
    extraction_method: str,
    source_type: str,
    indexed_at: str,
) -> List[Document]:
    """
    Fallback to character-based chunking when no section headers are found.
    Still enriches metadata beyond what splitter.py does alone.
    """
    from lc.splitter import split_documents
    chunks = split_documents(docs)

    for i, chunk in enumerate(chunks):
        chunk.metadata.update({
            "section_type":      "unknown",
            "section_title":     "Unknown",
            "chunk_index":       i,
            "original_filename": fname,
            "extraction_method": extraction_method,
            "source_type":       source_type,
            "indexed_at":        indexed_at,
        })

    return chunks
