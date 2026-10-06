from pathlib import PurePosixPath

import pytest

from app.modules.wiki.mcps.docs.corpus import validate_source_path


@pytest.mark.parametrize(
    "source_path",
    [
        "docs/file.md",
        "domain-docs/catasto/docs/file.md",
        "domain-docs/file.md",
        "docs/.hidden.md",
        "docs/..md",
        "docs/a..b.md",
        "docs/nested/README.md",
        "docs/spaces in name.md",
        "docs/città.md",
        "docs/line\nbreak.md",
        "docs/file.txt.md",
        "docs/C:/file.md",
    ],
)
def test_canonical_markdown_paths_preserve_existing_contract(source_path):
    assert validate_source_path(source_path) == PurePosixPath(source_path)


@pytest.mark.parametrize(
    ("source_path", "message"),
    [
        ("", "Expected a canonical Markdown path"),
        (".", "Expected a canonical Markdown path"),
        ("./", "Expected a canonical Markdown path"),
        ("docs", "Expected a canonical Markdown path"),
        ("docs/", "Expected a canonical Markdown path"),
        ("docs/.md", "Expected a canonical Markdown path"),
        ("docs/file.MD", "Expected a canonical Markdown path"),
        ("docs/file.md ", "Expected a canonical Markdown path"),
        ("docs/file.txt", "Expected a canonical Markdown path"),
        ("docs//file.md", "Expected a canonical Markdown path"),
        ("docs/./file.md", "Expected a canonical Markdown path"),
        ("./docs/file.md", "Expected a canonical Markdown path"),
        ("docs/file.md/", "Expected a canonical Markdown path"),
        ("/docs/file.md", "Invalid document path"),
        ("//docs/file.md", "Invalid document path"),
        ("/docs/file.txt", "Invalid document path"),
        ("../docs/file.md", "Invalid document path"),
        ("docs/../file.md", "Invalid document path"),
        ("docs/..", "Invalid document path"),
        ("docs\\file.md", "Invalid document path"),
        ("C:\\docs\\file.txt", "Invalid document path"),
        ("docs/file\x00.md", "Invalid document path"),
        ("backend/file.md", "Document outside the allowed corpus roots"),
        ("Docs/file.md", "Document outside the allowed corpus roots"),
        (" docs/file.md", "Document outside the allowed corpus roots"),
        ("file.md", "Document outside the allowed corpus roots"),
        ("domain-docs.md", "Document outside the allowed corpus roots"),
    ],
)
def test_invalid_paths_preserve_error_precedence(source_path, message):
    with pytest.raises(ValueError, match=rf"^{message}$"):
        validate_source_path(source_path)
