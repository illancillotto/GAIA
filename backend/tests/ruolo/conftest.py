from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _td896_sample_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ruolo tests render the TD 896 slip without a real Poste authorization code.
    monkeypatch.setattr("app.core.config.settings.td896_sample_mode", True)
