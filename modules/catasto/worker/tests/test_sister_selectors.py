from pathlib import Path
import json
import sys

import pytest


WORKER_ROOT = Path(__file__).resolve().parents[1]

if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

from sister_selectors import SisterSelectorsConfig


def test_sister_selectors_load_defaults_from_repo_config() -> None:
    config = SisterSelectorsConfig.load()

    assert config.login_tab_selector == "a.nav-link[href='#tab-5']"
    assert config.comune_selector == "select[name='denomComune']"
    assert config.save_button_selector == "input[name='metodo'][value='Salva']"


def test_sister_selectors_allow_targeted_override(tmp_path) -> None:
    config_path = tmp_path / "selectors.json"
    config_path.write_text(
        json.dumps(
            {
                "territorio_value": "CAGLIARI Territorio-CA",
                "immobile_link_name": "Immobile urbano",
            }
        ),
        encoding="utf-8",
    )

    config = SisterSelectorsConfig.load(config_path)

    assert config.territorio_value == "CAGLIARI Territorio-CA"
    assert config.immobile_link_name == "Immobile urbano"
    assert config.login_url.startswith("https://")


def test_sister_selectors_reject_unknown_keys(tmp_path) -> None:
    config_path = tmp_path / "selectors.json"
    config_path.write_text(json.dumps({"unknown_selector": "#broken"}), encoding="utf-8")

    with pytest.raises(ValueError, match="Unknown SISTER selector keys"):
        SisterSelectorsConfig.load(config_path)
