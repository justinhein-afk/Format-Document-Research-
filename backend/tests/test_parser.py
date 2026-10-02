from app.parser import parse_docx


def test_blocks_in_order_with_features(paper_bytes):
    parsed = parse_docx(paper_bytes)
    assert len(parsed.blocks) == len(parsed.elements)
    texts = [b.text for b in parsed.blocks]
    assert texts[0] == "THE EFFECTS OF SLEEP ON MEMORY CONSOLIDATION"
    first = parsed.blocks[0]
    assert first.bold and first.all_caps and first.align == "center" and first.size_pt == 16
    assert any(b.kind == "table" for b in parsed.blocks)
    assert any(b.has_image for b in parsed.blocks)
    assert any(b.has_equation for b in parsed.blocks)
    assert sum(b.is_list for b in parsed.blocks) == 3
    # hyperlink text is part of the paragraph text
    assert any("this review" in t for t in texts)
