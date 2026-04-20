"""PDF parsing service using PyMuPDF.

Extracts full text, chapter/section structure, and reference list from academic PDFs.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF


@dataclass
class ParsedSection:
    idx: int
    title: str
    content: str
    level: int = 1
    page_start: int | None = None
    page_end: int | None = None


@dataclass
class ParsedReference:
    idx: int
    raw_text: str
    title: str | None = None
    authors: str | None = None
    year: int | None = None
    venue: str | None = None


@dataclass
class ParsedPaper:
    title: str
    authors: str | None = None
    keywords: str | None = None
    page_count: int = 0
    full_text: str = ""
    sections: list[ParsedSection] = field(default_factory=list)
    references: list[ParsedReference] = field(default_factory=list)


_HEADING_RE = re.compile(
    r"^(\d+\.?\s+|[IVXLC]+\.?\s+|[A-Z]\.?\s+)"
    r"(Abstract|Introduction|Related\s+Work|Background|Method|Approach|"
    r"Experiment|Result|Discussion|Conclusion|Acknowledge|Reference|Appendix)",
    re.IGNORECASE,
)

_KEYWORDS_RE = re.compile(
    r"(?:Keywords|Key\s*words|KEYWORDS|KEY\s*WORDS)\s*[:：—\-]\s*(.+)",
    re.IGNORECASE,
)

_REF_SPLIT_RE = re.compile(r"\n\[(\d+)\]")
_YEAR_RE = re.compile(r"((?:19|20)\d{2})")


def _detect_headings(blocks: list[dict], page_idx: int) -> list[tuple[str, int, int]]:
    """Return (heading_text, level, page) tuples detected in page blocks."""
    headings: list[tuple[str, int, int]] = []
    for b in blocks:
        if b["type"] != 0:
            continue
        for line in b.get("lines", []):
            text = "".join(span["text"] for span in line.get("spans", [])).strip()
            if not text or len(text) > 200:
                continue
            avg_size = sum(s["size"] for s in line["spans"]) / len(line["spans"]) if line["spans"] else 0
            bold = any("bold" in s.get("font", "").lower() for s in line["spans"])
            if _HEADING_RE.match(text) or (bold and avg_size >= 11 and len(text) < 120):
                level = 1 if avg_size >= 13 else 2
                headings.append((text, level, page_idx))
    return headings


def _extract_keywords(text: str) -> str | None:
    """Extract the Keywords line from the first few thousand characters of the paper."""
    # Keywords typically appear near the top (abstract area)
    search_area = text[:5000]
    m = _KEYWORDS_RE.search(search_area)
    if not m:
        return None
    raw = m.group(1).strip()
    # Take content up to the next line break or section heading
    raw = re.split(r"\n\s*\n|\n\d+\.?\s+[A-Z]", raw)[0].strip()
    raw = re.sub(r"\s+", " ", raw).strip(" .;")
    return raw if raw else None


def _extract_references(text: str) -> list[ParsedReference]:
    ref_section = ""
    for marker in ("References", "REFERENCES", "Bibliography", "BIBLIOGRAPHY"):
        pos = text.rfind(marker)
        if pos != -1:
            ref_section = text[pos:]
            break
    if not ref_section:
        return []

    parts = _REF_SPLIT_RE.split(ref_section)
    refs: list[ParsedReference] = []
    i = 1
    while i < len(parts) - 1:
        try:
            idx = int(parts[i])
        except ValueError:
            i += 2
            continue
        raw = parts[i + 1].strip().replace("\n", " ")
        year_match = _YEAR_RE.search(raw)
        year = int(year_match.group(1)) if year_match else None
        refs.append(ParsedReference(idx=idx, raw_text=raw, year=year))
        i += 2
    return refs


def parse_pdf(file_path: str | Path) -> ParsedPaper:
    doc = fitz.open(str(file_path))
    page_count = len(doc)

    all_text_parts: list[str] = []
    all_headings: list[tuple[str, int, int]] = []

    for page_idx in range(page_count):
        page = doc[page_idx]
        text = page.get_text("text")
        all_text_parts.append(text)
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        all_headings.extend(_detect_headings(blocks, page_idx))

    full_text = "\n".join(all_text_parts)

    # Extract title from first page (largest font text)
    first_page = doc[0]
    blocks0 = first_page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
    title = _extract_title(blocks0)

    # Build sections from headings
    sections: list[ParsedSection] = []
    for i, (heading_text, level, page_idx) in enumerate(all_headings):
        start_pos = full_text.find(heading_text)
        if i + 1 < len(all_headings):
            next_heading = all_headings[i + 1][0]
            end_pos = full_text.find(next_heading, start_pos + len(heading_text))
            if end_pos == -1:
                end_pos = len(full_text)
        else:
            end_pos = len(full_text)

        content = full_text[start_pos:end_pos].strip()
        next_page = all_headings[i + 1][2] if i + 1 < len(all_headings) else page_count - 1
        sections.append(ParsedSection(
            idx=i,
            title=heading_text,
            content=content,
            level=level,
            page_start=page_idx,
            page_end=next_page,
        ))

    if not sections and full_text.strip():
        sections.append(ParsedSection(
            idx=0,
            title="Full Text",
            content=full_text.strip(),
            level=1,
            page_start=0,
            page_end=page_count - 1,
        ))

    keywords = _extract_keywords(full_text)
    references = _extract_references(full_text)
    doc.close()

    return ParsedPaper(
        title=title,
        keywords=keywords,
        page_count=page_count,
        full_text=full_text,
        sections=sections,
        references=references,
    )


def _extract_title(blocks: list[dict]) -> str:
    candidates: list[tuple[float, str]] = []
    for b in blocks:
        if b["type"] != 0:
            continue
        for line in b.get("lines", []):
            text = "".join(s["text"] for s in line.get("spans", [])).strip()
            if not text or len(text) < 5:
                continue
            avg_size = sum(s["size"] for s in line["spans"]) / len(line["spans"]) if line["spans"] else 0
            candidates.append((avg_size, text))
    if not candidates:
        return "Untitled"
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1][:512]


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """Split text into overlapping chunks for embedding."""
    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap
    return chunks
