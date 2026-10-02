"""Deterministic labeling.

Strong rules (confidence 1.0) are trusted as-is. Weak heuristics (< 1.0) are guesses
that the AI pass may override; they are also the fallback when AI is unavailable.
"""

from __future__ import annotations

import re

from .models import Block, Label, LEVEL_TO_HEADING

STRONG = 1.0
WEAK = 0.4
DEFAULT = 0.3

_ABSTRACT_HEADING = re.compile(r"^abstract\s*[:.]?$", re.I)
_ABSTRACT_INLINE = re.compile(r"^abstract\s*[:.\-–—]\s*\S", re.I)
_KEYWORDS = re.compile(r"^(key\s?words|index terms)\s*[:.\-–—]", re.I)
_REFERENCES = re.compile(
    r"^(\d+\.?\s*)?(references|reference list|bibliography|works cited|literature cited|sources)\s*[:.]?$", re.I
)
_APPENDIX = re.compile(r"^appendix(\s+[A-Z0-9]{1,3})?\b", re.I)
_CAPTION = re.compile(r"^(figure|fig\.|table)\s*(\d+[a-z]?|[A-Z]\d+)\s*([.:\-–—]|$)", re.I)
_CAPTION_LOOSE = re.compile(r"^(figure|fig\.|table)\s*(\d+[a-z]?|[A-Z]\d+)\b", re.I)
_NOTE = re.compile(r"^notes?\s*[.:]\s*\S", re.I)
_NUMBERED_HEADING = re.compile(r"^((\d{1,2})(\.\d{1,2})*)\.?\s+\S")
_ROMAN_HEADING = re.compile(r"^[IVX]+\.\s+\S")
_HEADING_STYLE = re.compile(r"^heading\s*([1-9])$", re.I)
_AFFILIATION = re.compile(r"\b(universit|college|department|institute|school|faculty|laborator|hospital|center|centre)", re.I)
_COURSE = re.compile(r"^[A-Z]{2,5}[\s-]?\d{2,4}[A-Z]?\b")
_INSTRUCTOR = re.compile(r"^(dr\.?|prof\.?|professor|instructor)\b", re.I)
_DATE = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b.*\d{4}"
    r"|^\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}$",
    re.I,
)


def _set(block: Block, label: Label, confidence: float, source: str = "rules") -> None:
    block.label = label
    block.confidence = confidence
    block.source = source  # type: ignore[assignment]


def _looks_like_heading(b: Block) -> bool:
    text = b.text
    return (
        0 < len(text) <= 120
        and len(text.split()) <= 15
        and not text.endswith((".", ",", ";"))
        or bool(_NUMBERED_HEADING.match(text) and len(text) <= 120 and not text.endswith("."))
    )


def apply_rules(blocks: list[Block]) -> None:
    in_references = False
    in_abstract = False
    seen_content = False  # anything after the title page (abstract, headings, body)
    seen_title = False

    for b in blocks:
        text = b.text
        style = (b.style or "").strip()

        # --- structural certainties -------------------------------------------------
        if b.kind == "table":
            _set(b, Label.TABLE, STRONG)
            continue
        if b.has_equation and len(text) <= 10:
            _set(b, Label.EQUATION, STRONG)
            continue
        if b.has_image and len(text) <= 3:
            _set(b, Label.FIGURE, STRONG)
            continue
        if not text:
            _set(b, Label.IGNORE, STRONG)
            continue

        # --- unambiguous section markers -------------------------------------------
        if _REFERENCES.match(text):
            _set(b, Label.REFERENCE_HEADING, STRONG)
            in_references = seen_content = True
            continue
        if _APPENDIX.match(text) and len(text) <= 80:
            _set(b, Label.APPENDIX_HEADING, STRONG)
            in_references = False
            seen_content = True
            continue
        if in_references:
            _set(b, Label.REFERENCE_ENTRY, STRONG)
            continue
        if _ABSTRACT_HEADING.match(text):
            _set(b, Label.ABSTRACT_HEADING, STRONG)
            seen_content = in_abstract = True
            continue
        if _ABSTRACT_INLINE.match(text):
            _set(b, Label.ABSTRACT_BODY, STRONG)
            seen_content = True
            continue
        if _KEYWORDS.match(text):
            _set(b, Label.KEYWORDS, STRONG)
            seen_content = True
            in_abstract = False
            continue
        if _CAPTION.match(text) and len(text) <= 300:
            is_table = text.lower().startswith("table")
            _set(b, Label.TABLE_CAPTION if is_table else Label.FIGURE_CAPTION, STRONG)
            continue
        if _NOTE.match(text):
            _set(b, Label.NOTE, STRONG)
            continue

        # --- Word's own styles -------------------------------------------------------
        if style.lower() == "title":
            _set(b, Label.TITLE, STRONG)
            seen_title = True
            continue
        m = _HEADING_STYLE.match(style)
        if m and int(m.group(1)) <= 5:
            _set(b, LEVEL_TO_HEADING[int(m.group(1))], STRONG)
            seen_content = True
            continue
        if style.lower() in ("quote", "intense quote", "block text"):
            _set(b, Label.BLOCK_QUOTE, STRONG)
            continue
        if style.lower() == "caption":
            _set(b, Label.TABLE_CAPTION if text.lower().startswith("table") else Label.FIGURE_CAPTION, STRONG)
            continue

        # --- weak guesses ------------------------------------------------------------
        if not seen_content and not seen_title and len(text) <= 250 and (
            b.bold or b.align == "center" or (b.size_pt or 0) > 12.5
        ):
            _set(b, Label.TITLE, WEAK, "heuristic")
            seen_title = True
            continue
        if not seen_content and seen_title and len(text) <= 200:
            _set(b, _title_page_label(text), WEAK, "heuristic")
            continue
        if in_abstract:
            if _looks_like_heading(b) and _guess_heading_level(b) is not None:
                in_abstract = False
            else:
                _set(b, Label.ABSTRACT_BODY, WEAK, "heuristic")
                continue
        if _CAPTION_LOOSE.match(text) and len(text) <= 200 and not text.endswith("."):
            is_table = text.lower().startswith("table")
            _set(b, Label.TABLE_CAPTION if is_table else Label.FIGURE_CAPTION, WEAK, "heuristic")
            continue
        if _looks_like_heading(b):
            level = _guess_heading_level(b)
            if level is not None:
                _set(b, LEVEL_TO_HEADING[level], WEAK, "heuristic")
                seen_content = True
                continue
        if b.is_list:
            _set(b, Label.LIST_ITEM, WEAK, "heuristic")
            seen_content = True
            continue

        _set(b, Label.BODY, DEFAULT, "heuristic")
        seen_content = True


def _title_page_label(text: str) -> Label:
    if _DATE.search(text):
        return Label.DATE
    if _INSTRUCTOR.match(text):
        return Label.INSTRUCTOR
    if _COURSE.match(text):
        return Label.COURSE
    if _AFFILIATION.search(text):
        return Label.AFFILIATION
    return Label.AUTHOR


def _guess_heading_level(b: Block) -> int | None:
    text = b.text
    m = _NUMBERED_HEADING.match(text)
    if m and (b.bold or len(text.split()) <= 8):
        depth = m.group(1).count(".") + 1
        return min(depth, 5)
    if _ROMAN_HEADING.match(text) and (b.bold or b.all_caps):
        return 1
    if b.all_caps and len(text) <= 80:
        return 1
    if b.bold and b.align == "center":
        return 1
    if b.bold and b.italic:
        return 3
    if b.bold:
        return 2
    if (b.size_pt or 0) >= 13:
        return 1
    return None
