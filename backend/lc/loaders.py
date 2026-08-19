"""
lc/loaders.py
--------------
Load documents (PDF, DOCX, TXT) with rich extraction.

Extraction strategy:
  1. PyMuPDF (fitz)    — primary text extraction, handles multi-column, text boxes
  2. pdfplumber        — table extraction → each table as a separate Document
  3. Gemini Vision     — fallback for scanned/image PDFs (no OCR dependency)

Every loader returns a list of LangChain `Document` objects:
    Document(
        page_content = "the extracted text",
        metadata     = {"source": "...", "page": 0, "extraction_method": "pymupdf", ...}
    )
"""

from __future__ import annotations

import os
import re
import base64
from pathlib import Path
from typing import List, Optional, Tuple

from langchain_core.documents import Document


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# If a page has fewer than this many chars of extracted text,
# it's likely scanned/image-based.
_SCANNED_THRESHOLD = 50


# ---------------------------------------------------------------------------
# PDF loading — PyMuPDF (primary)
# ---------------------------------------------------------------------------

def load_pdf(file_path: str, original_filename: str = None) -> List[Document]:
    """
    Load a PDF using PyMuPDF (fitz). Returns one Document per page.

    Advantages over PyPDFLoader:
      - Handles multi-column layouts (extracts in reading order)
      - Handles text boxes, sidebars, annotations
      - Built-in page-to-image conversion (no poppler needed)
    """
    import fitz  # PyMuPDF

    fname = original_filename or Path(file_path).name
    docs: List[Document] = []

    pdf = fitz.open(file_path)
    for page_num in range(len(pdf)):
        page = pdf[page_num]
        # "text" sort mode preserves reading order for multi-column
        text = page.get_text("text", sort=True)

        if text and text.strip():
            docs.append(Document(
                page_content=text,
                metadata={
                    "source":            fname,
                    "page":              page_num,
                    "extraction_method": "pymupdf",
                    "source_type":       "resume",
                },
            ))
    pdf.close()

    print(f"[LC Loader] PDF (PyMuPDF): {len(docs)} pages from {fname}")
    return docs


# ---------------------------------------------------------------------------
# PDF tables — pdfplumber
# ---------------------------------------------------------------------------

def extract_tables(file_path: str, original_filename: str = None) -> List[Document]:
    """
    Extract tables from a PDF using pdfplumber.
    Each table becomes its own Document with section_type="table".
    Tables are converted to readable markdown format.
    """
    import pdfplumber

    fname = original_filename or Path(file_path).name
    table_docs: List[Document] = []

    try:
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                for table_idx, table in enumerate(tables):
                    if not table or len(table) < 2:
                        continue  # skip empty or single-row tables

                    # Convert to markdown table
                    md_table = _table_to_markdown(table)
                    if md_table.strip():
                        table_docs.append(Document(
                            page_content=md_table,
                            metadata={
                                "source":            fname,
                                "page":              page_num,
                                "extraction_method": "pdfplumber",
                                "source_type":       "resume",
                                "section_type":      "table",
                                "table_index":       table_idx,
                            },
                        ))
    except Exception as e:
        print(f"[LC Loader] Table extraction warning: {e}")

    if table_docs:
        print(f"[LC Loader] Tables: {len(table_docs)} table(s) from {fname}")
    return table_docs


def _table_to_markdown(table: List[List]) -> str:
    """Convert a pdfplumber table (list of rows) to markdown format."""
    if not table:
        return ""

    # Clean cells: replace None with empty string, strip whitespace
    cleaned = []
    for row in table:
        cleaned.append([str(cell).strip() if cell else "" for cell in row])

    # Skip tables that are mostly empty
    total_cells = sum(len(row) for row in cleaned)
    non_empty   = sum(1 for row in cleaned for cell in row if cell)
    if total_cells > 0 and non_empty / total_cells < 0.3:
        return ""

    # Build markdown
    lines = []
    header = cleaned[0]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join("---" for _ in header) + " |")
    for row in cleaned[1:]:
        # Pad or trim to match header columns
        padded = row + [""] * (len(header) - len(row)) if len(row) < len(header) else row[:len(header)]
        lines.append("| " + " | ".join(padded) + " |")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scanned PDF detection + Gemini Vision fallback
# ---------------------------------------------------------------------------

def _is_scanned_pdf(file_path: str) -> bool:
    """
    Detect if a PDF is scanned (image-based) by checking if
    PyMuPDF extracts very little text from each page.
    """
    import fitz

    try:
        pdf = fitz.open(file_path)
        total_text_len = 0
        num_pages = len(pdf)

        for page_num in range(min(num_pages, 3)):  # check first 3 pages
            text = pdf[page_num].get_text("text")
            total_text_len += len(text.strip())

        pdf.close()
        avg_chars = total_text_len / max(num_pages, 1)
        return avg_chars < _SCANNED_THRESHOLD
    except Exception:
        return False


def _pdf_pages_to_base64(file_path: str) -> List[str]:
    """
    Convert PDF pages to base64-encoded PNG images using PyMuPDF.
    No poppler dependency — PyMuPDF renders pages natively.
    """
    import fitz

    images = []
    pdf = fitz.open(file_path)
    for page_num in range(len(pdf)):
        page = pdf[page_num]
        # Render at 2x DPI for better Gemini Vision accuracy
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        images.append(b64)
    pdf.close()
    return images


def load_pdf_with_vision(
    file_path: str,
    original_filename: str = None,
) -> List[Document]:
    """
    Extract text from a scanned/image PDF using Gemini Vision.

    Sends each page as an image to Gemini and asks it to extract
    all text content. This is the simplest approach — no Tesseract,
    no poppler, just the Gemini API key you already have.
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage

    fname = original_filename or Path(file_path).name
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        print("[LC Loader] GEMINI_API_KEY not set — cannot process scanned PDF")
        return []

    llm = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        google_api_key=api_key,
        temperature=0.0,
    )

    page_images = _pdf_pages_to_base64(file_path)
    docs: List[Document] = []

    for page_num, b64_img in enumerate(page_images):
        try:
            msg = HumanMessage(content=[
                {"type": "text", "text": (
                    "Extract ALL text content from this resume page exactly as written. "
                    "Preserve the structure: section headers, bullet points, dates, "
                    "company names, skills. Do NOT summarise or interpret — "
                    "just extract the raw text faithfully."
                )},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/png;base64,{b64_img}"
                }},
            ])
            response = llm.invoke([msg])
            text = response.content.strip()

            if text:
                docs.append(Document(
                    page_content=text,
                    metadata={
                        "source":            fname,
                        "page":              page_num,
                        "extraction_method": "gemini_vision",
                        "source_type":       "resume",
                    },
                ))
        except Exception as e:
            print(f"[LC Loader] Gemini Vision error on page {page_num}: {e}")

    print(f"[LC Loader] PDF (Gemini Vision): {len(docs)} pages from {fname}")
    return docs


# ---------------------------------------------------------------------------
# DOCX and TXT loaders (minimal changes — add metadata)
# ---------------------------------------------------------------------------

def load_docx(file_path: str, original_filename: str = None) -> List[Document]:
    """Load a DOCX resume. Returns a single Document."""
    from langchain_community.document_loaders import Docx2txtLoader

    fname = original_filename or Path(file_path).name
    loader = Docx2txtLoader(file_path)
    docs = loader.load()

    # Enrich metadata
    for doc in docs:
        doc.metadata["source"] = fname
        doc.metadata["extraction_method"] = "docx2txt"
        doc.metadata["source_type"] = "resume"

    print(f"[LC Loader] DOCX: {len(docs)} doc(s) from {fname}")
    return docs


def load_txt(file_path: str, original_filename: str = None) -> List[Document]:
    """Load a plain text resume."""
    from langchain_community.document_loaders import TextLoader

    fname = original_filename or Path(file_path).name
    loader = TextLoader(file_path, encoding="utf-8")
    docs = loader.load()

    # Enrich metadata
    for doc in docs:
        doc.metadata["source"] = fname
        doc.metadata["extraction_method"] = "textloader"
        doc.metadata["source_type"] = "resume"

    print(f"[LC Loader] TXT: {len(docs)} doc(s) from {fname}")
    return docs


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def load_resume(
    file_path: str,
    original_filename: str = None,
) -> List[Document]:
    """
    Auto-detect format and load a resume file with the best extraction
    strategy available.

    For PDFs:
      1. Try PyMuPDF text extraction
      2. If scanned → fallback to Gemini Vision
      3. Also extract tables via pdfplumber (appended as separate Documents)

    Parameters
    ----------
    file_path : str
        Path to the resume file on disk.
    original_filename : str, optional
        The real filename (e.g. "alice_resume.pdf").
        If not provided, uses the basename of file_path.

    Returns
    -------
    list[Document] — one or more Documents with enriched metadata.
    """
    ext = Path(file_path).suffix.lower()
    fname = original_filename or Path(file_path).name

    if ext == ".pdf":
        # Check if scanned first
        if _is_scanned_pdf(file_path):
            print(f"[LC Loader] Scanned PDF detected — using Gemini Vision")
            docs = load_pdf_with_vision(file_path, fname)
        else:
            docs = load_pdf(file_path, fname)

        # Also extract tables (appended as extra Documents)
        table_docs = extract_tables(file_path, fname)
        if table_docs:
            docs.extend(table_docs)

        return docs

    elif ext in (".docx", ".doc"):
        return load_docx(file_path, fname)

    elif ext in (".txt", ".text", ".md"):
        return load_txt(file_path, fname)

    else:
        raise ValueError(f"Unsupported file type: {ext}. Use PDF, DOCX, or TXT.")


def get_full_text(docs: List[Document]) -> str:
    """Merge all page_content from a list of Documents into one string."""
    return "\n\n".join(d.page_content for d in docs if d.page_content.strip())


# ---------------------------------------------------------------------------
# Quick heuristic extractors (same as before, used for identity resolution)
# ---------------------------------------------------------------------------

_EMAIL_RE    = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.I)
_PHONE_RE    = re.compile(r"(?:\+?\d[\d\s\-().]{6,}\d)")
_LINKEDIN_RE = re.compile(r"linkedin\.com/in/[\w\-]+", re.I)
_GITHUB_RE   = re.compile(r"github\.com/[\w\-]+", re.I)


def extract_quick_fields(text: str) -> dict:
    """
    Fast regex extraction of key identity fields from raw resume text.
    Used for the merger's identity resolution step BEFORE the LLM runs.
    """
    email   = (m := _EMAIL_RE.search(text)) and m.group(0).lower()
    phone   = (m := _PHONE_RE.search(text)) and m.group(0).strip()
    linkedin = (m := _LINKEDIN_RE.search(text)) and f"https://{m.group(0)}"
    github   = (m := _GITHUB_RE.search(text))  and f"https://{m.group(0)}"

    # Name heuristic: first 2-4 capitalized words in first 5 lines
    name = None
    for line in text.splitlines()[:6]:
        line = line.strip()
        if not line or "@" in line or "http" in line.lower() or len(line) > 60:
            continue
        words = line.split()
        if 2 <= len(words) <= 5 and all(w[0].isupper() for w in words if w.isalpha()):
            name = line
            break

    return {
        k: v for k, v in {
            "name":       name    or None,
            "email":      email   or None,
            "phone":      phone   or None,
            "linkedin":   linkedin or None,
            "github_url": github  or None,
        }.items() if v
    }
