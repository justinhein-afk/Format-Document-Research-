"""Claude-assisted labeling for blocks the rules could not settle.

Only compact summaries of each block are sent (truncated text plus a few formatting
features), and only for documents that have uncertain blocks, to keep a free tool cheap.
"""

from __future__ import annotations

import json
import logging
import os
import anthropic
from pydantic import BaseModel

from .models import Block, Label

log = logging.getLogger(__name__)

MODEL = os.environ.get("APA_CLASSIFIER_MODEL", "claude-haiku-4-5")
WINDOW = 150  # blocks per request
CONTEXT = 5  # neighbouring blocks included on each side of a window
TEXT_LIMIT = 220

SYSTEM_PROMPT = f"""You label the structure of research papers so they can be reformatted in APA 7th edition style.

You receive the paper as a list of blocks in document order. Each block has an index `i`, \
its text (long paragraphs are truncated), and formatting hints: `b` bold, `it` italic, \
`sz` font size in points, `al` alignment, `caps` all caps, `list` list item, `img` contains \
an image, `eq` contains an equation, `style` the Word style name. Some blocks already carry \
a `known` label; they are given for context and are correct. Some carry a `guess` from a \
simple heuristic, which may be wrong.

Return a label for every block whose `i` is listed in `label_these`.

Labels:
- title: the paper's title (usually the first line, often bold, centered, or large). Only one.
- author: author name line(s) on the title page.
- affiliation: university/department/institution line on the title page.
- course: course number and name (student papers), e.g. "PSY 101: Introduction to Psychology".
- instructor: instructor's name, e.g. "Dr. Jane Smith".
- date: the assignment due date or paper date on the title page.
- author_note: author note paragraph (ORCID, disclosures, correspondence) on the title page.
- abstract_heading: the word "Abstract" as a heading.
- abstract_body: paragraph(s) of the abstract.
- keywords: the "Keywords:" line.
- heading_1 .. heading_5: section headings. Level 1 = main sections (Introduction, Method, \
Results, Discussion, Conclusion), level 2 = subsections, level 3 = sub-subsections, and so on. \
Infer the level from numbering ("2.1" is level 2), formatting, and the outline of the paper. \
A heading is short and is not a full sentence.
- body: ordinary paragraph text.
- block_quote: a long quotation set off from the text.
- list_item: an item of a bulleted or numbered list.
- equation: a display equation.
- figure: a paragraph that holds an image.
- figure_caption: "Figure N" label and/or figure title.
- table: a table.
- table_caption: "Table N" label and/or table title.
- note: a "Note." paragraph under a table or figure.
- reference_heading: the "References"/"Bibliography" heading.
- reference_entry: one entry of the reference list.
- appendix_heading: "Appendix" or "Appendix A" heading (or the title line right after it).
- footnote_text: a footnote that was typed as normal text at the end of the paper.
- ignore: junk that should be dropped (stray page numbers, running heads typed into the body, \
"Page 3 of 10", table of contents lines, separator lines).

Mark `sure` false when you are unsure about a block, so a person checks it."""

class BlockLabel(BaseModel):
    i: int
    label: Label
    sure: bool


class LabelResult(BaseModel):
    labels: list[BlockLabel]


def ai_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _summarize(b: Block, include: bool) -> dict:
    d: dict = {"i": b.index, "text": b.text[:TEXT_LIMIT] + ("…" if len(b.text) > TEXT_LIMIT else "")}
    if b.kind == "table":
        d["table"] = True
    for key, value in (("b", b.bold), ("it", b.italic), ("caps", b.all_caps), ("list", b.is_list),
                       ("img", b.has_image), ("eq", b.has_equation)):
        if value:
            d[key] = True
    if b.size_pt:
        d["sz"] = b.size_pt
    if b.align and b.align != "left":
        d["al"] = b.align
    if b.style and b.style.lower() not in ("normal", "default paragraph font", "body text"):
        d["style"] = b.style
    if include:
        d["guess"] = b.label.value
    else:
        d["known"] = b.label.value
    return d


def classify_with_ai(blocks: list[Block], client: anthropic.Anthropic | None = None) -> int:
    """Relabel every block with confidence < 1. Returns the number of blocks labeled by AI."""
    targets = [b for b in blocks if b.confidence < 1.0]
    if not targets:
        return 0
    client = client or anthropic.Anthropic(max_retries=2, timeout=90)

    labeled = 0
    for start in range(0, len(blocks), WINDOW):
        window = blocks[start:start + WINDOW]
        wanted = [b.index for b in window if b.confidence < 1.0]
        if not wanted:
            continue
        lo, hi = max(0, start - CONTEXT), min(len(blocks), start + WINDOW + CONTEXT)
        payload = {
            "blocks": [_summarize(b, include=b.index in wanted) for b in blocks[lo:hi]],
            "label_these": wanted,
        }
        result = _request(client, payload)
        if result is None:
            continue
        by_index = {b.index: b for b in window}
        wanted_set = set(wanted)
        for item in result.labels:
            block = by_index.get(item.i)
            if block is None or item.i not in wanted_set:
                continue
            block.label = item.label
            block.confidence = 0.9 if item.sure else 0.5
            block.source = "ai"
            labeled += 1
    return labeled


def _request(client: anthropic.Anthropic, payload: dict) -> LabelResult | None:
    try:
        response = client.messages.parse(
            model=MODEL,
            max_tokens=16000,
            temperature=0,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
            output_format=LabelResult,
        )
    except anthropic.RateLimitError:
        log.warning("Claude rate limited; falling back to heuristics for this window")
        return None
    except anthropic.APIStatusError as exc:
        log.warning("Claude API error %s; falling back to heuristics", exc.status_code)
        return None
    except anthropic.APIConnectionError:
        log.warning("Could not reach Claude; falling back to heuristics")
        return None
    except ValueError:  # response did not validate against LabelResult
        log.warning("Classifier returned malformed labels; falling back to heuristics")
        return None
    if response.stop_reason != "end_turn" or response.parsed_output is None:
        log.warning("Unusable classifier response (stop_reason=%s)", response.stop_reason)
        return None
    return response.parsed_output
