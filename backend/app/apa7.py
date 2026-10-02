"""APA 7th edition layout rules expressed as Word styles and text helpers."""

from __future__ import annotations

import re

from docx.document import Document as DocxDocument
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from .models import FontChoice

INDENT = Inches(0.5)

FONTS: dict[FontChoice, tuple[str, float]] = {
    FontChoice.TIMES_NEW_ROMAN_12: ("Times New Roman", 12),
    FontChoice.CALIBRI_11: ("Calibri", 11),
    FontChoice.ARIAL_11: ("Arial", 11),
    FontChoice.GEORGIA_11: ("Georgia", 11),
    FontChoice.LUCIDA_SANS_UNICODE_10: ("Lucida Sans Unicode", 10),
}

# name -> (base, bold, italic, alignment, first-line indent, left indent, hanging, keep-with-next, single-spaced)
_PARAGRAPH_STYLES = {
    "APA Body": ("Normal", None, None, WD_ALIGN_PARAGRAPH.LEFT, INDENT, None, False, False, False),
    "APA Title": ("Normal", True, None, WD_ALIGN_PARAGRAPH.CENTER, Inches(0), None, False, True, False),
    "APA Title Page": ("Normal", None, None, WD_ALIGN_PARAGRAPH.CENTER, Inches(0), None, False, True, False),
    "APA Section Label": ("Normal", True, None, WD_ALIGN_PARAGRAPH.CENTER, Inches(0), None, False, True, False),
    "APA Abstract": ("Normal", None, None, WD_ALIGN_PARAGRAPH.LEFT, Inches(0), None, False, False, False),
    "APA Keywords": ("Normal", None, None, WD_ALIGN_PARAGRAPH.LEFT, INDENT, None, False, False, False),
    "APA Block Quote": ("Normal", None, None, WD_ALIGN_PARAGRAPH.LEFT, Inches(0), INDENT, False, False, False),
    "APA List": ("Normal", None, None, WD_ALIGN_PARAGRAPH.LEFT, None, None, False, False, False),
    "APA Equation": ("Normal", None, None, WD_ALIGN_PARAGRAPH.CENTER, Inches(0), None, False, False, False),
    "APA Figure": ("Normal", None, None, WD_ALIGN_PARAGRAPH.LEFT, Inches(0), None, False, False, False),
    "APA Caption Label": ("Normal", True, None, WD_ALIGN_PARAGRAPH.LEFT, Inches(0), None, False, True, False),
    "APA Caption Title": ("Normal", None, True, WD_ALIGN_PARAGRAPH.LEFT, Inches(0), None, False, True, False),
    "APA Note": ("Normal", None, None, WD_ALIGN_PARAGRAPH.LEFT, Inches(0), None, False, False, False),
    "APA Table Text": ("Normal", None, None, WD_ALIGN_PARAGRAPH.LEFT, Inches(0), None, False, False, True),
    "APA Reference": ("Normal", None, None, WD_ALIGN_PARAGRAPH.LEFT, None, INDENT, True, False, False),
    "APA Footnote": ("Normal", None, None, WD_ALIGN_PARAGRAPH.LEFT, INDENT, None, False, False, False),
}

# Built-in heading styles keep Word's navigation pane and outline working.
_HEADINGS = {
    1: (True, False, WD_ALIGN_PARAGRAPH.CENTER),
    2: (True, False, WD_ALIGN_PARAGRAPH.LEFT),
    3: (True, True, WD_ALIGN_PARAGRAPH.LEFT),
}


def setup_document(doc: DocxDocument, font: FontChoice) -> None:
    """Page setup, base font and every APA style used by the renderer."""
    name, size = FONTS[font]

    for section in doc.sections:
        section.page_width, section.page_height = Inches(8.5), Inches(11)
        section.top_margin = section.bottom_margin = Inches(1)
        section.left_margin = section.right_margin = Inches(1)
        section.header_distance = section.footer_distance = Inches(0.5)

    normal = doc.styles["Normal"]
    _set_font(normal, name, size)
    pf = normal.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.DOUBLE
    pf.space_before = pf.space_after = Pt(0)
    pf.widow_control = True
    _set_doc_defaults(doc, name, size)

    for style_name, (base, bold, italic, align, first, left, hanging, keep, single) in _PARAGRAPH_STYLES.items():
        style = _get_or_add_paragraph_style(doc, style_name)
        style.base_style = doc.styles[base]
        style.font.bold = bold
        style.font.italic = italic
        spf = style.paragraph_format
        spf.alignment = align
        spf.space_before = spf.space_after = Pt(0)
        spf.line_spacing_rule = WD_LINE_SPACING.SINGLE if single else WD_LINE_SPACING.DOUBLE
        if hanging:
            spf.left_indent = INDENT
            spf.first_line_indent = -INDENT
        else:
            if first is not None:
                spf.first_line_indent = first
            if left is not None:
                spf.left_indent = left
        spf.keep_with_next = keep
        style.quick_style = True

    for level in range(1, 6):
        style = doc.styles[f"Heading {level}"]
        bold, italic, align = _HEADINGS.get(level, (True, level == 5, WD_ALIGN_PARAGRAPH.LEFT))
        _set_font(style, name, size)
        style.font.bold = bold
        style.font.italic = italic
        style.font.color.rgb = RGBColor(0, 0, 0)
        spf = style.paragraph_format
        spf.alignment = align
        spf.space_before = spf.space_after = Pt(0)
        spf.line_spacing_rule = WD_LINE_SPACING.DOUBLE
        spf.first_line_indent = INDENT if level >= 4 else Inches(0)
        spf.left_indent = Inches(0)
        spf.keep_with_next = True

    for style_name in ("Header", "Footer"):
        if style_name in [s.name for s in doc.styles]:
            _set_font(doc.styles[style_name], name, size)


def _get_or_add_paragraph_style(doc: DocxDocument, name: str):
    try:
        return doc.styles[name]
    except KeyError:
        return doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)


def _set_font(style, name: str, size: float) -> None:
    style.font.name = name
    style.font.size = Pt(size)
    rpr = style.element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.insert(0, fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(attr), name)
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        fonts.attrib.pop(qn(attr), None)


def _set_doc_defaults(doc: DocxDocument, name: str, size: float) -> None:
    styles_el = doc.styles.element
    rpr_default = styles_el.find(f"{qn('w:docDefaults')}/{qn('w:rPrDefault')}/{qn('w:rPr')}")
    if rpr_default is None:
        return
    fonts = rpr_default.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr_default.insert(0, fonts)
    fonts.attrib.clear()
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(attr), name)
    for tag in ("w:sz", "w:szCs"):
        el = rpr_default.find(qn(tag))
        if el is None:
            el = OxmlElement(tag)
            rpr_default.append(el)
        el.set(qn("w:val"), str(int(size * 2)))


# --- text helpers -----------------------------------------------------------------------

_MINOR_WORDS = {
    "a", "an", "the", "and", "but", "or", "nor", "for", "so", "yet", "as", "at", "by", "in", "of", "off", "on",
    "per", "to", "up", "via", "vs", "vs.",
}
_WORD = re.compile(r"[A-Za-z][A-Za-z'’]*")


def title_case(text: str) -> str:
    """APA title case: capitalize major words and words of four letters or more.

    Words that are already capitalized mid-word or fully capitalized (iPhone, fMRI, USA)
    are left alone unless the whole string is in capitals.
    """
    shouting = text.isupper()
    if shouting:
        text = text.lower()

    out: list[str] = []
    pos = 0
    first = True
    after_colon = False
    for m in _WORD.finditer(text):
        between = text[pos:m.start()]
        out.append(between)
        if re.search(r"[:?!—–]\s*$", between):
            after_colon = True
        word = m.group(0)
        preceded_by_hyphen = between.endswith("-")
        lower = word.lower()
        keep_as_is = not shouting and any(c.isupper() for c in word[1:])
        if keep_as_is:
            out.append(word)
        elif not first and not after_colon and lower in _MINOR_WORDS and not preceded_by_hyphen:
            out.append(lower)
        elif preceded_by_hyphen and len(word) <= 3 and lower in _MINOR_WORDS:
            out.append(lower)
        else:
            out.append(word[0].upper() + word[1:])
        first = False
        after_colon = False
        pos = m.end()
    out.append(text[pos:])
    return "".join(out)


_HEADING_NUMBER = re.compile(r"^\s*((\d{1,2}(\.\d{1,2})*\.?)|([IVXLC]+\.)|([A-H]\.))\s+(?=\S)")
_REFERENCE_NUMBER = re.compile(r"^\s*(\[\d+\]|\d+\.|\(\d+\))\s+")
_KEYWORDS_PREFIX = re.compile(r"^\s*(key\s?words|index terms)\s*[:.\-–—]\s*", re.I)
_ABSTRACT_PREFIX = re.compile(r"^\s*abstract\s*[:.\-–—]\s*", re.I)
_CAPTION = re.compile(r"^\s*(figure|fig\.|table)\s*(\d+[a-z]?|[A-Z]\d+)\s*[.:\-–—]?\s*", re.I)


def strip_heading_number(text: str) -> str:
    return _HEADING_NUMBER.sub("", text, count=1)


def strip_reference_number(text: str) -> str:
    return _REFERENCE_NUMBER.sub("", text, count=1)


def strip_keywords_prefix(text: str) -> str:
    return _KEYWORDS_PREFIX.sub("", text, count=1)


def strip_abstract_prefix(text: str) -> str:
    return _ABSTRACT_PREFIX.sub("", text, count=1)


def split_caption(text: str) -> tuple[str, str] | None:
    """'Figure 2. Mean scores by group' -> ('Figure 2', 'Mean scores by group')."""
    m = _CAPTION.match(text)
    if not m:
        return None
    kind = "Table" if m.group(1).lower() == "table" else "Figure"
    return f"{kind} {m.group(2)}", text[m.end():].strip()


def caption_prefix_length(text: str) -> int:
    m = _CAPTION.match(text)
    return m.end() if m else 0


def reference_sort_key(text: str) -> str:
    return re.sub(r"^[^A-Za-z0-9]+", "", strip_reference_number(text)).casefold()
