from app.classifier import classify, repair
from app.models import Block, Label
from app.parser import parse_docx


def _labels(paper_bytes):
    parsed = parse_docx(paper_bytes)
    classify(parsed.blocks, use_ai=False)
    return {b.text: b.label for b in parsed.blocks if b.text}


def test_rules_and_heuristics(paper_bytes):
    labels = _labels(paper_bytes)
    assert labels["THE EFFECTS OF SLEEP ON MEMORY CONSOLIDATION"] == Label.TITLE
    assert labels["Jane Q. Student"] == Label.AUTHOR
    assert labels["Department of Psychology, State University"] == Label.AFFILIATION
    assert labels["PSY 301: Research Methods"] == Label.COURSE
    assert labels["Dr. Alan Turing"] == Label.INSTRUCTOR
    assert labels["March 3, 2026"] == Label.DATE
    assert labels["Abstract"] == Label.ABSTRACT_HEADING
    assert labels["Keywords: sleep, memory, consolidation"] == Label.KEYWORDS
    assert labels["1. Introduction"] == Label.HEADING_1
    assert labels["1.1 prior work on sleep"] == Label.HEADING_2
    assert labels["theoretical framing"] == Label.HEADING_3
    assert labels["Table 1. participant demographics by condition"] == Label.TABLE_CAPTION
    assert labels["Figure 1: Recall accuracy in the sleep and wake groups"] == Label.FIGURE_CAPTION
    assert labels["Note. Ages are means in years."] == Label.NOTE
    assert labels["References"] == Label.REFERENCE_HEADING
    assert labels["[2] Alpha, B. (2019). Consolidation revisited. Academic Press."] == Label.REFERENCE_ENTRY
    assert labels["Appendix A: survey items"] == Label.APPENDIX_HEADING


def _block(i, label, text="x"):
    return Block(index=i, kind="paragraph", text=text, label=label, confidence=0.9, source="ai")


def test_repair_heading_levels_do_not_skip():
    blocks = [_block(0, Label.HEADING_1), _block(1, Label.HEADING_3), _block(2, Label.HEADING_4)]
    repair(blocks)
    assert [b.label for b in blocks] == [Label.HEADING_1, Label.HEADING_2, Label.HEADING_3]


def test_repair_single_title_and_references():
    blocks = [
        _block(0, Label.TITLE), _block(1, Label.BODY), _block(2, Label.TITLE),
        _block(3, Label.REFERENCE_HEADING), _block(4, Label.BODY), _block(5, Label.APPENDIX_HEADING),
        _block(6, Label.BODY), _block(7, Label.AUTHOR),
    ]
    repair(blocks)
    assert blocks[2].label == Label.HEADING_1
    assert blocks[4].label == Label.REFERENCE_ENTRY
    assert blocks[6].label == Label.BODY
    assert blocks[7].label == Label.BODY  # title-page label after the body started


class _FakeMessages:
    def __init__(self, labels):
        self.labels = labels
        self.calls = []

    def parse(self, **kwargs):
        from types import SimpleNamespace

        from app.ai_classifier import LabelResult
        import json

        self.calls.append(kwargs)
        wanted = json.loads(kwargs["messages"][0]["content"])["label_these"]
        out = LabelResult(labels=[{"i": i, "label": self.labels.get(i, "body"), "sure": True} for i in wanted])
        return SimpleNamespace(stop_reason="end_turn", parsed_output=out)


class _FakeClient:
    def __init__(self, labels):
        self.messages = _FakeMessages(labels)


def test_ai_overrides_only_uncertain_blocks(paper_bytes):
    parsed = parse_docx(paper_bytes)
    client = _FakeClient({1: "author", 8: "abstract_body"})
    ai_used, warnings = classify(parsed.blocks, client=client)
    assert ai_used and not warnings
    assert parsed.blocks[8].label == Label.ABSTRACT_BODY and parsed.blocks[8].source == "ai"
    # strong rule labels are never sent for relabeling
    sent = __import__("json").loads(client.messages.calls[0]["messages"][0]["content"])["label_these"]
    references = next(b.index for b in parsed.blocks if b.text == "References")
    assert references not in sent
    assert client.messages.calls[0]["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_ai_failure_falls_back_to_heuristics(paper_bytes):
    class Broken:
        class messages:
            @staticmethod
            def parse(**kwargs):
                raise RuntimeError("boom")

    parsed = parse_docx(paper_bytes)
    ai_used, warnings = classify(parsed.blocks, client=Broken())
    assert not ai_used and warnings
    assert parsed.blocks[0].label == Label.TITLE
