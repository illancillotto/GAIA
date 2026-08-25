import pytest

from app.modules.organigramma.positions import position_code_from_title


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Dirigente", "dirigente"),
        ("Direttore generale", "dirigente"),
        ("Capo settore", "capo_settore"),
        ("Capo operai", "capo_operai"),
        ("Capo operaio", "capo_operai"),
        ("Capo reparto", "capo_reparto"),
        ("Collaboratore", None),
        (None, None),
    ],
)
def test_position_code_from_title(title: str | None, expected: str | None) -> None:
    assert position_code_from_title(title) == expected
