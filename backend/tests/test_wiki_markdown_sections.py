import pytest

from app.modules.wiki.mcps.docs.corpus import markdown_sections


@pytest.mark.parametrize("marker", ["`", "~"])
@pytest.mark.parametrize("opening_length", [3, 4, 6])
@pytest.mark.parametrize("closing_length", [3, 4, 6, 8])
@pytest.mark.parametrize("same_marker", [True, False])
@pytest.mark.parametrize("indentation", [0, 3, 4])
@pytest.mark.parametrize("suffix", ["", " ignored suffix"])
def test_fence_closure_preserves_literal_headings(
    marker, opening_length, closing_length, same_marker, indentation, suffix
):
    opening = marker * opening_length + "markdown"
    closing_marker = marker if same_marker else {"`": "~", "~": "`"}[marker]
    closing = " " * indentation + closing_marker * closing_length + suffix
    first_section = f"# First\n{opening}\n## Literal\n{closing}"
    content = f"Preamble\n{first_section}\n# After\nTail"
    closes = same_marker and closing_length >= opening_length and indentation <= 3
    if closes:
        expected = [(None, "Preamble"), ("First", first_section), ("After", "# After\nTail")]
    else:
        expected = [(None, "Preamble"), ("First", first_section + "\n# After\nTail")]
    assert markdown_sections(content) == expected


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("", []),
        (" \n\t\n", []),
        ("# Heading\n```\n```\n# Next", [("Heading", "# Heading\n```\n```"), ("Next", "# Next")]),
        ("# Title ###\r\nBody", [("Title", "# Title ###\nBody")]),
        ("####### Not a heading", [(None, "####### Not a heading")]),
        ("# " + "x" * 305, [("x" * 300, "# " + "x" * 305)]),
    ],
)
def test_section_boundaries_and_normalization(content, expected):
    assert markdown_sections(content) == expected
