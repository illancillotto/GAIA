from __future__ import annotations

import pytest

from app.modules.elaborazioni.bonifica_oristanese.parsers import (
    clean_html_text,
    extract_href_id,
    parse_form_fields,
)


@pytest.mark.parametrize(
    ("markup", "expected"),
    [(None, ""), (b"<b> bytes </b>", "bytes"), ("<b> a </b>\n c ", "a c"), (42, "42"), ("", "")],
)
def test_markup_normalization(markup, expected):
    assert clean_html_text(markup) == expected


@pytest.mark.parametrize(
    ("markup", "expected"),
    [
        (None, None),
        ("", None),
        ("<a>no href</a>", None),
        ('<a href="/other/12">a</a>', None),
        ('<a href="/item/text">a</a>', None),
        ('<a href="/other/12">a</a><a href="/item/text">b</a><a href="/item/003/">c</a>', 3),
    ],
)
def test_extract_href_id(markup, expected):
    assert extract_href_id(markup, "/item/") == expected


@pytest.mark.parametrize(
    ("markup", "expected"),
    [
        (None, {}),
        (42, {}),
        (b'<input name="x" value="bytes">', {"x": "bytes"}),
        ('<input><input name=""><input name="_token" value="x"><input name="_method">', {}),
        (
            '<input name="x" value="a"><input name="x" value="b"><input name="y">',
            {"x": "b", "y": ""},
        ),
        ('<textarea name="x">  a\n b  </textarea>', {"x": "a\n b"}),
        ('<select name="x"><option value="first">first</option></select>', {"x": ""}),
        (
            '<select name="x"><option selected value="a">A</option><option selected value="b">B</option></select>',
            {"x": "a"},
        ),
        ('<select name="x"><option selected>label</option></select>', {"x": ""}),
        (
            '<select name="x" multiple><option value="a" selected></option><option selected></option></select>',
            {"x": ["a", ""]},
        ),
        (
            '<select name="x[]"><option value="a" selected></option><option value="b"></option></select>',
            {"x[]": ["a"]},
        ),
        ('<select name="x[]" multiple></select>', {"x[]": []}),
        ('<input name="x" type="CHECKBOX" checked value="a">', {"x": True}),
        ('<input name="x" type="checkbox" value="a">', {"x": False}),
        (
            '<input name="x[]" type="checkbox" checked><input name="x[]" type="checkbox" value="b"><input name="x[]" type="checkbox" value="c" checked>',
            {"x[]": ["on", "c"]},
        ),
        (
            '<input name="x[]" value="old"><input name="x[]" type="checkbox" checked value="new">',
            {"x[]": ["new"]},
        ),
        (
            '<select name="x[]"><option selected value="old"></option></select><input name="x[]" type="checkbox" checked value="new">',
            {"x[]": ["old", "new"]},
        ),
        (
            '<input name="x" type="radio" value="a"><input name="x" type="radio" value="b">',
            {"x": ""},
        ),
        (
            '<input name="x" type="radio" value="a" checked><input name="x" type="radio" value="b">',
            {"x": "a"},
        ),
        (
            '<input name="x" type="radio" checked><input name="x" type="radio" value="b" checked>',
            {"x": "b"},
        ),
        ('<textarea name="x">old</textarea><input name="x" type="radio">', {"x": "old"}),
        (
            '<input name="x" type="" value="a"><input name="y" type="hidden" disabled value="b">',
            {"x": "a", "y": "b"},
        ),
    ],
)
def test_form_field_contract(markup, expected):
    result = parse_form_fields(markup)
    assert result == expected
    assert list(result) == list(expected)
    assert parse_form_fields(markup) == expected


def test_form_arrays_are_independent():
    markup = '<select name="x[]"><option selected value="a"></option></select>'
    first = parse_form_fields(markup)
    second = parse_form_fields(markup)
    first["x[]"].append("consumer")
    assert second == {"x[]": ["a"]}
    assert parse_form_fields(markup) == second
