import importlib.util
import sys
import types
from pathlib import Path
from uuid import uuid4

from app.schemas.catasto_phase1 import CatAnagraficaMatch, CatAnagraficaUtenzaSummary, CatIntestatarioResponse

if "shapely" not in sys.modules:
    shapely_module = types.ModuleType("shapely")
    shapely_geometry = types.ModuleType("shapely.geometry")
    shapely_geometry.shape = lambda value: value
    shapely_module.geometry = shapely_geometry
    sys.modules["shapely"] = shapely_module
    sys.modules["shapely.geometry"] = shapely_geometry

if "geoalchemy2" not in sys.modules:
    geoalchemy2_module = types.ModuleType("geoalchemy2")
    geoalchemy2_shape = types.ModuleType("geoalchemy2.shape")
    geoalchemy2_shape.to_shape = lambda value: value
    geoalchemy2_module.shape = geoalchemy2_shape
    sys.modules["geoalchemy2"] = geoalchemy2_module
    sys.modules["geoalchemy2.shape"] = geoalchemy2_shape

_MODULE_PATH = Path(__file__).resolve().parents[1] / "app/modules/catasto/routes/anagrafica.py"
_SPEC = importlib.util.spec_from_file_location("catasto_anagrafica_route_under_test", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
CapacitasLiveAuthoritativeSanitizer = _MODULE.CapacitasLiveAuthoritativeSanitizer


def _build_match(*, cert_com: str | None, cert_pvc: str | None, cert_fra: str | None) -> CatAnagraficaMatch:
    return CatAnagraficaMatch(
        particella_id=uuid4(),
        unit_id=None,
        comune_id=uuid4(),
        comune="Uras",
        cod_comune_capacitas=289,
        codice_catastale="L496",
        foglio="14",
        particella="1079",
        subalterno=None,
        num_distretto=None,
        nome_distretto=None,
        superficie_mq=None,
        superficie_grafica_mq=None,
        presente_in_catasto_consorzio=True,
        utenza_latest=CatAnagraficaUtenzaSummary(
            id=uuid4(),
            cco="000000033",
            anno_campagna=2025,
            stato="capacitas_live",
            num_distretto=None,
            nome_distretto=None,
            sup_irrigabile_mq=None,
            denominazione="Comune Di Marrubiu",
            codice_fiscale="80001090952",
            ha_anomalie=None,
        ),
        cert_com=cert_com,
        cert_pvc=cert_pvc,
        cert_fra=cert_fra,
        cert_ccs="00000" if cert_com and cert_pvc and cert_fra else None,
        stato_ruolo="Iscrivibile a ruolo",
        stato_cnc="Lista 1",
        intestatari=[
            CatIntestatarioResponse(
                id=uuid4(),
                codice_fiscale="80001090952",
                denominazione="Comune Di Marrubiu",
                tipo="PF",
                cognome="Comune",
                nome="Di Marrubiu",
                data_nascita=None,
                luogo_nascita=None,
                indirizzo="PIAZZA Roma 7",
                comune_residenza="MARRUBIU",
                cap="09094",
                email=None,
                telefono=None,
                ragione_sociale=None,
                source="capacitas",
                last_verified_at=None,
                deceduto=None,
            )
        ],
        anomalie_count=0,
        anomalie_top=[],
        note=None,
    )


def test_capacitas_live_authoritative_sanitizer_clears_match_without_context() -> None:
    sanitizer = CapacitasLiveAuthoritativeSanitizer()
    match = _build_match(cert_com=None, cert_pvc=None, cert_fra=None)

    sanitized = sanitizer.sanitize(match)

    assert sanitized.intestatari == []
    assert sanitized.stato_ruolo is None
    assert sanitized.stato_cnc is None
    assert sanitized.cert_com is None
    assert sanitized.cert_pvc is None
    assert sanitized.cert_fra is None
    assert sanitized.cert_ccs is None


def test_capacitas_live_authoritative_sanitizer_keeps_match_with_context() -> None:
    sanitizer = CapacitasLiveAuthoritativeSanitizer()
    match = _build_match(cert_com="289", cert_pvc="097", cert_fra="38")

    sanitized = sanitizer.sanitize(match)

    assert len(sanitized.intestatari) == 1
    assert sanitized.stato_ruolo == "Iscrivibile a ruolo"
    assert sanitized.stato_cnc == "Lista 1"
    assert sanitized.cert_com == "289"
    assert sanitized.cert_pvc == "097"
    assert sanitized.cert_fra == "38"
    assert sanitized.cert_ccs == "00000"
