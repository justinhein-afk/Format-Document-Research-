"""Shared data types for the parse -> classify -> render pipeline."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Label(str, Enum):
    """Semantic role of one block in a research paper."""

    # Title page
    TITLE = "title"
    AUTHOR = "author"
    AFFILIATION = "affiliation"
    COURSE = "course"
    INSTRUCTOR = "instructor"
    DATE = "date"
    AUTHOR_NOTE = "author_note"
    # Abstract
    ABSTRACT_HEADING = "abstract_heading"
    ABSTRACT_BODY = "abstract_body"
    KEYWORDS = "keywords"
    # Body
    HEADING_1 = "heading_1"
    HEADING_2 = "heading_2"
    HEADING_3 = "heading_3"
    HEADING_4 = "heading_4"
    HEADING_5 = "heading_5"
    BODY = "body"
    BLOCK_QUOTE = "block_quote"
    LIST_ITEM = "list_item"
    EQUATION = "equation"
    # Figures and tables
    FIGURE = "figure"
    FIGURE_CAPTION = "figure_caption"
    TABLE = "table"
    TABLE_CAPTION = "table_caption"
    NOTE = "note"
    # Back matter
    REFERENCE_HEADING = "reference_heading"
    REFERENCE_ENTRY = "reference_entry"
    APPENDIX_HEADING = "appendix_heading"
    FOOTNOTE_TEXT = "footnote_text"
    # Dropped from output (blank lines, stray page-break paragraphs, etc.)
    IGNORE = "ignore"


TITLE_PAGE_LABELS = frozenset(
    {Label.TITLE, Label.AUTHOR, Label.AFFILIATION, Label.COURSE, Label.INSTRUCTOR, Label.DATE, Label.AUTHOR_NOTE}
)
ABSTRACT_LABELS = frozenset({Label.ABSTRACT_HEADING, Label.ABSTRACT_BODY, Label.KEYWORDS})
HEADING_LEVELS = {
    Label.HEADING_1: 1,
    Label.HEADING_2: 2,
    Label.HEADING_3: 3,
    Label.HEADING_4: 4,
    Label.HEADING_5: 5,
}
LEVEL_TO_HEADING = {v: k for k, v in HEADING_LEVELS.items()}

LabelSource = Literal["rules", "heuristic", "ai", "user", "repair"]


class Block(BaseModel):
    """One top-level body element of the source document (a paragraph or a table)."""

    index: int
    kind: Literal["paragraph", "table"]
    text: str
    style: str | None = None
    bold: bool = False
    italic: bool = False
    size_pt: float | None = None
    align: Literal["left", "center", "right", "justify"] | None = None
    all_caps: bool = False
    is_list: bool = False
    has_image: bool = False
    has_equation: bool = False
    # Filled in by the classifier
    label: Label = Label.BODY
    confidence: float = 0.0
    source: LabelSource = "heuristic"


class PaperType(str, Enum):
    STUDENT = "student"
    PROFESSIONAL = "professional"


class FontChoice(str, Enum):
    TIMES_NEW_ROMAN_12 = "Times New Roman 12"
    CALIBRI_11 = "Calibri 11"
    ARIAL_11 = "Arial 11"
    GEORGIA_11 = "Georgia 11"
    LUCIDA_SANS_UNICODE_10 = "Lucida Sans Unicode 10"


class RenderOptions(BaseModel):
    paper_type: PaperType = PaperType.STUDENT
    font: FontChoice = FontChoice.TIMES_NEW_ROMAN_12
    include_title_page: bool = True
    running_head: str | None = Field(default=None, max_length=50)
    title_case_headings: bool = True
    sort_references: bool = True


class LabelAssignment(BaseModel):
    index: int
    label: Label


class AnalyzeResponse(BaseModel):
    blocks: list[Block]
    ai_used: bool
    warnings: list[str] = []
