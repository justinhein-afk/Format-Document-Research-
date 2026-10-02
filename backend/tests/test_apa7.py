from app import apa7


def test_title_case():
    assert apa7.title_case("the effects of sleep on memory") == "The Effects of Sleep on Memory"
    assert apa7.title_case("THE EFFECTS OF SLEEP") == "The Effects of Sleep"
    assert apa7.title_case("fMRI evidence: a review of the field") == "fMRI Evidence: A Review of the Field"
    assert apa7.title_case("self-report measures in research") == "Self-Report Measures in Research"


def test_prefix_helpers():
    assert apa7.strip_heading_number("2.1 Method") == "Method"
    assert apa7.strip_heading_number("IV. Results") == "Results"
    assert apa7.strip_heading_number("2020 Census Data") == "2020 Census Data"
    assert apa7.strip_reference_number("[12] Smith, J. (2020).") == "Smith, J. (2020)."
    assert apa7.split_caption("Figure 2: Mean scores") == ("Figure 2", "Mean scores")
    assert apa7.split_caption("Table 3") == ("Table 3", "")
    assert apa7.split_caption("Results showed") is None
