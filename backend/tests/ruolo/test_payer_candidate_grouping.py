"""Characterize payer grouping through the public candidate transformation."""

from copy import deepcopy
from itertools import product
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

from app.modules.ruolo.services import payer_assignments as service


def _avviso(number):
    return {
        "id": UUID(int=number),
        "anno_tributario": 2020 + number,
        "adjusted_due_amount": str(number * 10),
        "paid_amount": str(number),
        "saldo_amount": str(number * 9),
        "annuality_manager_label": f"manager-{number}",
        "residenza_raw": "original address",
        "domicilio_raw": "original domicile",
    }


def _candidate(avvisi, name="Owner"):
    return {
        "avvisi": avvisi,
        "display_name": name,
        "codice_fiscale": "OWNER",
        "subject_id": UUID(int=100),
        "metadata": {"keep": "shared"},
    }


def _payers():
    first = service.Payer(UUID(int=11), "FIRST", "First payer", "Via A", "/first")
    second = service.Payer(UUID(int=12), "SECOND", "Second payer", None, None)
    return {
        UUID(int=1): (SimpleNamespace(reason="decesso"), first),
        UUID(int=2): (SimpleNamespace(reason="vendita"), second),
        UUID(int=3): (SimpleNamespace(reason="ufficio"), first),
    }


def test_no_assignments_return_the_original_list_without_rebuilding(monkeypatch):
    load = Mock(return_value={})
    monkeypatch.setattr(service, "active_payers", load)
    db = object()
    for candidates in ([], [_candidate([])], [_candidate([_avviso(1)])]):
        assert service.reassign_candidates(db, candidates) is candidates
        load.assert_called_with(db, [a["id"] for c in candidates for a in c["avvisi"]])


def test_grouping_preserves_order_duplicates_totals_and_first_assignment(monkeypatch):
    payers = _payers()
    load = Mock(return_value=payers)
    monkeypatch.setattr(service, "active_payers", load)
    db = object()
    avvisi = [_avviso(number) for number in range(4)]
    # Exhaust all short sequences, including repeats of the same dictionary.
    for size in range(5):
        for numbers in product(range(4), repeat=size):
            selected = [avvisi[number] for number in numbers]
            candidate = _candidate(selected)
            snapshot = deepcopy(candidate)
            result = service.reassign_candidates(db, [candidate])
            load.assert_called_with(db, [avviso["id"] for avviso in selected])
            own = [avviso for avviso in selected if avviso["id"] not in payers]
            group_ids = list(
                dict.fromkeys(payers[a["id"]][1].subject_id for a in selected if a["id"] in payers)
            )
            assert len(result) == bool(own) + len(group_ids)
            offset = int(bool(own))
            if own:
                assert result[0]["avvisi"] == own
                assert all(
                    actual is expected
                    for actual, expected in zip(result[0]["avvisi"], own, strict=True)
                )
                assert (result[0] is candidate) == (not group_ids)
            for group_id, actual in zip(group_ids, result[offset:], strict=True):
                grouped = [
                    a
                    for a in selected
                    if a["id"] in payers and payers[a["id"]][1].subject_id == group_id
                ]
                assignment, payer = payers[grouped[0]["id"]]
                assert actual is not candidate
                assert actual["subject_id"] == group_id
                assert actual["codice_fiscale"] == payer.tax_code
                assert actual["display_name"] == payer.name
                assert actual["nas_folder_path"] == payer.nas_folder_path
                assert actual["has_nas_folder"] == bool(payer.nas_folder_path)
                assert actual["payer_assignment"] == {
                    "intestatario": "Owner",
                    "codice_fiscale": "OWNER",
                    "reason": assignment.reason,
                    "role": {"decesso": "erede", "vendita": "acquirente"}.get(assignment.reason),
                }
                assert actual["avvisi"] == [
                    {**a, "residenza_raw": payer.address, "domicilio_raw": None} for a in grouped
                ]
                assert all(a is not b for a, b in zip(actual["avvisi"], grouped, strict=True))
                assert actual["avvisi_count"] == len(grouped)
                assert actual["years"] == sorted({a["anno_tributario"] for a in grouped})
                assert actual["annuality_managers"] == sorted(
                    {a["annuality_manager_label"] for a in grouped}
                )
                for field, source in (
                    ("due_amount", "adjusted_due_amount"),
                    ("paid_amount", "paid_amount"),
                    ("saldo_amount", "saldo_amount"),
                ):
                    assert actual[field] == sum(float(a[source]) for a in grouped)
                assert actual["surcharge_amount"] == actual["interest_amount"] == 0
                assert actual["metadata"] is candidate["metadata"]
            assert candidate == snapshot


def test_candidates_stay_separate_even_when_they_share_a_payer(monkeypatch):
    monkeypatch.setattr(service, "active_payers", Mock(return_value=_payers()))
    first = _candidate([_avviso(1)], "First owner")
    unchanged = _candidate([_avviso(0)], "Unchanged owner")
    last = _candidate([_avviso(3)], "Last owner")
    result = service.reassign_candidates(object(), [first, unchanged, last])
    assert len(result) == 3
    assert result[1] is unchanged
    assert [result[i]["payer_assignment"]["intestatario"] for i in (0, 2)] == [
        "First owner",
        "Last owner",
    ]
    assert result[0]["subject_id"] == result[2]["subject_id"]
    assert result[0]["payer_assignment"]["reason"] == "decesso"
    assert result[2]["payer_assignment"]["reason"] == "ufficio"
