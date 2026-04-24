from __future__ import annotations

from collections.abc import Generator
from datetime import date, datetime, timezone
from decimal import Decimal

from cryptography.fernet import Fernet
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.capacitas import CapacitasCredential
from app.models.capacitas import CapacitasTerreniSyncJob
from app.models.catasto_phase1 import (
    CatCapacitasCertificato,
    CatCapacitasTerrenoDetail,
    CatCapacitasTerrenoRow,
    CatComune,
    CatConsorzioOccupancy,
    CatConsorzioUnit,
    CatImportBatch,
    CatParticella,
    CatSchemaContributo,
    CatUtenzaIrrigua,
)
from app.modules.elaborazioni.capacitas.models import (
    CapacitasLookupOption,
    CapacitasSearchResult,
    CapacitasTerreniSearchResult,
    CapacitasTerrenoCertificato,
    CapacitasTerrenoDetail,
)
from app.services.catasto_credentials import get_credential_fernet


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    generated_key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setattr("app.services.catasto_credentials.settings.credential_master_key", generated_key)
    monkeypatch.setattr("app.core.config.settings.credential_master_key", generated_key)
    get_credential_fernet.cache_clear()

    db = TestingSessionLocal()
    db.add(
        ApplicationUser(
            username="elaborazioni-admin",
            email="elaborazioni@example.local",
            password_hash=hash_password("secret123"),
            role=ApplicationUserRole.ADMIN.value,
            is_active=True,
        )
    )
    comune_uras = CatComune(
        nome_comune="Uras",
        codice_catastale="L496",
        cod_comune_capacitas=289,
        codice_comune_formato_numerico=115087,
        codice_comune_numerico_2017_2025=95087,
        nome_comune_legacy="Uras",
        cod_provincia=115,
        sigla_provincia="OR",
        regione="Sardegna",
    )
    comune_arborea = CatComune(
        nome_comune="Arborea",
        codice_catastale="A357",
        cod_comune_capacitas=165,
        codice_comune_formato_numerico=115006,
        codice_comune_numerico_2017_2025=95006,
        nome_comune_legacy="Arborea",
        cod_provincia=115,
        sigla_provincia="OR",
        regione="Sardegna",
    )
    comune_terralba = CatComune(
        nome_comune="Terralba",
        codice_catastale="L122",
        cod_comune_capacitas=280,
        codice_comune_formato_numerico=115083,
        codice_comune_numerico_2017_2025=95082,
        nome_comune_legacy="Terralba",
        cod_provincia=115,
        sigla_provincia="OR",
        regione="Sardegna",
    )
    batch = CatImportBatch(
        filename="seed-terreni.xlsx",
        tipo="capacitas_ruolo",
        anno_campagna=2026,
        hash_file="seed-terreni",
        status="completed",
        righe_totali=1,
        righe_importate=1,
        righe_anomalie=0,
        created_by=1,
    )
    particella = CatParticella(
        comune=comune_uras,
        cod_comune_capacitas=289,
        codice_catastale="L496",
        nome_comune="Uras",
        foglio="1",
        particella="680",
        subalterno=None,
        num_distretto="34",
        nome_distretto="Distretto 34",
        is_current=True,
        superficie_mq=5500,
        superficie_grafica_mq=5480,
    )
    db.add_all(
        [
            comune_uras,
            comune_arborea,
            comune_terralba,
            batch,
            particella,
            CatParticella(
                comune=comune_terralba,
                cod_comune_capacitas=280,
                codice_catastale="L122",
                nome_comune="Terralba",
                foglio="14",
                particella="330",
                subalterno=None,
                num_distretto="25",
                nome_distretto="Distretto Terralba",
                is_current=True,
                superficie_mq=2100,
                superficie_grafica_mq=2088,
            ),
            CatSchemaContributo(codice="0648", descrizione="Schema 0648", tipo_calcolo="fisso", attivo=True),
            CatSchemaContributo(codice="0985", descrizione="Schema 0985", tipo_calcolo="contatori", attivo=True),
        ]
    )
    db.flush()
    db.add(
        CatUtenzaIrrigua(
            import_batch_id=batch.id,
            anno_campagna=2026,
            cco="0A1103877",
            comune_id=comune_uras.id,
            cod_comune_capacitas=289,
            nome_comune="Uras",
            foglio="1",
            particella="680",
            particella_id=particella.id,
            sup_catastale_mq=Decimal("5500.00"),
            sup_irrigabile_mq=Decimal("5500.00"),
            codice_fiscale="LSADNL68S48L496D",
            codice_fiscale_raw="LSADNL68S48L496D",
        )
    )
    db.commit()
    db.close()

    yield

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def auth_headers() -> dict[str, str]:
    response = client.post("/auth/login", json={"username": "elaborazioni-admin", "password": "secret123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_capacitas_decoder_decodes_real_payload() -> None:
    from app.modules.elaborazioni.capacitas.decoder import decode_response

    payload = (
        "SZ7VLLbtswEPwV3nwJYfEhkepNlptCgGMbihMEKAqUIlcpAVsMaLmHFP2yHvpJ/YVyHdvpNUWP3YM0uzucXSzm14+fH8"
        "m3Zv6OTLiShQPGqAGlqOz6nppOldQJ6wxnrtCynFyRZv5QLavEz/qyE6UD6nTeU6nyjHagLe1sntnCaa7AJP7taMaA9ITXZ"
        "ox+FwaPBfoSK0qxEx9TSSQ09wnIBDbrBPCPwwiOXt/XKFSqhOvVDe6s8Uldr7BeZbrgRYmDrqN5Rj2OC9gvgG2MlM5g2/sQ"
        "sfS+VEiow+4wYH5Tte3drLnDLWAIOz+YZx+OrXWI9kCqLez3ZnAxIMWMZmn21o/meL0py6as1Ki4OITH8Nqrqw+Lpmqb4yzn"
        "LVz7vTXbo25bL26XmrdczUQuZ0iBOFab08XmYMEd/jhgHJNm8xVlyWvgmfwYtoGhZgxP0cNoPhM2lZfWwnfsdNFzzl/y5QZi"
        "hAEPP/l+RU5+kHkOwDOgQjhGpbZAu1L2NNdCFpmUJn3/pR829BwXP/CzH/hf+kHlgov/frj4gU/FW/1APv0G"
    )

    decoded = decode_response(payload)
    assert isinstance(decoded, list)
    rows = decoded
    assert len(rows) == 2
    assert any("PORCU" in str(row.get("Denominazione", "")).upper() for row in rows)


def test_capacitas_session_extracts_token_from_html_and_auth_cookie() -> None:
    from app.modules.elaborazioni.capacitas.session import CapacitasSessionManager

    manager = CapacitasSessionManager("user", "secret")

    html_token = manager._extract_token_from_html(
        '<html><body><script>window.appConfig = {"token":"123e4567-e89b-12d3-a456-426614174000"}</script></body></html>'
    )
    assert html_token == "123e4567-e89b-12d3-a456-426614174000"

    import httpx

    manager._http = httpx.AsyncClient()
    manager._http.cookies.set("involture__AUTH_COOKIE", "123e4567-e89b-12d3-a456-426614174000|tenant|rest")
    cookie_token = manager._extract_token_from_cookies()
    assert cookie_token == "123e4567-e89b-12d3-a456-426614174000"


def test_capacitas_terreni_parsers_extract_rows_certificato_and_detail() -> None:
    from app.modules.elaborazioni.capacitas.apps.involture.parsers import (
        parse_certificato_html,
        parse_terreni_search_result,
        parse_terreno_detail_html,
    )

    terreni_payload = (
        "[ {ID: '74354d04-d124-4d9e-a3b4-9ca24400ea9f', PVC: '097', COM: '289', CCO: '0A1103877', FRA: '38', "
        "CCS: '00000', Ta_ext: ' 9', Sez: '', Foglio: '   1', Partic: '  680', Sub: '', Superficie: '5500', "
        "BacDescr: 'Da assegnare', Anno: '2026', Voltura: '13', Opcode: '050', DataReg: '02/03/2026', Belfiore: 'L496'} ]"
    )
    certificato_html = """
    <pre id="Capacitas_ContentMain_ContentCertificatoPre">
      <div>PARTITA: <span>0A1103877/38/00000</span> - URAS - STATO: Iscrivibile a ruolo</div>
      <div> UTENZA: D001254734 - STATO CNC: non iscritta a ruolo</div>
      <div class='rpt-riga rpt-riga-ana'>DI: <span>Lasi Daniela</span> C.F. LSADNL68S48L496D</div>
      <div class='rpt-riga rpt-riga-terreno' data-id='74354D04-D124-4D9E-A3B4-9CA24400EA9F'>   34    1   680            5.500 0 </div>
      <div class='rpt-riga rpt-riga-terreno' data-id='74354D04-D124-4D9E-A3B4-9CA24400EA9F'><strong>Riordino: </strong>R.F. 23/8099 <strong> Maglia: </strong>178 <strong> Lotto: </strong>1</div>
    </pre>
    """
    detail_html = """
    <input id="Capacitas_ContentMain_txtFoglioDt" value="1" />
    <input id="Capacitas_ContentMain_txtParticDt" value="680" />
    <script>
      loadDataGridV2(jQuery("#grdRis"), "[ {ID: '1', Parametro: 'RIORDINO_F', VStr: 'R.F. 23/8099'}, {ID: '2', Parametro: 'MAGLIA_RF', VStr: '178'}, {ID: '3', Parametro: 'LOTTO_RF', VStr: '1'}, {ID: '4', Parametro: 'IRRIDIST', VStr: '34'} ]", false);
    </script>
    """

    result = parse_terreni_search_result(terreni_payload)
    certificato = parse_certificato_html(certificato_html)
    detail = parse_terreno_detail_html(detail_html)

    assert result.total == 1
    assert result.rows[0].foglio == "1"
    assert result.rows[0].particella == "680"
    assert result.rows[0].row_visual_state == "current_black"
    assert certificato.partita_code == "0A1103877/38/00000"
    assert certificato.utenza_code == "D001254734"
    assert certificato.terreni[0].riordino_code == "R.F. 23/8099"
    assert detail.foglio == "1"
    assert detail.particella == "680"
    assert detail.riordino_maglia == "178"
    assert detail.irridist == "34"


def test_capacitas_credentials_crud_encrypts_password() -> None:
    create_response = client.post(
        "/elaborazioni/capacitas/credentials",
        headers=auth_headers(),
        json={
            "label": "Account principale",
            "username": "capacitas-user",
            "password": "capacitas-secret",
            "active": True,
            "allowed_hours_start": 0,
            "allowed_hours_end": 23,
        },
    )

    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["label"] == "Account principale"
    assert "password" not in payload

    list_response = client.get("/elaborazioni/capacitas/credentials", headers=auth_headers())
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    db = TestingSessionLocal()
    try:
        credential = db.query(CapacitasCredential).one()
        assert credential.username == "capacitas-user"
        assert credential.password_encrypted != "capacitas-secret"
    finally:
        db.close()

    update_response = client.patch(
        f"/elaborazioni/capacitas/credentials/{payload['id']}",
        headers=auth_headers(),
        json={"active": False},
    )
    assert update_response.status_code == 200
    assert update_response.json()["active"] is False

    delete_response = client.delete(
        f"/elaborazioni/capacitas/credentials/{payload['id']}",
        headers=auth_headers(),
    )
    assert delete_response.status_code == 204


def test_capacitas_involture_search_uses_selected_credential_and_returns_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/elaborazioni/capacitas/credentials",
        headers=auth_headers(),
        json={
            "label": "Ricerca CF",
            "username": "capacitas-user",
            "password": "capacitas-secret",
        },
    )
    credential_id = create_response.json()["id"]

    async def fake_login(self):
        from app.modules.elaborazioni.capacitas.session import CapacitasSession

        self._session = CapacitasSession(token="123e4567-e89b-12d3-a456-426614174000")
        return self._session

    async def fake_activate_app(self, app_name: str) -> None:
        return None

    async def fake_close(self) -> None:
        return None

    async def fake_search_anagrafica(self, q: str, tipo: int = 1, solo_con_beni: bool = False) -> CapacitasSearchResult:
        assert q == "PRCLSN82R27B354B"
        assert tipo == 2
        assert solo_con_beni is False
        return CapacitasSearchResult(
            total=2,
            rows=[
                {
                    "CCO": "0A0862690",
                    "Denominazione": "Porcu Alessandro",
                    "CodiceFiscale": "PRCLSN82R27B354B",
                    "Comune": "ORISTANO",
                },
                {
                    "CCO": "0A0875323",
                    "Denominazione": "Porcu Alessandro",
                    "CodiceFiscale": "PRCLSN82R27B354B",
                    "Comune": "ORISTANO",
                },
            ],
        )

    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_anagrafica", fake_search_anagrafica)

    search_response = client.post(
        "/elaborazioni/capacitas/involture/search",
        headers=auth_headers(),
        json={
            "q": "PRCLSN82R27B354B",
            "tipo_ricerca": 2,
            "credential_id": credential_id,
        },
    )

    assert search_response.status_code == 200
    payload = search_response.json()
    assert payload["total"] == 2
    assert len(payload["rows"]) == 2
    assert payload["rows"][0]["Denominazione"] == "Porcu Alessandro"

    db = TestingSessionLocal()
    try:
        credential = db.get(CapacitasCredential, credential_id)
        assert credential is not None
        assert credential.last_error is None
        assert credential.last_used_at is not None
        assert credential.last_used_at.tzinfo is not None or credential.last_used_at == credential.last_used_at.replace(tzinfo=None)
    finally:
        db.close()


def test_capacitas_terreni_search_endpoint_returns_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    create_response = client.post(
        "/elaborazioni/capacitas/credentials",
        headers=auth_headers(),
        json={"label": "Terreni", "username": "capacitas-user", "password": "capacitas-secret"},
    )
    credential_id = create_response.json()["id"]

    async def fake_login(self):
        from app.modules.elaborazioni.capacitas.session import CapacitasSession

        self._session = CapacitasSession(token="123e4567-e89b-12d3-a456-426614174000")
        return self._session

    async def fake_activate_app(self, app_name: str) -> None:
        return None

    async def fake_close(self) -> None:
        return None

    async def fake_search_terreni(self, request) -> CapacitasTerreniSearchResult:
        assert request.frazione_id == "38"
        assert request.foglio == "1"
        assert request.particella == "680"
        return CapacitasTerreniSearchResult(
            total=1,
            rows=[
                {
                    "ID": "74354d04-d124-4d9e-a3b4-9ca24400ea9f",
                    "PVC": "097",
                    "COM": "289",
                    "CCO": "0A1103877",
                    "FRA": "38",
                    "CCS": "00000",
                    "Foglio": "1",
                    "Partic": "680",
                    "Anno": "2026",
                    "Belfiore": "L496",
                    "Ta_ext": " 9",
                }
            ],
        )

    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_terreni", fake_search_terreni)

    response = client.post(
        "/elaborazioni/capacitas/involture/terreni/search",
        headers=auth_headers(),
        json={"frazione_id": "38", "foglio": "1", "particella": "680", "credential_id": credential_id},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["rows"][0]["CCO"] == "0A1103877"


def test_capacitas_terreni_lookup_endpoints_return_options(monkeypatch: pytest.MonkeyPatch) -> None:
    create_response = client.post(
        "/elaborazioni/capacitas/credentials",
        headers=auth_headers(),
        json={"label": "Terreni Lookup", "username": "capacitas-user", "password": "capacitas-secret"},
    )
    credential_id = create_response.json()["id"]

    async def fake_login(self):
        from app.modules.elaborazioni.capacitas.session import CapacitasSession

        self._session = CapacitasSession(token="123e4567-e89b-12d3-a456-426614174000")
        return self._session

    async def fake_activate_app(self, app_name: str) -> None:
        return None

    async def fake_close(self) -> None:
        return None

    async def fake_search_frazioni(self, query: str) -> list[CapacitasLookupOption]:
        assert query == "uras"
        return [CapacitasLookupOption(id="38", display="URAS")]

    async def fake_load_sezioni(self, frazione_id: str) -> list[CapacitasLookupOption]:
        assert frazione_id == "38"
        return [CapacitasLookupOption(id="A", display="A")]

    async def fake_load_fogli(self, frazione_id: str, sezione: str = "") -> list[CapacitasLookupOption]:
        assert frazione_id == "38"
        assert sezione == "A"
        return [CapacitasLookupOption(id="1", display="1")]

    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_frazioni", fake_search_frazioni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.load_sezioni", fake_load_sezioni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.load_fogli", fake_load_fogli)

    frazioni_response = client.get(
        f"/elaborazioni/capacitas/involture/frazioni?q=uras&credential_id={credential_id}",
        headers=auth_headers(),
    )
    sezioni_response = client.get(
        f"/elaborazioni/capacitas/involture/sezioni?frazione_id=38&credential_id={credential_id}",
        headers=auth_headers(),
    )
    fogli_response = client.get(
        f"/elaborazioni/capacitas/involture/fogli?frazione_id=38&sezione=A&credential_id={credential_id}",
        headers=auth_headers(),
    )

    assert frazioni_response.status_code == 200
    assert frazioni_response.json()[0]["display"] == "URAS"
    assert sezioni_response.status_code == 200
    assert sezioni_response.json()[0]["id"] == "A"
    assert fogli_response.status_code == 200
    assert fogli_response.json()[0]["id"] == "1"


def test_capacitas_terreni_sync_persists_consorzio_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    create_response = client.post(
        "/elaborazioni/capacitas/credentials",
        headers=auth_headers(),
        json={"label": "Terreni Sync", "username": "capacitas-user", "password": "capacitas-secret"},
    )
    credential_id = create_response.json()["id"]

    async def fake_login(self):
        from app.modules.elaborazioni.capacitas.session import CapacitasSession

        self._session = CapacitasSession(token="123e4567-e89b-12d3-a456-426614174000")
        return self._session

    async def fake_activate_app(self, app_name: str) -> None:
        return None

    async def fake_close(self) -> None:
        return None

    async def fake_search_terreni(self, request) -> CapacitasTerreniSearchResult:
        return CapacitasTerreniSearchResult(
            total=1,
            rows=[
                {
                    "ID": "74354d04-d124-4d9e-a3b4-9ca24400ea9f",
                    "PVC": "097",
                    "COM": "289",
                    "CCO": "0A1103877",
                    "FRA": "38",
                    "CCS": "00000",
                    "Foglio": "1",
                    "Partic": "680",
                    "Sub": "",
                    "Anno": "2026",
                    "Voltura": "13",
                    "Opcode": "050",
                    "DataReg": "02/03/2026",
                    "Superficie": "5500",
                    "BacDescr": "Da assegnare",
                    "Belfiore": "L496",
                    "Ta_ext": " 9",
                }
            ],
        )

    async def fake_fetch_certificato(self, **kwargs) -> CapacitasTerrenoCertificato:
        return CapacitasTerrenoCertificato(
            cco="0A1103877",
            fra="38",
            ccs="00000",
            pvc="097",
            com="289",
            partita_code="0A1103877/38/00000",
            utenza_code="D001254734",
            utenza_status="non iscritta a ruolo",
            ruolo_status="Iscrivibile a ruolo",
            raw_html="<html>certificato</html>",
        )

    async def fake_fetch_detail(self, **kwargs) -> CapacitasTerrenoDetail:
        return CapacitasTerrenoDetail(
            external_row_id="74354d04-d124-4d9e-a3b4-9ca24400ea9f",
            foglio="1",
            particella="680",
            riordino_code="R.F. 23/8099",
            riordino_maglia="178",
            riordino_lotto="1",
            irridist="34",
            parameters={"RIORDINO_F": "R.F. 23/8099", "MAGLIA_RF": "178", "LOTTO_RF": "1", "IRRIDIST": "34"},
            raw_html="<html>dettaglio</html>",
        )

    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_terreni", fake_search_terreni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.fetch_certificato", fake_fetch_certificato)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.fetch_terreno_detail", fake_fetch_detail)

    response = client.post(
        "/elaborazioni/capacitas/involture/terreni/sync",
        headers=auth_headers(),
        json={
            "frazione_id": "38",
            "foglio": "1",
            "particella": "680",
            "credential_id": credential_id,
            "fetch_certificati": True,
            "fetch_details": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_rows"] == 1
    assert payload["imported_rows"] == 1
    assert payload["imported_certificati"] == 1
    assert payload["imported_details"] == 1
    assert payload["linked_units"] == 1
    assert payload["linked_occupancies"] == 1

    db = TestingSessionLocal()
    try:
        assert db.query(CatConsorzioUnit).count() == 1
        assert db.query(CatConsorzioOccupancy).count() == 1
        assert db.query(CatCapacitasTerrenoRow).count() == 1
        assert db.query(CatCapacitasCertificato).count() == 1
        assert db.query(CatCapacitasTerrenoDetail).count() == 1
    finally:
        db.close()


def test_capacitas_terreni_sync_avoids_duplicate_certificati_for_same_cco(monkeypatch: pytest.MonkeyPatch) -> None:
    create_response = client.post(
        "/elaborazioni/capacitas/credentials",
        headers=auth_headers(),
        json={"label": "Terreni Dup", "username": "capacitas-user", "password": "capacitas-secret"},
    )
    credential_id = create_response.json()["id"]

    async def fake_login(self):
        from app.modules.elaborazioni.capacitas.session import CapacitasSession

        self._session = CapacitasSession(token="123e4567-e89b-12d3-a456-426614174000")
        return self._session

    async def fake_activate_app(self, app_name: str) -> None:
        return None

    async def fake_close(self) -> None:
        return None

    async def fake_search_terreni(self, request) -> CapacitasTerreniSearchResult:
        return CapacitasTerreniSearchResult(
            total=2,
            rows=[
                {
                    "ID": "row-1",
                    "PVC": "097",
                    "COM": "289",
                    "CCO": "0A1103877",
                    "FRA": "38",
                    "CCS": "00000",
                    "Foglio": "1",
                    "Partic": "680",
                    "Anno": "2026",
                    "Belfiore": "L496",
                    "Ta_ext": " 9",
                },
                {
                    "ID": "row-2",
                    "PVC": "097",
                    "COM": "289",
                    "CCO": "0A1103877",
                    "FRA": "38",
                    "CCS": "00000",
                    "Foglio": "1",
                    "Partic": "680",
                    "Anno": "2026",
                    "Belfiore": "L496",
                    "Ta_ext": "#9",
                },
            ],
        )

    async def fake_fetch_certificato(self, **kwargs) -> CapacitasTerrenoCertificato:
        return CapacitasTerrenoCertificato(
            cco="0A1103877",
            fra="38",
            ccs="00000",
            pvc="097",
            com="289",
            partita_code="0A1103877/38/00000",
            raw_html="<html>certificato</html>",
        )

    async def fake_fetch_detail(self, **kwargs) -> CapacitasTerrenoDetail:
        return CapacitasTerrenoDetail(
            external_row_id=kwargs["external_row_id"],
            foglio="1",
            particella="680",
            raw_html="<html>dettaglio</html>",
        )

    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_terreni", fake_search_terreni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.fetch_certificato", fake_fetch_certificato)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.fetch_terreno_detail", fake_fetch_detail)

    response = client.post(
        "/elaborazioni/capacitas/involture/terreni/sync",
        headers=auth_headers(),
        json={
            "frazione_id": "38",
            "foglio": "1",
            "particella": "680",
            "credential_id": credential_id,
            "fetch_certificati": True,
            "fetch_details": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["imported_certificati"] == 1

    db = TestingSessionLocal()
    try:
        assert db.query(CatCapacitasCertificato).count() == 1
        assert db.query(CatCapacitasTerrenoRow).count() == 2
    finally:
        db.close()


def test_capacitas_terreni_sync_batch_returns_item_results(monkeypatch: pytest.MonkeyPatch) -> None:
    create_response = client.post(
        "/elaborazioni/capacitas/credentials",
        headers=auth_headers(),
        json={"label": "Terreni Batch", "username": "capacitas-user", "password": "capacitas-secret"},
    )
    credential_id = create_response.json()["id"]

    async def fake_login(self):
        from app.modules.elaborazioni.capacitas.session import CapacitasSession

        self._session = CapacitasSession(token="123e4567-e89b-12d3-a456-426614174000")
        return self._session

    async def fake_activate_app(self, app_name: str) -> None:
        return None

    async def fake_close(self) -> None:
        return None

    async def fake_search_terreni(self, request) -> CapacitasTerreniSearchResult:
        if request.particella == "680":
            return CapacitasTerreniSearchResult(
                total=1,
                rows=[
                    {
                        "ID": "batch-row-1",
                        "PVC": "097",
                        "COM": "289",
                        "CCO": "0A1103877",
                        "FRA": "38",
                        "CCS": "00000",
                        "Foglio": "1",
                        "Partic": "680",
                        "Anno": "2026",
                        "Belfiore": "L496",
                        "Ta_ext": " 9",
                    }
                ],
            )
        raise RuntimeError("Particella non trovata")

    async def fake_fetch_certificato(self, **kwargs) -> CapacitasTerrenoCertificato:
        return CapacitasTerrenoCertificato(
            cco="0A1103877",
            fra="38",
            ccs="00000",
            pvc="097",
            com="289",
            partita_code="0A1103877/38/00000",
            raw_html="<html>certificato</html>",
        )

    async def fake_fetch_detail(self, **kwargs) -> CapacitasTerrenoDetail:
        return CapacitasTerrenoDetail(
            external_row_id="batch-row-1",
            foglio="1",
            particella="680",
            raw_html="<html>dettaglio</html>",
        )

    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_terreni", fake_search_terreni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.fetch_certificato", fake_fetch_certificato)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.fetch_terreno_detail", fake_fetch_detail)

    response = client.post(
        "/elaborazioni/capacitas/involture/terreni/sync-batch",
        headers=auth_headers(),
        json={
            "credential_id": credential_id,
            "continue_on_error": True,
            "items": [
                {"label": "corrente", "frazione_id": "38", "foglio": "1", "particella": "680"},
                {"label": "missing", "frazione_id": "38", "foglio": "1", "particella": "9999"},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["processed_items"] == 2
    assert payload["failed_items"] == 1
    assert payload["imported_rows"] == 1
    assert payload["items"][0]["ok"] is True
    assert payload["items"][1]["ok"] is False


def test_capacitas_terreni_sync_batch_resolves_comune_and_applies_global_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/elaborazioni/capacitas/credentials",
        headers=auth_headers(),
        json={"label": "Terreni Batch Comune", "username": "capacitas-user", "password": "capacitas-secret"},
    )
    credential_id = create_response.json()["id"]

    async def fake_login(self):
        from app.modules.elaborazioni.capacitas.session import CapacitasSession

        self._session = CapacitasSession(token="123e4567-e89b-12d3-a456-426614174000")
        return self._session

    async def fake_activate_app(self, app_name: str) -> None:
        return None

    async def fake_close(self) -> None:
        return None

    async def fake_search_frazioni(self, query: str) -> list[CapacitasLookupOption]:
        assert query == "Uras"
        return [CapacitasLookupOption(id="38", display="URAS")]

    async def fake_search_terreni(self, request) -> CapacitasTerreniSearchResult:
        assert request.frazione_id == "38"
        return CapacitasTerreniSearchResult(
            total=1,
            rows=[
                {
                    "ID": "batch-row-umanizzato-1",
                    "PVC": "097",
                    "COM": "289",
                    "CCO": "0A1103877",
                    "FRA": "38",
                    "CCS": "00000",
                    "Foglio": "1",
                    "Partic": "680",
                    "Anno": "2026",
                    "Belfiore": "L496",
                    "Ta_ext": " 9",
                }
            ],
        )

    async def fail_fetch_certificato(self, **kwargs):
        raise AssertionError("fetch_certificato non deve essere invocato quando fetch_certificati=false")

    async def fail_fetch_detail(self, **kwargs):
        raise AssertionError("fetch_terreno_detail non deve essere invocato quando fetch_details=false")

    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_frazioni", fake_search_frazioni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_terreni", fake_search_terreni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.fetch_certificato", fail_fetch_certificato)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.fetch_terreno_detail", fail_fetch_detail)

    response = client.post(
        "/elaborazioni/capacitas/involture/terreni/sync-batch",
        headers=auth_headers(),
        json={
            "credential_id": credential_id,
            "continue_on_error": True,
            "fetch_certificati": False,
            "fetch_details": False,
            "items": [{"comune": "Uras", "foglio": "1", "particella": "680"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["processed_items"] == 1
    assert payload["failed_items"] == 0
    assert payload["imported_rows"] == 1
    assert payload["imported_certificati"] == 0
    assert payload["imported_details"] == 0
    assert payload["items"][0]["ok"] is True


def test_capacitas_terreni_sync_resolves_arborea_terralba_swap_to_real_comune(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/elaborazioni/capacitas/credentials",
        headers=auth_headers(),
        json={"label": "Terreni Swap", "username": "capacitas-user", "password": "capacitas-secret"},
    )
    credential_id = create_response.json()["id"]

    async def fake_login(self):
        from app.modules.elaborazioni.capacitas.session import CapacitasSession

        self._session = CapacitasSession(token="123e4567-e89b-12d3-a456-426614174000")
        return self._session

    async def fake_activate_app(self, app_name: str) -> None:
        return None

    async def fake_close(self) -> None:
        return None

    async def fake_search_terreni(self, request) -> CapacitasTerreniSearchResult:
        return CapacitasTerreniSearchResult(
            total=1,
            rows=[
                {
                    "ID": "swap-row-1",
                    "PVC": "097",
                    "COM": "165",
                    "CCO": "0A9999999",
                    "FRA": "1",
                    "CCS": "00000",
                    "Foglio": "14",
                    "Partic": "330",
                    "Anno": "2026",
                    "Belfiore": "A357",
                    "Ta_ext": " 9",
                }
            ],
        )

    async def fake_fetch_certificato(self, **kwargs) -> CapacitasTerrenoCertificato:
        return CapacitasTerrenoCertificato(
            cco="0A9999999",
            fra="1",
            ccs="00000",
            pvc="097",
            com="165",
            partita_code="0A9999999/1/00000",
            raw_html="<html>certificato</html>",
        )

    async def fake_fetch_detail(self, **kwargs) -> CapacitasTerrenoDetail:
        return CapacitasTerrenoDetail(
            external_row_id="swap-row-1",
            foglio="14",
            particella="330",
            raw_html="<html>dettaglio</html>",
        )

    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_terreni", fake_search_terreni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.fetch_certificato", fake_fetch_certificato)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.fetch_terreno_detail", fake_fetch_detail)

    response = client.post(
        "/elaborazioni/capacitas/involture/terreni/sync",
        headers=auth_headers(),
        json={
            "frazione_id": "1",
            "foglio": "14",
            "particella": "330",
            "credential_id": credential_id,
            "fetch_certificati": True,
            "fetch_details": True,
        },
    )

    assert response.status_code == 200

    db = TestingSessionLocal()
    try:
        unit = db.query(CatConsorzioUnit).filter(CatConsorzioUnit.foglio == "14", CatConsorzioUnit.particella == "330").one()
        assert unit.cod_comune_capacitas == 280
        assert unit.source_cod_comune_capacitas == 165
        assert unit.source_codice_catastale == "A357"
        assert unit.source_comune_label == "Arborea"
        assert unit.comune_resolution_mode == "swapped_arborea_terralba"
    finally:
        db.close()


def test_capacitas_terreni_job_lifecycle_persists_and_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.elaborazioni.capacitas_routes.SessionLocal", TestingSessionLocal)

    create_response = client.post(
        "/elaborazioni/capacitas/credentials",
        headers=auth_headers(),
        json={"label": "Terreni Job", "username": "capacitas-user", "password": "capacitas-secret"},
    )
    credential_id = create_response.json()["id"]

    async def fake_login(self):
        from app.modules.elaborazioni.capacitas.session import CapacitasSession

        self._session = CapacitasSession(token="123e4567-e89b-12d3-a456-426614174000")
        return self._session

    async def fake_activate_app(self, app_name: str) -> None:
        return None

    async def fake_close(self) -> None:
        return None

    async def fake_search_terreni(self, request) -> CapacitasTerreniSearchResult:
        return CapacitasTerreniSearchResult(
            total=1,
            rows=[
                {
                    "ID": "job-row-1",
                    "PVC": "097",
                    "COM": "289",
                    "CCO": "0A1103877",
                    "FRA": "38",
                    "CCS": "00000",
                    "Foglio": "1",
                    "Partic": "680",
                    "Anno": "2026",
                    "Belfiore": "L496",
                    "Ta_ext": " 9",
                }
            ],
        )

    async def fake_fetch_certificato(self, **kwargs) -> CapacitasTerrenoCertificato:
        return CapacitasTerrenoCertificato(
            cco="0A1103877",
            fra="38",
            ccs="00000",
            pvc="097",
            com="289",
            partita_code="0A1103877/38/00000",
            raw_html="<html>certificato</html>",
        )

    async def fake_fetch_detail(self, **kwargs) -> CapacitasTerrenoDetail:
        return CapacitasTerrenoDetail(
            external_row_id="job-row-1",
            foglio="1",
            particella="680",
            raw_html="<html>dettaglio</html>",
        )

    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_terreni", fake_search_terreni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.fetch_certificato", fake_fetch_certificato)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.fetch_terreno_detail", fake_fetch_detail)

    create_job_response = client.post(
        "/elaborazioni/capacitas/involture/terreni/jobs",
        headers=auth_headers(),
        json={
            "credential_id": credential_id,
            "items": [{"label": "job-1", "frazione_id": "38", "foglio": "1", "particella": "680"}],
        },
    )
    assert create_job_response.status_code == 202
    job_id = create_job_response.json()["id"]
    assert create_job_response.json()["status"] in {"pending", "succeeded", "completed_with_errors"}

    list_jobs_response = client.get("/elaborazioni/capacitas/involture/terreni/jobs", headers=auth_headers())
    get_job_response = client.get(f"/elaborazioni/capacitas/involture/terreni/jobs/{job_id}", headers=auth_headers())

    assert list_jobs_response.status_code == 200
    assert any(item["id"] == job_id for item in list_jobs_response.json())
    assert get_job_response.status_code == 200
    assert get_job_response.json()["status"] == "succeeded"
    assert get_job_response.json()["result_json"]["processed_items"] == 1

    rerun_job_response = client.post(
        f"/elaborazioni/capacitas/involture/terreni/jobs/{job_id}/run",
        headers=auth_headers(),
    )
    assert rerun_job_response.status_code == 200
    assert rerun_job_response.json()["status"] == "succeeded"

    db = TestingSessionLocal()
    try:
        job = db.get(CapacitasTerreniSyncJob, job_id)
        assert job is not None
        assert job.status == "succeeded"
        assert job.result_json is not None
    finally:
        db.close()


def test_capacitas_credential_test_returns_diagnostic_detail_on_login_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/elaborazioni/capacitas/credentials",
        headers=auth_headers(),
        json={
            "label": "Probe errore",
            "username": "capacitas-user",
            "password": "capacitas-secret",
        },
    )
    credential_id = create_response.json()["id"]

    async def fake_login(self):
        raise RuntimeError(
            "Capacitas login fallito: token non trovato dopo il POST credenziali. "
            "URL finale=https://sso.servizicapacitas.com/pages/login.aspx | "
            "title=Login | cookies=ASP.NET_SessionId | segnali=login_form,error_message | "
            "snippet=Credenziali non valide",
        )

    async def fake_close(self) -> None:
        return None

    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)

    response = client.post(
        f"/elaborazioni/capacitas/credentials/{credential_id}/test",
        headers=auth_headers(),
    )

    assert response.status_code == 502
    payload = response.json()
    assert "token non trovato" in payload["detail"]
    assert "URL finale=" in payload["detail"]
    assert "cookies=" in payload["detail"]
