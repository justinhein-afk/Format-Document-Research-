"""Read a .docx into an ordered list of Blocks, keeping each block's XML element.

The renderer later copies those elements into the APA document, so images, tables,
equations and inline formatting survive untouched.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from docx import Document
from docx.document import Document as DocxDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from lxml import etree

from .models import Block

_ALIGN_NAMES = {
    WD_ALIGN_PARAGRAPH.LEFT: "left",
    WD_ALIGN_PARAGRAPH.CENTER: "center",
    WD_ALIGN_PARAGRAPH.RIGHT: "right",
    WD_ALIGN_PARAGRAPH.JUSTIFY: "justify",
}

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"


@dataclass
class ParsedDocument:
    doc: DocxDocument
    blocks: list[Block]
    elements: list[etree._Element]  # elements[i] belongs to blocks[i]


def parse_docx(data: bytes) -> ParsedDocument:
    doc = Document(io.BytesIO(data))
    body = doc.element.body
    _accept_tracked_changes(body)
    _strip_comments(body)

    blocks: list[Block] = []
    elements: list[etree._Element] = []
    for el in _iter_block_elements(body):
        index = len(blocks)
        if el.tag == qn("w:tbl"):
            blocks.append(Block(index=index, kind="table", text=_table_preview(el)))
        else:
            blocks.append(_paragraph_block(index, Paragraph(el, doc)))
        elements.append(el)
    return ParsedDocument(doc=doc, blocks=blocks, elements=elements)


def _iter_block_elements(container):
    """Yield top-level paragraphs and tables, flattening content controls (w:sdt)."""
    for child in container.iterchildren():
        if child.tag in (qn("w:p"), qn("w:tbl")):
            yield child
        elif child.tag == qn("w:sdt"):
            content = child.find(qn("w:sdtContent"))
            if content is not None:
                yield from _iter_block_elements(content)


def _accept_tracked_changes(root) -> None:
    """Accept all revisions: keep insertions, drop deletions and change history."""
    for tag in ("w:del", "w:moveFrom"):
        for el in list(root.iter(qn(tag))):
            el.getparent().remove(el)
    for tag in ("w:ins", "w:moveTo"):
        for el in list(root.iter(qn(tag))):
            parent = el.getparent()
            if parent is None:
                continue
            if parent.tag == qn("w:rPr"):  # inserted paragraph mark: just a marker
                parent.remove(el)
                continue
            idx = parent.index(el)
            for child in list(el):
                parent.insert(idx, child)
                idx += 1
            parent.remove(el)
    for tag in ("w:rPrChange", "w:pPrChange", "w:sectPrChange", "w:tblPrChange", "w:trPrChange", "w:tcPrChange",
                "w:moveFromRangeStart", "w:moveFromRangeEnd", "w:moveToRangeStart", "w:moveToRangeEnd"):
        for el in list(root.iter(qn(tag))):
            el.getparent().remove(el)


def _strip_comments(root) -> None:
    for tag in ("w:commentRangeStart", "w:commentRangeEnd"):
        for el in list(root.iter(qn(tag))):
            el.getparent().remove(el)
    for ref in list(root.iter(qn("w:commentReference"))):
        run = ref.getparent()
        if run.tag == qn("w:r"):
            run.getparent().remove(run)
        else:
            run.remove(ref)


def paragraph_text(p_el) -> str:
    parts: list[str] = []
    for el in p_el.iter(qn("w:t"), qn("w:tab"), qn("w:br")):
        if el.tag == qn("w:t"):
            parts.append(el.text or "")
        elif el.tag == qn("w:tab"):
            parts.append("\t")
        elif el.get(qn("w:type")) not in ("page", "column"):
            parts.append(" ")
    return "".join(parts)


def _table_preview(tbl_el) -> str:
    rows = []
    for tr in tbl_el.iter(qn("w:tr")):
        cells = [paragraph_text(tc).strip() for tc in tr.iter(qn("w:tc"))]
        rows.append(" | ".join(cells))
        if len(rows) == 3:
            break
    return "\n".join(rows)


def _style_chain(style):
    while style is not None:
        yield style
        style = style.base_style


def _style_font_attr(style, attr):
    for s in _style_chain(style):
        value = getattr(s.font, attr)
        if value is not None:
            return value
    return None


def _paragraph_block(index: int, para: Paragraph) -> Block:
    p_el = para._p
    text = paragraph_text(p_el).strip()
    try:
        style = para.style
    except (KeyError, ValueError):
        style = None
    style_bold = bool(_style_font_attr(style, "bold")) if style is not None else False
    style_italic = bool(_style_font_attr(style, "italic")) if style is not None else False
    style_size = _style_font_attr(style, "size") if style is not None else None

    bold_chars = italic_chars = total_chars = 0
    sizes: list[float] = []
    for run in para.iter_inner_content():
        runs = run.runs if hasattr(run, "runs") else [run]  # hyperlinks contain runs
        for r in runs:
            n = len(r.text.strip())
            if not n:
                continue
            total_chars += n
            if (r.bold if r.bold is not None else style_bold):
                bold_chars += n
            if (r.italic if r.italic is not None else style_italic):
                italic_chars += n
            size = r.font.size or style_size
            if size is not None:
                sizes.append(size.pt)

    alignment = para.alignment
    if alignment is None and style is not None:
        for s in _style_chain(style):
            if s.paragraph_format.alignment is not None:
                alignment = s.paragraph_format.alignment
                break

    letters = [c for c in text if c.isalpha()]
    num_pr = p_el.find(f"{qn('w:pPr')}/{qn('w:numPr')}")
    return Block(
        index=index,
        kind="paragraph",
        text=text,
        style=style.name if style is not None else None,
        bold=total_chars > 0 and bold_chars / total_chars >= 0.9,
        italic=total_chars > 0 and italic_chars / total_chars >= 0.9,
        size_pt=max(sizes) if sizes else None,
        align=_ALIGN_NAMES.get(alignment),
        all_caps=len(letters) >= 2 and all(c.isupper() for c in letters),
        is_list=num_pr is not None or (style is not None and "List" in (style.name or "")),
        has_image=any(True for _ in p_el.iter(qn("w:drawing"), qn("w:pict"))),
        has_equation=any(True for _ in p_el.iter(f"{{{M_NS}}}oMath")),
    )
