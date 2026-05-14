from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class SisterSelectorsConfig:
    login_url: str = "https://iampe.agenziaentrate.gov.it/sam/UI/Login?realm=/agenziaentrate"
    login_tab_selector: str = "a.nav-link[href='#tab-5']"
    username_selector: str = "#username-sister"
    password_selector: str = "#password-sister"
    login_button_selector: str = "#tab-5 form button[type='submit']"
    confirm_button_xpath: str = "//input[@value='Conferma']"
    territorio_selector: str = "select[name='listacom']"
    territorio_apply_button_name: str = "Applica"
    territorio_value: str = "ORISTANO Territorio-OR"
    consultazioni_link_name: str = "Consultazioni e Certificazioni"
    visure_link_name: str = "Visure catastali"
    conferma_lettura_button_name: str = "Conferma Lettura"
    immobile_link_name: str = "Immobile"
    subject_pf_url: str = "https://sister3.agenziaentrate.gov.it/Visure/SceltaLink.do?lista=PF&codUfficio=OR"
    subject_pnf_url: str = "https://sister3.agenziaentrate.gov.it/Visure/SceltaLink.do?lista=PNF&codUfficio=OR"
    catasto_selector: str = "select[name='tipoCatasto']"
    comune_selector: str = "select[name='denomComune']"
    sezione_input_selector: str = "input[name='sezione']"
    sezione_select_selector: str = "select[name='sezione']"
    foglio_selector: str = "input[name='foglio']"
    particella_selector: str = "input[name='particella1']"
    subalterno_selector: str = "input[name='subalterno1']"
    motivo_selector: str = "select[name='motivoLista']"
    motivo_value: str = "Altri fini istituzionali "
    visura_button_selector: str = "input[name='scelta'][value='Visura']"
    subject_search_button_selectors: list[str] | None = None
    subject_open_visura_button_selectors: list[str] | None = None
    subject_result_selector_candidates: list[str] | None = None
    tipo_visura_selector: str = "input[name='tipoVisura']"
    captcha_field_selector: str = "input[name='inCaptchaChars']"
    captcha_image_selector: str = "img[src*='captcha' i]"
    inoltra_button_selector: str = "input[name='inoltra'][value='Inoltra']"
    save_button_selector: str = "input[name='metodo'][value='Salva']"

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> "SisterSelectorsConfig":
        resolved_path = _resolve_config_path(config_path)
        raw = _load_override_data(resolved_path)
        default_payload = asdict(cls())
        unknown_keys = set(raw) - set(default_payload)
        if unknown_keys:
            raise ValueError(
                f"Unknown SISTER selector keys in {resolved_path}: {', '.join(sorted(unknown_keys))}",
            )
        payload = {**default_payload, **raw}
        return cls(**payload)


def _resolve_config_path(config_path: str | Path | None) -> Path:
    if config_path is not None:
        return Path(config_path)

    env_value = os.getenv("ELABORAZIONI_SISTER_SELECTORS_PATH", os.getenv("CATASTO_SISTER_SELECTORS_PATH"))
    if env_value:
        return Path(env_value)

    return Path(__file__).with_name("sister_selectors.json")


def _load_override_data(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}

    with config_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise ValueError(f"SISTER selector config must be a JSON object: {config_path}")

    return payload
