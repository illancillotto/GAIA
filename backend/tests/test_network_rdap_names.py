"""Characterize RDAP entity-name selection through the existing extractor."""

from copy import deepcopy

import pytest

from app.modules.network.router.helpers import devices


def _entity(*rows):
    return {"vcardArray": ["vcard", list(rows)]}


def _name(value, field="fn"):
    return [field, {}, "text", value]


@pytest.mark.parametrize("entities", [None, {}, (), "entities", 1])
def test_only_an_entity_list_is_traversed(entities):
    assert devices._extract_rdap_entity_names({"entities": entities}) == []


@pytest.mark.parametrize(
    "entity",
    [
        None,
        [],
        "entity",
        {},
        {"vcardArray": None},
        {"vcardArray": ()},
        {"vcardArray": []},
        {"vcardArray": ["vcard"]},
        {"vcardArray": ["vcard", [], "extra"]},
        {"vcardArray": ["vcard", None]},
        {"vcardArray": ["vcard", (_name("tuple"),)]},
    ],
)
def test_entities_without_a_two_element_vcard_with_a_row_list_are_ignored(entity):
    assert devices._extract_rdap_entity_names({"entities": [entity]}) == []


@pytest.mark.parametrize(
    "row",
    [
        None,
        (),
        ("fn", {}, "text", "tuple"),
        [],
        ["fn", {}, "text"],
        [["unhashable but too short"]],
        _name("ignored", "email"),
        _name("ignored", "FN"),
        _name(None),
        _name(123),
        _name(""),
        _name("  \t\n"),
    ],
)
def test_invalid_or_blank_name_rows_do_not_hide_a_later_valid_row(row):
    assert devices._extract_rdap_entity_names({"entities": [_entity(row, _name(" Valid "))]}) == [
        "Valid"
    ]


def test_each_entity_contributes_its_first_valid_name_then_names_are_stably_deduplicated():
    poison = _name("unreachable", [])
    payload = {
        "entities": [
            _entity(_name("   "), _name(" Acme ", "org"), _name("Other"), poison),
            _entity(_name("Acme")),
            _entity(_name("ACME")),
            _entity(_name(" caffè ", "org")),
            _entity(_name("ignored", "email"), _name("Last")),
        ]
    }
    snapshot = deepcopy(payload)
    assert devices._extract_rdap_entity_names(payload) == ["Acme", "ACME", "caffè", "Last"]
    assert payload == snapshot


def test_vcard_marker_and_extra_name_row_fields_are_not_new_validation_requirements():
    payload = {"entities": [{"vcardArray": [None, [["fn", None, None, " Name ", "extra"]]]}]}
    assert devices._extract_rdap_entity_names(payload) == ["Name"]


def test_unhashable_name_field_still_raises_before_later_entities_are_visited():
    with pytest.raises(TypeError, match="unhashable"):
        devices._extract_rdap_entity_names(
            {"entities": [_entity(_name("bad", [])), _entity(_name("Later"))]}
        )


@pytest.mark.parametrize("second_value", ["Changed", "", None, 0])
def test_accepted_string_is_stripped_twice_and_the_second_result_is_kept(second_value):
    trace = []
    results = iter(["Accepted", second_value])

    class ChangingString(str):
        def strip(self):
            trace.append("strip")
            return next(results)

    value = ChangingString("Original")
    assert devices._extract_rdap_entity_names({"entities": [_entity(_name(value))]}) == [
        second_value
    ]
    assert trace == ["strip", "strip"]


def test_unhashable_second_strip_result_still_raises_during_final_deduplication():
    results = iter(["Accepted", []])

    class ChangingString(str):
        def strip(self):
            return next(results)

    with pytest.raises(TypeError, match="unhashable"):
        devices._extract_rdap_entity_names(
            {"entities": [_entity(_name(ChangingString("Original")))]}
        )


def test_vcard_and_name_row_reads_keep_their_order_and_multiplicity():
    trace = []

    class Sequence(list):
        def __init__(self, label, values):
            super().__init__(values)
            self.label = label

        def __len__(self):
            trace.append((self.label, "len"))
            return super().__len__()

        def __getitem__(self, index):
            trace.append((self.label, "get", index))
            return super().__getitem__(index)

    class Name(str):
        def strip(self):
            trace.append(("strip",))
            return "Name"

    row = Sequence("row", _name(Name(" Name ")))
    vcard = Sequence("vcard", ["vcard", [row]])
    assert devices._extract_rdap_entity_names({"entities": [{"vcardArray": vcard}]}) == ["Name"]
    assert trace == [
        ("vcard", "len"),
        ("vcard", "get", 1),
        ("vcard", "get", 1),
        ("row", "len"),
        ("row", "get", 0),
        ("row", "get", 3),
        ("row", "get", 3),
        ("strip",),
        ("row", "get", 3),
        ("strip",),
    ]
