"""Label blocks: rules first, Claude for what is left, then repair the outline."""

from __future__ import annotations

import logging

from .ai_classifier import ai_available, classify_with_ai
from .models import ABSTRACT_LABELS, HEADING_LEVELS, LEVEL_TO_HEADING, TITLE_PAGE_LABELS, Block, Label
from .rules import apply_rules

log = logging.getLogger(__name__)


def classify(blocks: list[Block], use_ai: bool = True, client=None) -> tuple[bool, list[str]]:
    """Label blocks in place. Returns (ai_used, warnings)."""
    warnings: list[str] = []
    apply_rules(blocks)
    ai_used = False
    if use_ai and (client is not None or ai_available()):
        try:
            ai_used = classify_with_ai(blocks, client=client) > 0
        except Exception:  # never fail an upload because the AI pass broke
            log.exception("AI classification failed")
        if not ai_used and any(b.confidence < 1.0 for b in blocks):
            warnings.append("AI labeling was unavailable, so some labels are rough guesses. Please review them.")
    elif any(b.confidence < 1.0 for b in blocks):
        warnings.append("AI labeling is turned off, so some labels are rough guesses. Please review them.")
    repair(blocks)
    return ai_used, warnings


def _relabel(block: Block, label: Label) -> None:
    if block.label != label:
        block.label = label
        block.source = "repair"
        block.confidence = min(block.confidence, 0.5)


def repair(blocks: list[Block]) -> None:
    """Enforce structural rules that hold for any APA paper."""
    content = [b for b in blocks if b.label != Label.IGNORE]

    # One title; any later "title" is really a heading.
    titles = [b for b in content if b.label == Label.TITLE]
    for extra in titles[1:]:
        _relabel(extra, Label.HEADING_1)

    # Title-page labels only make sense before the paper body starts.
    body_started = False
    for b in content:
        if b.label in TITLE_PAGE_LABELS:
            if body_started and b.label != Label.TITLE:
                _relabel(b, Label.BODY)
        elif b.label not in ABSTRACT_LABELS:
            body_started = True

    # Everything between the reference heading and the next appendix is a reference.
    in_refs = False
    for b in content:
        if b.label == Label.REFERENCE_HEADING:
            in_refs = True
        elif b.label == Label.APPENDIX_HEADING:
            in_refs = False
        elif in_refs and b.label not in (Label.FIGURE, Label.TABLE, Label.FIGURE_CAPTION, Label.TABLE_CAPTION,
                                         Label.NOTE, Label.REFERENCE_ENTRY, Label.FOOTNOTE_TEXT):
            _relabel(b, Label.REFERENCE_ENTRY)

    # Heading levels never skip (an H1 followed by an H3 becomes H1 -> H2).
    previous = 0
    for b in content:
        if b.label in (Label.APPENDIX_HEADING, Label.REFERENCE_HEADING):
            previous = 1
            continue
        level = HEADING_LEVELS.get(b.label)
        if level is None:
            continue
        if level > previous + 1:
            level = previous + 1
            _relabel(b, LEVEL_TO_HEADING[level])
        previous = level
