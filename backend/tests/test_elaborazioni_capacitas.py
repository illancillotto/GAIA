from __future__ import annotations

from collections.abc import Generator
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid

from cryptography.fernet import Fernet
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.capacitas import CapacitasCredential
from app.models.capacitas import (
    CapacitasAnagraficaHistoryImportJob,
    CapacitasParticelleSyncJob,
    CapacitasTerreniSyncJob,
)
from app.models.catasto_phase1 import (
    CatCapacitasCertificato,
    CatCapacitasIntestatario,
    CatCapacitasTerrenoDetail,
    CatCapacitasTerrenoRow,
    CatComune,
    CatUtenzaIntestatario,
    CatConsorzioOccupancy,
    CatConsorzioUnit,
    CatImportBatch,
    CatParticella,
    CatSchemaContributo,
    CatUtenzaIrrigua,
)
from app.modules.utenze.models import AnagraficaPerson, AnagraficaPersonSnapshot, AnagraficaSubject
from app.modules.elaborazioni.capacitas.models import (
    CapacitasAnagrafica,
    CapacitasAnagraficaDetail,
    CapacitasLookupOption,
    CapacitasStoricoAnagraficaRow,
    CapacitasSearchResult,
    CapacitasTerreniSearchResult,
    CapacitasTerrenoCertificato,
    CapacitasTerrenoDetail,
)
from app.services.catasto_credentials import get_credential_fernet
from app.services.elaborazioni_capacitas_anagrafica_history import prepare_anagrafica_history_jobs_for_recovery
from app.services.elaborazioni_capacitas_particelle_sync import prepare_particelle_sync_jobs_for_recovery
from app.services.elaborazioni_capacitas_terreni import prepare_terreni_sync_jobs_for_recovery


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
            cod_frazione=38,
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


def test_particelle_sync_policy_uses_900ms_daytime_default() -> None:
    from app.services.elaborazioni_capacitas_particelle_sync import compute_sync_policy

    policy = compute_sync_policy(datetime(2026, 4, 27, 10, 0, tzinfo=timezone.utc))

    assert policy.aggressive_window is False
    assert policy.throttle_ms == 900
    assert policy.speed_multiplier == 1
    assert policy.parallel_workers == 1


def test_particelle_sync_policy_double_speed_halves_throttle() -> None:
    from app.services.elaborazioni_capacitas_particelle_sync import compute_sync_policy

    daytime_policy = compute_sync_policy(datetime(2026, 4, 27, 10, 0, tzinfo=timezone.utc), double_speed=True)
    evening_policy = compute_sync_policy(datetime(2026, 4, 27, 18, 0, tzinfo=timezone.utc), double_speed=True)

    assert daytime_policy.throttle_ms == 450
    assert daytime_policy.speed_multiplier == 2
    assert evening_policy.aggressive_window is True
    assert evening_policy.throttle_ms == 175


def test_particelle_sync_policy_caps_parallel_workers() -> None:
    from app.services.elaborazioni_capacitas_particelle_sync import compute_sync_policy

    policy = compute_sync_policy(datetime(2026, 4, 27, 10, 0, tzinfo=timezone.utc), parallel_workers=5)

    assert policy.parallel_workers == 2


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


def test_capacitas_session_builds_login_form_data_from_real_markup() -> None:
    from app.modules.elaborazioni.capacitas.session import CapacitasSessionManager

    html_text = """
    <form method="post" action="./login.aspx" id="form1" onsubmit="MakeSafe();">
      <input type="hidden" name="__LASTFOCUS" id="__LASTFOCUS" value="" />
      <input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value="vs123" />
      <input type="hidden" name="__VIEWSTATEGENERATOR" id="__VIEWSTATEGENERATOR" value="gen123" />
      <input type="hidden" name="__EVENTTARGET" id="__EVENTTARGET" value="" />
      <input type="hidden" name="__EVENTARGUMENT" id="__EVENTARGUMENT" value="" />
      <input type="hidden" name="__EVENTVALIDATION" id="__EVENTVALIDATION" value="ev123" />
      <input name="ctl00$ContentMain$txtUsername" type="text" id="ContentMain_txtUsername" />
      <input name="ctl00$ContentMain$txtPassword" type="password" id="ContentMain_txtPassword" />
      <input type="submit" name="ctl00$ContentMain$btnAccedi" value="Accedi" id="ContentMain_btnAccedi" />
      <input name="ctl00$ContentMain$txtGAUerInput" type="text" id="ContentMain_txtGAUerInput" />
    </form>
    """

    form_data = CapacitasSessionManager._build_login_form_data(html_text, "PORCUAL", "#Cagliari1!")
    assert form_data["__VIEWSTATE"] == "vs123"
    assert form_data["__EVENTVALIDATION"] == "ev123"
    assert form_data["ctl00$ContentMain$txtUsername"] == "PORCUAL"
    assert form_data["ctl00$ContentMain$txtPassword"] == "#Cagliari1!"
    assert form_data["ctl00$ContentMain$btnAccedi"] == "Accedi"
    assert form_data["ctl00$ContentMain$txtGAUerInput"] == ""


@pytest.mark.anyio
async def test_capacitas_activate_app_uses_sso_tile_launch_and_handles_duplicate_cookie_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import httpx

    from app.modules.elaborazioni.capacitas.session import CapacitasSession, CapacitasSessionManager

    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/pages/ajax/ajaxTiles.aspx":
            return httpx.Response(200, text="ignored")
        return httpx.Response(
            200,
            headers=[
                ("set-cookie", "ASP.NET_SessionId=abc; Domain=sso.servizicapacitas.com; Path=/"),
                ("set-cookie", "ASP.NET_SessionId=def; Domain=involture1.servizicapacitas.com; Path=/"),
                ("set-cookie", "involture__AUTH_COOKIE=123e4567-e89b-12d3-a456-426614174000|tenant; Domain=sso.servizicapacitas.com; Path=/"),
            ],
            text="ok",
        )

    transport = httpx.MockTransport(handler)
    manager = CapacitasSessionManager("PORCUAL", "secret")
    manager._http = httpx.AsyncClient(transport=transport)
    manager._session = CapacitasSession(token="123e4567-e89b-12d3-a456-426614174000")
    monkeypatch.setattr(
        "app.modules.elaborazioni.capacitas.session.decode_response",
        lambda payload: [
            {
                "tile": (
                    "%3cspan+class%3d%27tile%27+data-idrun%3d%27run-123%27+data-codcons%3d%27090%27+"
                    "data-url%3d%27https%253a%252f%252finvolture1.servizicapacitas.com%252fpages%252flogin.aspx%27+"
                    "data-descriz%3d%27inVOLTURE%27+data-app%3d%27involture%27%3e%3c%2fspan%3e"
                )
            }
        ],
    )

    await manager.activate_app("involture")

    cookies = manager._session.app_cookies["involture"]
    assert len(cookies) >= 1
    assert any(cookie["name"] == "ASP.NET_SessionId" for cookie in cookies)
    assert len(requests) == 2
    assert requests[0].url.path == "/pages/ajax/ajaxTiles.aspx"
    assert requests[1].url.path == "/pages/login.aspx"
    assert requests[1].url.params["codConsApp"] == "090"
    assert requests[1].url.params["idRun"] == "run-123"
    assert requests[1].url.params["token"] == "123e4567-e89b-12d3-a456-426614174000"

    await manager.close()


@pytest.mark.anyio
async def test_involture_lookup_decodes_sz_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    from app.modules.elaborazioni.capacitas.apps.involture.client import InVoltureClient
    from app.modules.elaborazioni.capacitas.session import CapacitasSessionManager

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="SZignored")

    transport = httpx.MockTransport(handler)
    manager = CapacitasSessionManager("PORCUAL", "secret")
    manager._http = httpx.AsyncClient(transport=transport)
    manager._session = type("SessionStub", (), {"token": "123e4567-e89b-12d3-a456-426614174000"})()
    monkeypatch.setattr(
        "app.modules.elaborazioni.capacitas.apps.involture.client.decode_response",
        lambda payload: [{"ID": "38", "Display": "URAS"}],
    )

    client_api = InVoltureClient(manager)
    rows = await client_api.search_frazioni("uras")

    assert len(rows) == 1
    assert rows[0].id == "38"
    assert rows[0].display == "URAS"

    await manager.close()


@pytest.mark.anyio
async def test_involture_fetch_anagrafica_history_returns_empty_on_missing_history(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    from app.modules.elaborazioni.capacitas.apps.involture.client import InVoltureClient
    from app.modules.elaborazioni.capacitas.session import CapacitasSessionManager

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="NOnessuno storico presente")

    transport = httpx.MockTransport(handler)
    manager = CapacitasSessionManager("PORCUAL", "secret")
    manager._http = httpx.AsyncClient(transport=transport)
    manager._session = type("SessionStub", (), {"token": "123e4567-e89b-12d3-a456-426614174000"})()

    client_api = InVoltureClient(manager)
    rows = await client_api.fetch_anagrafica_history(idxana="IDX-TEST")

    assert rows == []

    await manager.close()


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
      <div class='rpt-riga rpt-riga-ana' data-idxesa='D5DAB932-5D57-4088-A55B-C60EAE215F59' data-idxana='BD23974F-E9A2-4DFA-8B2C-9B18B1699EB8'>DI: <span>Lasi Daniela</span> C.F. LSADNL68S48L496D <span class='evento-'></span></div>
      <div class='rpt-riga'>    nata il 08/11/1968 in &lt;L496&gt; URAS</div>
      <div class='rpt-riga'>    RES: 09098 &lt;L122&gt; TERRALBA (OR) - VIA Manca 151</div>
      <div class='rpt-riga'>    TITOLI: Proprieta` 1/1</div>
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
    assert certificato.intestatari[0].idxana == "BD23974F-E9A2-4DFA-8B2C-9B18B1699EB8"
    assert certificato.intestatari[0].codice_fiscale == "LSADNL68S48L496D"
    assert certificato.intestatari[0].luogo_nascita == "URAS"
    assert certificato.intestatari[0].comune_residenza == "TERRALBA"
    assert certificato.intestatari[0].titoli == "Proprieta` 1/1"
    assert certificato.terreni[0].riordino_code == "R.F. 23/8099"
    assert detail.foglio == "1"
    assert detail.particella == "680"
    assert detail.riordino_maglia == "178"
    assert detail.irridist == "34"


def test_capacitas_storico_anagrafica_parsers_extract_list_and_detail() -> None:
    from app.modules.elaborazioni.capacitas.apps.involture.parsers import (
        parse_anagrafica_detail_html,
        parse_storico_anagrafica_rows,
    )

    storico_payload = """
    [
      {
        ID: '079a6609-2896-4bc8-99c1-5eed0030723a',
        IDXANA: 'd485ad5a-ccb4-493d-b868-414d321a9b2a',
        At: 'AT',
        DataAgg: '14/01/2015 10:54:23',
        Denominazione: 'Cadoni Angelo Antioco',
        CodFisc: 'CDNNLN53M01G113C',
        PIva: '',
        DataNascita: '01/08/1953',
        LuogoNascita: 'ORISTANO',
        Sesso: 'M',
        Anno: '2014',
        Site: 'Z',
        Voltura: '999999',
        Op: 'FIX',
        SN: '9'
      }
    ]
    """
    detail_html = """
    <form name="formDlg" method="post" action="./dlgNuovaAnagrafica.aspx?ID=079a6609-2896-4bc8-99c1-5eed0030723a&storica=1" id="formDlg">
      <input id="txtCognomeDlg" value="Cadoni" />
      <input id="txtNomeDlg" value="Angelo Antioco" />
      <input id="txtSessoDlg" value="M" />
      <input id="txtDataDlg" value="01/08/1953" />
      <input id="txtDenominazioneDlg" value="Cadoni Angelo Antioco" />
      <input id="txtBelfioreDlg" value="G113" />
      <input id="txtProvDlg" value="OR" />
      <input id="txtCodFiscDlg" value="CDNNLN53M01G113C" />
      <input id="txtPIvaDlg" value="" />
      <input id="txtResBelfDlg" value="PALMAS ARBOREA" />
      <input id="txtResProvDlg" value="OR" />
      <input id="txtResLocaDlg" value="" />
      <select id="ddlResToponDlg"><option selected="selected">VIA</option></select>
      <input id="txtResIndirDlg" value="Mameli" />
      <input id="txtResCivDlg" value="18" />
      <input id="txtResSubDlg" value="" />
      <input id="txtResCapDlg" value="09090" />
      <input id="txtAltreInfoEmailDlg" value="cadoni@example.local" />
      <input id="txtAltreInfoTelDlg" value="0783000000" />
      <input id="txtAltreInfoNote1Dlg" value="Storico importato" />
      <input id="cbFisicaDlg" type="checkbox" checked="checked" />
    </form>
    """

    rows = parse_storico_anagrafica_rows(storico_payload)
    detail = parse_anagrafica_detail_html(detail_html)

    assert len(rows) == 1
    assert rows[0].history_id == "079a6609-2896-4bc8-99c1-5eed0030723a"
    assert rows[0].idxana == "d485ad5a-ccb4-493d-b868-414d321a9b2a"
    assert rows[0].denominazione == "Cadoni Angelo Antioco"
    assert rows[0].anno == "2014"
    assert detail.history_id == "079a6609-2896-4bc8-99c1-5eed0030723a"
    assert detail.cognome == "Cadoni"
    assert detail.nome == "Angelo Antioco"
    assert detail.codice_fiscale == "CDNNLN53M01G113C"
    assert detail.residenza_belfiore == "PALMAS ARBOREA"
    assert detail.residenza_toponimo == "VIA"
    assert detail.residenza_indirizzo == "Mameli"
    assert detail.residenza_civico == "18"
    assert detail.note == ["Storico importato"]


def test_capacitas_anagrafica_history_import_by_subject_id(monkeypatch: pytest.MonkeyPatch) -> None:
    create_response = client.post(
        "/elaborazioni/capacitas/credentials",
        headers=auth_headers(),
        json={"label": "Storico PF", "username": "capacitas-user", "password": "capacitas-secret"},
    )
    credential_id = create_response.json()["id"]

    db = TestingSessionLocal()
    subject = AnagraficaSubject(
        subject_type="person",
        status="active",
        source_system="gaia",
        source_name_raw="Cadoni Angelo Antioco",
        requires_review=False,
    )
    db.add(subject)
    db.flush()
    db.add(
        AnagraficaPerson(
            subject_id=subject.id,
            cognome="Cadoni",
            nome="Angelo Antioco",
            codice_fiscale="CDNNLN53M01G113C",
        )
    )
    db.commit()
    subject_id = str(subject.id)
    db.close()

    async def fake_login(self):
        from app.modules.elaborazioni.capacitas.session import CapacitasSession

        self._session = CapacitasSession(token="123e4567-e89b-12d3-a456-426614174000")
        return self._session

    async def fake_activate_app(self, app_name: str) -> None:
        return None

    async def fake_close(self) -> None:
        return None

    async def fake_search_by_cf(self, codice_fiscale: str) -> CapacitasSearchResult:
        assert codice_fiscale == "CDNNLN53M01G113C"
        return CapacitasSearchResult(
            total=1,
            rows=[
                CapacitasAnagrafica(
                    IDXANA="IDX-CADONI",
                    Denominazione="Cadoni Angelo Antioco",
                    CodiceFiscale="CDNNLN53M01G113C",
                )
            ],
        )

    async def fake_fetch_anagrafica_history(self, *, idxana: str):
        assert idxana == "IDX-CADONI"
        return [
            CapacitasStoricoAnagraficaRow(
                ID="HIST-2014",
                IDXANA=idxana,
                DataAgg="14/01/2015 10:54:23",
                Denominazione="Cadoni Angelo Antioco",
                CodFisc="CDNNLN53M01G113C",
                DataNascita="01/08/1953",
                LuogoNascita="ORISTANO",
                Anno="2014",
            ),
            CapacitasStoricoAnagraficaRow(
                ID="HIST-2016",
                IDXANA=idxana,
                DataAgg="14/01/2017 10:54:23",
                Denominazione="Cadoni Angelo Antioco",
                CodFisc="CDNNLN53M01G113C",
                DataNascita="01/08/1953",
                LuogoNascita="ORISTANO",
                Anno="2016",
            ),
        ]

    async def fake_fetch_anagrafica_detail(self, *, history_id: str):
        details = {
            "HIST-2014": CapacitasAnagraficaDetail(
                history_id="HIST-2014",
                idxana="IDX-CADONI",
                cognome="Cadoni",
                nome="Angelo Antioco",
                denominazione="Cadoni Angelo Antioco",
                codice_fiscale="CDNNLN53M01G113C",
                data_nascita=date(1953, 8, 1),
                residenza_belfiore="PALMAS ARBOREA",
                residenza_toponimo="VIA",
                residenza_indirizzo="Mameli",
                residenza_civico="18",
                residenza_cap="09090",
                note=["Storico 2014"],
            ),
            "HIST-2016": CapacitasAnagraficaDetail(
                history_id="HIST-2016",
                idxana="IDX-CADONI",
                cognome="Cadoni",
                nome="Angelo Antioco",
                denominazione="Cadoni Angelo Antioco",
                codice_fiscale="CDNNLN53M01G113C",
                data_nascita=date(1953, 8, 1),
                residenza_belfiore="PALMAS ARBOREA",
                residenza_toponimo="VIA",
                residenza_indirizzo="Garibaldi",
                residenza_civico="22",
                residenza_cap="09090",
                note=["Storico 2016"],
            ),
        }
        return details[history_id]

    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_by_cf", fake_search_by_cf)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.fetch_anagrafica_history", fake_fetch_anagrafica_history)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.fetch_anagrafica_detail", fake_fetch_anagrafica_detail)

    response = client.post(
        "/elaborazioni/capacitas/involture/anagrafica/storico/import",
        headers=auth_headers(),
        json={"credential_id": credential_id, "items": [{"subject_id": subject_id}]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["processed"] == 1
    assert payload["imported"] == 1
    assert payload["skipped"] == 0
    assert payload["failed"] == 0
    assert payload["snapshot_records_imported"] == 2
    assert payload["items"][0]["idxana"] == "IDX-CADONI"
    assert payload["items"][0]["imported_records"] == 2

    db = TestingSessionLocal()
    try:
        updated_subject = db.get(AnagraficaSubject, subject.id)
        snapshots = db.query(AnagraficaPersonSnapshot).filter_by(subject_id=subject.id).order_by(AnagraficaPersonSnapshot.source_ref.asc()).all()
        assert updated_subject is not None
        assert updated_subject.source_system == "capacitas"
        assert updated_subject.source_external_id == "IDX-CADONI"
        assert len(snapshots) == 2
        assert all(item.is_capacitas_history for item in snapshots)
        assert snapshots[0].source_ref == "HIST-2014"
        assert snapshots[1].source_ref == "HIST-2016"
    finally:
        db.close()


def test_capacitas_anagrafica_history_import_file_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    create_response = client.post(
        "/elaborazioni/capacitas/credentials",
        headers=auth_headers(),
        json={"label": "Storico batch", "username": "capacitas-user", "password": "capacitas-secret"},
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

    async def fake_fetch_anagrafica_history(self, *, idxana: str):
        assert idxana == "IDX-BATCH-1"
        return [
            CapacitasStoricoAnagraficaRow(
                ID="HIST-BATCH-1",
                IDXANA=idxana,
                DataAgg="01/02/2020 08:30:00",
                Denominazione="Porcu Alessandro",
                CodFisc="PRCLSN82R27B354B",
                DataNascita="27/10/1982",
                LuogoNascita="CAGLIARI",
                Anno="2020",
            )
        ]

    async def fake_fetch_anagrafica_detail(self, *, history_id: str):
        assert history_id == "HIST-BATCH-1"
        return CapacitasAnagraficaDetail(
            history_id=history_id,
            idxana="IDX-BATCH-1",
            cognome="Porcu",
            nome="Alessandro",
            denominazione="Porcu Alessandro",
            codice_fiscale="PRCLSN82R27B354B",
            data_nascita=date(1982, 10, 27),
            residenza_belfiore="ORISTANO",
            residenza_toponimo="VIA",
            residenza_indirizzo="Roma",
            residenza_civico="10",
            residenza_cap="09170",
        )

    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.fetch_anagrafica_history", fake_fetch_anagrafica_history)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.fetch_anagrafica_detail", fake_fetch_anagrafica_detail)

    files = {"file": ("storico.csv", b"idxana\nIDX-BATCH-1\n", "text/csv")}
    data = {"credential_id": str(credential_id), "continue_on_error": "true"}

    first_response = client.post(
        "/elaborazioni/capacitas/involture/anagrafica/storico/import-file",
        headers=auth_headers(),
        files=files,
        data=data,
    )
    second_response = client.post(
        "/elaborazioni/capacitas/involture/anagrafica/storico/import-file",
        headers=auth_headers(),
        files=files,
        data=data,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["imported"] == 1
    assert first_response.json()["snapshot_records_imported"] == 1
    assert second_response.json()["imported"] == 0
    assert second_response.json()["skipped"] == 1
    assert second_response.json()["items"][0]["message"] == "Storico gia importato."

    db = TestingSessionLocal()
    try:
        person = db.query(AnagraficaPerson).filter_by(codice_fiscale="PRCLSN82R27B354B").one()
        snapshots = db.query(AnagraficaPersonSnapshot).filter_by(subject_id=person.subject_id).all()
        assert len(snapshots) == 1
        assert snapshots[0].source_ref == "HIST-BATCH-1"
    finally:
        db.close()


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


def test_parse_terreni_search_result_accepts_decoded_list_and_empty_list() -> None:
    from app.modules.elaborazioni.capacitas.apps.involture.parsers import parse_terreni_search_result

    # SZ-decoded empty list (e.g. SZe797f7RCLAA= → [])
    result_empty = parse_terreni_search_result([])
    assert result_empty.total == 0
    assert result_empty.rows == []

    # SZ-decoded non-empty list
    rows = [
        {
            "ID": "abc",
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
    ]
    result = parse_terreni_search_result(rows)
    assert result.total == 1
    assert result.rows[0].foglio == "1"
    assert result.rows[0].particella == "680"


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


def test_capacitas_anagrafica_storico_endpoints_return_rows_and_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/elaborazioni/capacitas/credentials",
        headers=auth_headers(),
        json={"label": "Storico Anagrafica", "username": "capacitas-user", "password": "capacitas-secret"},
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

    async def fake_fetch_anagrafica_history(self, *, idxana: str) -> list[CapacitasStoricoAnagraficaRow]:
        assert idxana == "d485ad5a-ccb4-493d-b868-414d321a9b2a"
        return [
            CapacitasStoricoAnagraficaRow(
                ID="079a6609-2896-4bc8-99c1-5eed0030723a",
                IDXANA=idxana,
                Denominazione="Cadoni Angelo Antioco",
                CodFisc="CDNNLN53M01G113C",
                DataNascita="01/08/1953",
                LuogoNascita="ORISTANO",
                Sesso="M",
                Anno="2014",
                Voltura="999999",
                Op="FIX",
            )
        ]

    async def fake_fetch_anagrafica_detail(self, *, history_id: str) -> CapacitasAnagraficaDetail:
        assert history_id == "079a6609-2896-4bc8-99c1-5eed0030723a"
        return CapacitasAnagraficaDetail(
            history_id=history_id,
            idxana="d485ad5a-ccb4-493d-b868-414d321a9b2a",
            is_persona_fisica=True,
            cognome="Cadoni",
            nome="Angelo Antioco",
            denominazione="Cadoni Angelo Antioco",
            codice_fiscale="CDNNLN53M01G113C",
            data_nascita=date(1953, 8, 1),
            luogo_nascita="ORISTANO",
            residenza_belfiore="PALMAS ARBOREA",
            residenza_provincia="OR",
            residenza_toponimo="VIA",
            residenza_indirizzo="Mameli",
            residenza_civico="18",
            residenza_cap="09090",
            note=["Storico importato"],
        )

    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr(
        "app.modules.elaborazioni.capacitas.client.InVoltureClient.fetch_anagrafica_history",
        fake_fetch_anagrafica_history,
    )
    monkeypatch.setattr(
        "app.modules.elaborazioni.capacitas.client.InVoltureClient.fetch_anagrafica_detail",
        fake_fetch_anagrafica_detail,
    )

    storico_response = client.get(
        f"/elaborazioni/capacitas/involture/anagrafica/d485ad5a-ccb4-493d-b868-414d321a9b2a/storico?credential_id={credential_id}",
        headers=auth_headers(),
    )
    detail_response = client.get(
        f"/elaborazioni/capacitas/involture/anagrafica/storico/079a6609-2896-4bc8-99c1-5eed0030723a?credential_id={credential_id}",
        headers=auth_headers(),
    )

    assert storico_response.status_code == 200
    assert storico_response.json()[0]["ID"] == "079a6609-2896-4bc8-99c1-5eed0030723a"
    assert storico_response.json()[0]["Denominazione"] == "Cadoni Angelo Antioco"
    assert detail_response.status_code == 200
    assert detail_response.json()["history_id"] == "079a6609-2896-4bc8-99c1-5eed0030723a"
    assert detail_response.json()["cognome"] == "Cadoni"
    assert detail_response.json()["residenza_indirizzo"] == "Mameli"

    db = TestingSessionLocal()
    try:
        credential = db.get(CapacitasCredential, credential_id)
        assert credential is not None
        assert credential.last_error is None
        assert credential.last_used_at is not None
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


def test_capacitas_rpt_certificato_link_returns_browser_session_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/elaborazioni/capacitas/credentials",
        headers=auth_headers(),
        json={"label": "Direct link", "username": "capacitas-user", "password": "capacitas-secret"},
    )
    credential_id = create_response.json()["id"]

    db = TestingSessionLocal()
    try:
        db.add(
            CatCapacitasTerrenoRow(
                cco="0A1103877",
                com="289",
                pvc="097",
                fra="38",
                ccs="00000",
                collected_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
    finally:
        db.close()

    async def fail_login(self):
        raise AssertionError("Il link certificato deve usare la sessione browser, non il login backend")

    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fail_login)

    response = client.get(
        f"/elaborazioni/capacitas/involture/link/rpt-certificato?cco=0A1103877&credential_id={credential_id}",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    url = response.json()["url"]
    assert "rptCertificato.aspx" in url
    assert "CCO=0A1103877" in url
    assert "COM=289" in url
    assert "PVC=097" in url
    assert "FRA=38" in url
    assert "CCS=00000" in url
    assert "token=" not in url
    assert "app=" not in url
    assert "tenant=" not in url
    assert "BC=" not in url


def test_capacitas_rpt_certificato_link_prefers_certificato_snapshot() -> None:
    db = TestingSessionLocal()
    try:
        db.add(
            CatCapacitasCertificato(
                cco="0A2200001",
                com="777",
                pvc="123",
                fra="55",
                ccs="00009",
                collected_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            CatCapacitasTerrenoRow(
                cco="0A2200001",
                com="777",
                pvc="123",
                fra="55",
                ccs="00009",
                collected_at=datetime.now(timezone.utc) - timedelta(days=1),
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get(
        "/elaborazioni/capacitas/involture/link/rpt-certificato?cco=0A2200001",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    url = response.json()["url"]
    assert "CCO=0A2200001" in url
    assert "COM=777" in url
    assert "PVC=123" in url
    assert "FRA=55" in url
    assert "CCS=00009" in url


def test_capacitas_rpt_certificato_link_falls_back_to_occupancy_when_terreno_missing() -> None:
    db = TestingSessionLocal()
    try:
        unit = CatConsorzioUnit(
            cod_comune_capacitas=95,
            source_comune_label="ORISTANO",
            sezione_catastale="",
            foglio="1",
            particella="2",
            is_active=True,
        )
        db.add(unit)
        db.flush()
        db.add(
            CatConsorzioOccupancy(
                unit_id=unit.id,
                cco="0A2200002",
                com="451",
                pvc="011",
                fra="44",
                ccs="00007",
                source_type="capacitas_terreni",
                relationship_type="utilizzatore_reale",
                is_current=True,
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get(
        "/elaborazioni/capacitas/involture/link/rpt-certificato?cco=0A2200002",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    url = response.json()["url"]
    assert "COM=451" in url
    assert "PVC=011" in url
    assert "FRA=44" in url
    assert "CCS=00007" in url


def test_capacitas_rpt_certificato_link_uses_explicit_context_params() -> None:
    db = TestingSessionLocal()
    try:
        db.add(
            CatCapacitasCertificato(
                cco="0A2200004",
                com="165",
                pvc="097",
                fra="31",
                ccs="00000",
                collected_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            CatCapacitasCertificato(
                cco="0A2200004",
                com="289",
                pvc="097",
                fra="38",
                ccs="00000",
                collected_at=datetime.now(timezone.utc) - timedelta(days=1),
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get(
        "/elaborazioni/capacitas/involture/link/rpt-certificato?cco=0A2200004&com=289&pvc=097&fra=38&ccs=00000",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    url = response.json()["url"]
    assert "CCO=0A2200004" in url
    assert "COM=289" in url
    assert "PVC=097" in url
    assert "FRA=38" in url
    assert "CCS=00000" in url


def test_capacitas_rpt_certificato_link_rejects_ambiguous_cco_without_context() -> None:
    db = TestingSessionLocal()
    try:
        db.add(
            CatCapacitasCertificato(
                cco="0A2200099",
                com="165",
                pvc="097",
                fra="31",
                ccs="00000",
                collected_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            CatCapacitasCertificato(
                cco="0A2200099",
                com="289",
                pvc="097",
                fra="38",
                ccs="00000",
                collected_at=datetime.now(timezone.utc) - timedelta(days=1),
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get(
        "/elaborazioni/capacitas/involture/link/rpt-certificato?cco=0A2200099",
        headers=auth_headers(),
    )

    assert response.status_code == 409
    assert "ambiguo" in response.json()["detail"]
    assert "COM, PVC, FRA e CCS" in response.json()["detail"]


def test_capacitas_rpt_certificato_link_reports_incomplete_source_details() -> None:
    db = TestingSessionLocal()
    try:
        db.add(
            CatCapacitasCertificato(
                cco="0A2200003",
                com="289",
                pvc=None,
                fra=None,
                ccs="00000",
                collected_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get(
        "/elaborazioni/capacitas/involture/link/rpt-certificato?cco=0A2200003",
        headers=auth_headers(),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "CCO 0A2200003 presente in cat_capacitas_certificati ma incompleto: mancano PVC, FRA."


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

    async def fake_search_frazioni(self, query: str):
        return [CapacitasLookupOption(id="38", display="38 URAS")]

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
            intestatari=[
                {
                    "idxana": "BD23974F-E9A2-4DFA-8B2C-9B18B1699EB8",
                    "idxesa": "D5DAB932-5D57-4088-A55B-C60EAE215F59",
                    "codice_fiscale": "LSADNL68S48L496D",
                    "denominazione": "Lasi Daniela",
                    "data_nascita": date(1968, 11, 8),
                    "luogo_nascita": "URAS",
                    "residenza": "09098 TERRALBA (OR) - VIA Manca 151",
                    "comune_residenza": "TERRALBA",
                    "cap": "09098",
                    "titoli": "Proprieta` 1/1",
                }
            ],
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
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_frazioni", fake_search_frazioni)
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
        assert db.query(CatCapacitasIntestatario).count() == 1
        assert db.query(CatCapacitasTerrenoDetail).count() == 1
        assert db.query(AnagraficaSubject).count() == 1
        person = db.query(AnagraficaPerson).one()
        assert person.codice_fiscale == "LSADNL68S48L496D"
        assert person.comune_residenza == "TERRALBA"
    finally:
        db.close()


@pytest.mark.anyio
async def test_sync_certificato_snapshot_skips_annual_links_when_cert_context_is_ambiguous() -> None:
    from app.services.elaborazioni_capacitas_terreni import sync_certificato_snapshot

    class FakeClient:
        async def fetch_certificato(self, **kwargs) -> CapacitasTerrenoCertificato:
            return CapacitasTerrenoCertificato(
                cco="0A2200001",
                fra="38",
                ccs="00000",
                pvc="097",
                com="289",
                partita_code="0A2200001/38/00000",
                intestatari=[
                    {
                        "codice_fiscale": "RSSMRA80A01H501Z",
                        "denominazione": "Rossi Mario",
                        "titoli": "Proprieta` 1/1",
                    }
                ],
            )

    db = TestingSessionLocal()
    try:
        batch = db.query(CatImportBatch).first()
        assert batch is not None
        db.add_all(
            [
                CatUtenzaIrrigua(
                    import_batch_id=batch.id,
                    anno_campagna=2026,
                    cco="0A2200001",
                    cod_comune_capacitas=289,
                    cod_frazione=38,
                    foglio="1",
                    particella="680",
                ),
                CatUtenzaIrrigua(
                    import_batch_id=batch.id,
                    anno_campagna=2026,
                    cco="0A2200001",
                    cod_comune_capacitas=289,
                    cod_frazione=38,
                    foglio="2",
                    particella="15",
                ),
            ]
        )
        db.flush()

        await sync_certificato_snapshot(
            db,
            FakeClient(),  # type: ignore[arg-type]
            cco="0A2200001",
            com="289",
            pvc="097",
            fra="38",
            ccs="00000",
        )
        db.flush()

        assert db.query(CatCapacitasCertificato).count() == 1
        assert db.query(CatCapacitasIntestatario).count() == 1
        assert db.query(CatUtenzaIntestatario).count() == 0
    finally:
        db.close()


@pytest.mark.anyio
async def test_sync_certificato_snapshot_persists_only_explicit_target_utenza() -> None:
    from app.services.elaborazioni_capacitas_terreni import sync_certificato_snapshot

    class FakeClient:
        async def fetch_certificato(self, **kwargs) -> CapacitasTerrenoCertificato:
            return CapacitasTerrenoCertificato(
                cco="0A2200002",
                fra="38",
                ccs="00000",
                pvc="097",
                com="289",
                partita_code="0A2200002/38/00000",
                intestatari=[
                    {
                        "codice_fiscale": "BNCLCU82A01H501Z",
                        "denominazione": "Bianchi Luca",
                        "titoli": "Proprieta` 1/1",
                    }
                ],
            )

    db = TestingSessionLocal()
    try:
        batch = db.query(CatImportBatch).first()
        assert batch is not None
        target = CatUtenzaIrrigua(
            import_batch_id=batch.id,
            anno_campagna=2026,
            cco="0A2200002",
            cod_comune_capacitas=289,
            cod_frazione=38,
            foglio="1",
            particella="680",
        )
        other = CatUtenzaIrrigua(
            import_batch_id=batch.id,
            anno_campagna=2026,
            cco="0A2200002",
            cod_comune_capacitas=289,
            cod_frazione=38,
            foglio="2",
            particella="15",
        )
        db.add_all([target, other])
        db.flush()

        await sync_certificato_snapshot(
            db,
            FakeClient(),  # type: ignore[arg-type]
            cco="0A2200002",
            com="289",
            pvc="097",
            fra="38",
            ccs="00000",
            target_utenze=[target],
        )
        db.flush()

        annual_links = db.query(CatUtenzaIntestatario).all()
        assert len(annual_links) == 1
        assert annual_links[0].utenza_id == target.id
        assert annual_links[0].anno_riferimento == 2026
    finally:
        db.close()


@pytest.mark.anyio
async def test_sync_certificato_snapshot_reuses_latest_identical_snapshot() -> None:
    from app.services.elaborazioni_capacitas_terreni import sync_certificato_snapshot

    class FakeClient:
        def __init__(self) -> None:
            self.calls = 0

        async def fetch_certificato(self, **kwargs) -> CapacitasTerrenoCertificato:
            self.calls += 1
            return CapacitasTerrenoCertificato(
                cco="0A2200003",
                fra="38",
                ccs="00000",
                pvc="097",
                com="289",
                partita_code="0A2200003/38/00000",
                intestatari=[
                    {
                        "idxana": "IDX-2200003",
                        "codice_fiscale": "VRDLGI80A01H501Z",
                        "denominazione": "Verdi Luigi",
                        "titoli": "Proprieta` 1/1",
                    }
                ],
                raw_html=f"<html>certificato-{self.calls}</html>",
            )

    client = FakeClient()
    db = TestingSessionLocal()
    try:
        _, first_snapshot = await sync_certificato_snapshot(
            db,
            client,  # type: ignore[arg-type]
            cco="0A2200003",
            com="289",
            pvc="097",
            fra="38",
            ccs="00000",
            collected_at=datetime(2026, 5, 11, 8, 0, tzinfo=timezone.utc),
        )
        db.flush()

        _, second_snapshot = await sync_certificato_snapshot(
            db,
            client,  # type: ignore[arg-type]
            cco="0A2200003",
            com="289",
            pvc="097",
            fra="38",
            ccs="00000",
            collected_at=datetime(2026, 5, 11, 9, 0, tzinfo=timezone.utc),
        )
        db.flush()

        assert first_snapshot.id == second_snapshot.id
        assert db.query(CatCapacitasCertificato).count() == 1
        assert db.query(CatCapacitasIntestatario).count() == 1
        snapshot = db.query(CatCapacitasCertificato).one()
        assert snapshot.collected_at == datetime(2026, 5, 11, 9, 0, tzinfo=timezone.utc)
    finally:
        db.close()


@pytest.mark.anyio
async def test_sync_certificato_snapshot_replaces_annual_links_for_same_utenza_year() -> None:
    from app.services.elaborazioni_capacitas_terreni import sync_certificato_snapshot

    class FakeClient:
        async def fetch_certificato(self, **kwargs) -> CapacitasTerrenoCertificato:
            return CapacitasTerrenoCertificato(
                cco="0A2200004",
                fra="38",
                ccs="00000",
                pvc="097",
                com="289",
                partita_code="0A2200004/38/00000",
                intestatari=[
                    {
                        "idxana": "IDX-OWNER-1",
                        "codice_fiscale": "RSSMRA80A01H501Z",
                        "denominazione": "Rossi Mario",
                        "titoli": "Proprieta` 1/2",
                    },
                    {
                        "idxana": "IDX-OWNER-2",
                        "codice_fiscale": "BNCLCU82A01H501Z",
                        "denominazione": "Bianchi Luca",
                        "titoli": "Proprieta` 1/2",
                    },
                ],
            )

    db = TestingSessionLocal()
    try:
        batch = db.query(CatImportBatch).first()
        assert batch is not None
        utenza = CatUtenzaIrrigua(
            import_batch_id=batch.id,
            anno_campagna=2026,
            cco="0A2200004",
            cod_comune_capacitas=289,
            cod_frazione=38,
            foglio="1",
            particella="680",
        )
        db.add(utenza)
        db.flush()
        db.add(
            CatUtenzaIntestatario(
                utenza_id=utenza.id,
                idxana="IDX-OLD",
                anno_riferimento=2026,
                denominazione="Residuo Storico",
                titoli="Proprieta` 1/1",
                collected_at=datetime(2026, 5, 1, 8, 0, tzinfo=timezone.utc),
            )
        )
        db.flush()

        await sync_certificato_snapshot(
            db,
            FakeClient(),  # type: ignore[arg-type]
            cco="0A2200004",
            com="289",
            pvc="097",
            fra="38",
            ccs="00000",
            target_utenze=[utenza],
            collected_at=datetime(2026, 5, 11, 10, 0, tzinfo=timezone.utc),
        )
        db.flush()

        annual_links = (
            db.query(CatUtenzaIntestatario)
            .filter(CatUtenzaIntestatario.utenza_id == utenza.id, CatUtenzaIntestatario.anno_riferimento == 2026)
            .order_by(CatUtenzaIntestatario.denominazione.asc())
            .all()
        )
        assert len(annual_links) == 2
        assert [item.denominazione for item in annual_links] == ["Bianchi Luca", "Rossi Mario"]
        assert all(item.idxana != "IDX-OLD" for item in annual_links)
    finally:
        db.close()


def test_catasto_particella_capacitas_sync_route_updates_last_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    create_response = client.post(
        "/elaborazioni/capacitas/credentials",
        headers=auth_headers(),
        json={"label": "Particella Sync", "username": "capacitas-user", "password": "capacitas-secret"},
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

    async def fake_search_frazioni(self, query: str):
        return [CapacitasLookupOption(id="38", display="38 URAS")]

    async def fake_search_terreni(self, request) -> CapacitasTerreniSearchResult:
        return CapacitasTerreniSearchResult(
            total=1,
            rows=[
                {
                    "ID": "single-row-1",
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
            external_row_id="single-row-1",
            foglio="1",
            particella="680",
            raw_html="<html>dettaglio</html>",
        )

    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_frazioni", fake_search_frazioni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_terreni", fake_search_terreni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.fetch_certificato", fake_fetch_certificato)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.fetch_terreno_detail", fake_fetch_detail)

    db = TestingSessionLocal()
    try:
        particella = db.scalar(select(CatParticella).where(CatParticella.foglio == "1", CatParticella.particella == "680"))
        assert particella is not None
        particella_id = str(particella.id)
    finally:
        db.close()

    response = client.post(
        f"/catasto/particelle/{particella_id}/capacitas-sync",
        headers=auth_headers(),
        json={"credential_id": credential_id, "fetch_certificati": True, "fetch_details": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "synced"
    assert payload["particella"]["capacitas_last_sync_status"] == "synced"
    assert payload["particella"]["capacitas_last_sync_at"] is not None
    assert payload["job_id"] is not None

    db = TestingSessionLocal()
    try:
        refreshed = db.get(CatParticella, particella.id)
        assert refreshed is not None
        assert refreshed.capacitas_last_sync_status == "synced"
        assert refreshed.capacitas_last_sync_at is not None
        assert refreshed.capacitas_last_sync_job_id is not None

        job = db.get(CapacitasParticelleSyncJob, refreshed.capacitas_last_sync_job_id)
        assert job is not None
        assert job.mode == "single_particella"
        assert job.status == "succeeded"
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


def test_capacitas_terreni_sync_updates_existing_person_with_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    create_response = client.post(
        "/elaborazioni/capacitas/credentials",
        headers=auth_headers(),
        json={"label": "Terreni Snapshot", "username": "capacitas-user", "password": "capacitas-secret"},
    )
    credential_id = create_response.json()["id"]

    db = TestingSessionLocal()
    try:
        subject = AnagraficaSubject(
            subject_type="person",
            status="active",
            source_system="gaia",
            source_name_raw="Lasi_Daniela_LSADNL68S48L496D",
            requires_review=False,
        )
        db.add(subject)
        db.flush()
        db.add(
            AnagraficaPerson(
                subject_id=subject.id,
                cognome="Lasi",
                nome="Daniela",
                codice_fiscale="LSADNL68S48L496D",
                comune_residenza="URAS",
                indirizzo="VIA Vecchia 1",
            )
        )
        batch = db.query(CatImportBatch).filter_by(filename="seed-terreni.xlsx").one()
        unrelated_particella = db.query(CatParticella).filter_by(codice_catastale="L122", foglio="14", particella="330").one()
        db.add(
            CatUtenzaIrrigua(
                import_batch_id=batch.id,
                anno_campagna=2026,
                cco="0A1103877",
                comune_id=unrelated_particella.comune_id,
                cod_comune_capacitas=280,
                cod_frazione=12,
                nome_comune="Terralba",
                foglio="14",
                particella="330",
                particella_id=unrelated_particella.id,
                sup_catastale_mq=Decimal("2100.00"),
                sup_irrigabile_mq=Decimal("2100.00"),
                codice_fiscale="RSSMRA80A01H501U",
                codice_fiscale_raw="RSSMRA80A01H501U",
            )
        )
        db.commit()
    finally:
        db.close()

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
                    "ID": "snapshot-row-1",
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
            intestatari=[
                {
                    "idxana": "BD23974F-E9A2-4DFA-8B2C-9B18B1699EB8",
                    "idxesa": "D5DAB932-5D57-4088-A55B-C60EAE215F59",
                    "codice_fiscale": "LSADNL68S48L496D",
                    "denominazione": "Lasi Daniela",
                    "comune_residenza": "TERRALBA",
                    "residenza": "09098 TERRALBA (OR) - VIA Manca 151",
                    "cap": "09098",
                }
            ],
            raw_html="<html>certificato</html>",
        )

    async def fake_fetch_detail(self, **kwargs) -> CapacitasTerrenoDetail:
        return CapacitasTerrenoDetail(external_row_id="snapshot-row-1", foglio="1", particella="680", raw_html="<html>dettaglio</html>")

    async def fake_fetch_anagrafica_history(self, *, idxana: str):
        assert idxana == "BD23974F-E9A2-4DFA-8B2C-9B18B1699EB8"
        return [
            CapacitasStoricoAnagraficaRow(
                ID="HIST-1",
                IDXANA=idxana,
                At="AT",
                DataAgg="14/01/2026 10:54:23",
                Denominazione="Lasi Daniela",
                CodFisc="LSADNL68S48L496D",
                DataNascita="18/11/1968",
                LuogoNascita="TERRALBA",
                Sesso="F",
                Anno="2026",
                Site="Z",
                Voltura="1",
                Op="FIX",
                SN="9",
            )
        ]

    async def fake_fetch_anagrafica_detail(self, *, history_id: str):
        assert history_id == "HIST-1"
        return CapacitasAnagraficaDetail(
            history_id=history_id,
            idxana="BD23974F-E9A2-4DFA-8B2C-9B18B1699EB8",
            is_persona_fisica=True,
            cognome="Lasi",
            nome="Daniela",
            sesso="F",
            data_nascita=date(1968, 11, 18),
            denominazione="Lasi Daniela",
            codice_fiscale="LSADNL68S48L496D",
            residenza_belfiore="TERRALBA",
            residenza_cap="09098",
            residenza_toponimo="VIA",
            residenza_indirizzo="Manca",
            residenza_civico="151",
            note=[],
        )

    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_terreni", fake_search_terreni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.fetch_certificato", fake_fetch_certificato)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.fetch_terreno_detail", fake_fetch_detail)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.fetch_anagrafica_history", fake_fetch_anagrafica_history)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.fetch_anagrafica_detail", fake_fetch_anagrafica_detail)

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

    db = TestingSessionLocal()
    try:
        person = db.query(AnagraficaPerson).filter_by(codice_fiscale="LSADNL68S48L496D").one()
        assert person.comune_residenza == "TERRALBA"
        assert person.indirizzo == "VIA Manca 151"
        assert db.query(AnagraficaPersonSnapshot).count() == 2
        snapshots = db.query(AnagraficaPersonSnapshot).order_by(AnagraficaPersonSnapshot.is_capacitas_history.desc()).all()
        imported_snapshot = next(item for item in snapshots if item.is_capacitas_history)
        delta_snapshot = next(item for item in snapshots if not item.is_capacitas_history)
        assert imported_snapshot.source_ref == "HIST-1"
        assert imported_snapshot.comune_residenza == "TERRALBA"
        assert imported_snapshot.indirizzo == "VIA Manca 151"
        assert delta_snapshot.comune_residenza == "URAS"
        assert db.query(CatCapacitasIntestatario).one().subject_id == person.subject_id
        assert db.query(CatUtenzaIntestatario).count() == 1
        utenza_intestatario = db.query(CatUtenzaIntestatario).one()
        assert utenza_intestatario.utenza_record.foglio == "1"
        assert utenza_intestatario.utenza_record.particella == "680"
        assert utenza_intestatario.subject_id == person.subject_id
        assert utenza_intestatario.residenza == "VIA Manca 151"
        assert utenza_intestatario.comune_residenza == "TERRALBA"
        assert utenza_intestatario.cap == "09098"
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


def test_capacitas_terreni_sync_batch_tries_multiple_exact_comune_matches_until_particella_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/elaborazioni/capacitas/credentials",
        headers=auth_headers(),
        json={"label": "Terreni Batch Ambigui", "username": "capacitas-user", "password": "capacitas-secret"},
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
        assert query == "Arborea"
        return [
            CapacitasLookupOption(id="31", display="ARBOREA"),
            CapacitasLookupOption(id="12", display="PALMAS*ARBOREA"),
            CapacitasLookupOption(id="34", display="PALMAS*ARBOREA"),
        ]

    attempted_frazioni: list[str] = []

    async def fake_search_terreni(self, request) -> CapacitasTerreniSearchResult:
        attempted_frazioni.append(request.frazione_id)
        if request.frazione_id != "31":
            raise RuntimeError("Particella non trovata")
        return CapacitasTerreniSearchResult(
            total=1,
            rows=[
                {
                    "ID": "batch-row-arborea-1",
                    "PVC": "097",
                    "COM": "165",
                    "CCO": "0A1103877",
                    "FRA": "31",
                    "CCS": "00000",
                    "Foglio": "14",
                    "Partic": "330",
                    "Anno": "2026",
                    "Belfiore": "A357",
                    "Ta_ext": " 9",
                }
            ],
        )

    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_frazioni", fake_search_frazioni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_terreni", fake_search_terreni)

    response = client.post(
        "/elaborazioni/capacitas/involture/terreni/sync-batch",
        headers=auth_headers(),
        json={
            "credential_id": credential_id,
            "continue_on_error": True,
            "fetch_certificati": False,
            "fetch_details": False,
            "items": [{"comune": "Arborea", "foglio": "14", "particella": "330"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["processed_items"] == 1
    assert payload["failed_items"] == 0
    assert payload["items"][0]["ok"] is True
    assert attempted_frazioni == ["31"]


def test_capacitas_terreni_sync_batch_tries_duplicate_comune_matches_in_sequence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Quando frazione '14' non trova la particella (eccezione nella probe), il codice procede
    con la frazione '35' che ha risultati. Il probe chiama search_terreni su entrambe le
    frazioni, poi la sync chiama search_terreni di nuovo sulla frazione selezionata ('35'):
    la sequenza attesa è ['14', '35', '35']."""
    create_response = client.post(
        "/elaborazioni/capacitas/credentials",
        headers=auth_headers(),
        json={"label": "Terreni Batch Santa Giusta", "username": "capacitas-user", "password": "capacitas-secret"},
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
        assert query == "Santa Giusta"
        return [
            CapacitasLookupOption(id="14", display="SANTA GIUSTA"),
            CapacitasLookupOption(id="35", display="SANTA GIUSTA"),
        ]

    attempted_frazioni: list[str] = []

    async def fake_search_terreni(self, request) -> CapacitasTerreniSearchResult:
        attempted_frazioni.append(request.frazione_id)
        if request.frazione_id == "14":
            raise RuntimeError("Particella non trovata")
        return CapacitasTerreniSearchResult(
            total=1,
            rows=[
                {
                    "ID": "batch-row-sg-1",
                    "PVC": "097",
                    "COM": "292",
                    "CCO": "0A1103877",
                    "FRA": "35",
                    "CCS": "00000",
                    "Foglio": "7",
                    "Partic": "123",
                    "Anno": "2026",
                    "Belfiore": "I205",
                    "Ta_ext": " 9",
                }
            ],
        )

    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_frazioni", fake_search_frazioni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_terreni", fake_search_terreni)

    response = client.post(
        "/elaborazioni/capacitas/involture/terreni/sync-batch",
        headers=auth_headers(),
        json={
            "credential_id": credential_id,
            "continue_on_error": True,
            "fetch_certificati": False,
            "fetch_details": False,
            "items": [{"comune": "Santa Giusta", "foglio": "7", "particella": "123"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["processed_items"] == 1
    assert payload["failed_items"] == 0
    assert payload["items"][0]["ok"] is True
    # Probe: ["14" (eccezione), "35"] → un solo hit → sync usa solo "35" → search_terreni("35") di nuovo
    assert attempted_frazioni == ["14", "35", "35"]


def test_capacitas_terreni_sync_batch_matches_comune_without_asterisk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """'03 CABRAS' (no asterisk) must match the query 'Cabras' via the comune part."""
    create_response = client.post(
        "/elaborazioni/capacitas/credentials",
        headers=auth_headers(),
        json={"label": "Terreni Cabras", "username": "capacitas-user", "password": "capacitas-secret"},
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
        assert query == "Cabras"
        return [
            CapacitasLookupOption(id="03", display="03 CABRAS"),
            CapacitasLookupOption(id="20", display="20 SOLANAS*CABRAS"),
        ]

    attempted_frazioni: list[str] = []

    async def fake_search_terreni(self, request) -> CapacitasTerreniSearchResult:
        attempted_frazioni.append(request.frazione_id)
        if request.frazione_id != "03":
            raise RuntimeError("Particella non trovata")
        return CapacitasTerreniSearchResult(
            total=1,
            rows=[
                {
                    "ID": "cabras-row-1",
                    "PVC": "097",
                    "COM": "050",
                    "CCO": "0A1103877",
                    "FRA": "03",
                    "CCS": "00000",
                    "Foglio": "5",
                    "Partic": "200",
                    "Anno": "2026",
                    "Belfiore": "B354",
                    "Ta_ext": " 9",
                }
            ],
        )

    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_frazioni", fake_search_frazioni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_terreni", fake_search_terreni)

    response = client.post(
        "/elaborazioni/capacitas/involture/terreni/sync-batch",
        headers=auth_headers(),
        json={
            "credential_id": credential_id,
            "continue_on_error": True,
            "fetch_certificati": False,
            "fetch_details": False,
            "items": [{"comune": "Cabras", "foglio": "5", "particella": "200"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["processed_items"] == 1
    assert payload["failed_items"] == 0
    assert payload["items"][0]["ok"] is True
    assert "03" in attempted_frazioni


def test_capacitas_terreni_sync_batch_matches_oristano_city_among_frazioni(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """For Oristano sezione A, the city record '11 ORISTANO*ORISTANO' must be tried first."""
    create_response = client.post(
        "/elaborazioni/capacitas/credentials",
        headers=auth_headers(),
        json={"label": "Terreni Oristano", "username": "capacitas-user", "password": "capacitas-secret"},
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
        assert query == "Oristano"
        return [
            CapacitasLookupOption(id="04", display="04 DONIGALA FENUGHEDU*ORISTANO"),
            CapacitasLookupOption(id="09", display="09 NURAXINIEDDU*ORISTANO"),
            CapacitasLookupOption(id="11", display="11 ORISTANO*ORISTANO"),
            CapacitasLookupOption(id="18", display="18 SILI'*ORISTANO"),
        ]

    attempted_frazioni: list[str] = []

    async def fake_search_terreni(self, request) -> CapacitasTerreniSearchResult:
        attempted_frazioni.append(request.frazione_id)
        if request.frazione_id != "11":
            raise RuntimeError("Particella non trovata")
        return CapacitasTerreniSearchResult(
            total=1,
            rows=[
                {
                    "ID": "oristano-row-1",
                    "PVC": "097",
                    "COM": "170",
                    "CCO": "0A1103877",
                    "FRA": "11",
                    "CCS": "00000",
                    "Foglio": "3",
                    "Partic": "500",
                    "Anno": "2026",
                    "Belfiore": "G113",
                    "Ta_ext": " 9",
                }
            ],
        )

    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_frazioni", fake_search_frazioni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_terreni", fake_search_terreni)

    response = client.post(
        "/elaborazioni/capacitas/involture/terreni/sync-batch",
        headers=auth_headers(),
        json={
            "credential_id": credential_id,
            "continue_on_error": True,
            "fetch_certificati": False,
            "fetch_details": False,
            "items": [{"comune": "Oristano", "sezione": "A", "foglio": "3", "particella": "500"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["processed_items"] == 1
    assert payload["failed_items"] == 0
    assert payload["items"][0]["ok"] is True
    assert attempted_frazioni[0] == "11"


def test_capacitas_terreni_sync_batch_prioritizes_cabras_section_b(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """For Cabras sezione B, '20 SOLANAS*CABRAS' must be preferred over the city row."""
    create_response = client.post(
        "/elaborazioni/capacitas/credentials",
        headers=auth_headers(),
        json={"label": "Terreni Cabras B", "username": "capacitas-user", "password": "capacitas-secret"},
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
        assert query == "Cabras"
        return [
            CapacitasLookupOption(id="03", display="03 CABRAS"),
            CapacitasLookupOption(id="20", display="20 SOLANAS*CABRAS"),
        ]

    attempted_frazioni: list[str] = []

    async def fake_search_terreni(self, request) -> CapacitasTerreniSearchResult:
        attempted_frazioni.append(request.frazione_id)
        if request.frazione_id != "20":
            raise RuntimeError("Particella non trovata")
        return CapacitasTerreniSearchResult(
            total=1,
            rows=[
                {
                    "ID": "cabras-b-row-1",
                    "PVC": "097",
                    "COM": "050",
                    "CCO": "0A1103877",
                    "FRA": "20",
                    "CCS": "00000",
                    "Foglio": "5",
                    "Partic": "200",
                    "Anno": "2026",
                    "Belfiore": "B354",
                    "Ta_ext": " 9",
                }
            ],
        )

    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_frazioni", fake_search_frazioni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_terreni", fake_search_terreni)

    response = client.post(
        "/elaborazioni/capacitas/involture/terreni/sync-batch",
        headers=auth_headers(),
        json={
            "credential_id": credential_id,
            "continue_on_error": True,
            "fetch_certificati": False,
            "fetch_details": False,
            "items": [{"comune": "Cabras", "sezione": "B", "foglio": "5", "particella": "200"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["processed_items"] == 1
    assert payload["failed_items"] == 0
    assert payload["items"][0]["ok"] is True
    assert attempted_frazioni[0] == "20"


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
    assert create_job_response.json()["status"] == "pending"

    list_jobs_response = client.get("/elaborazioni/capacitas/involture/terreni/jobs", headers=auth_headers())
    get_job_response = client.get(f"/elaborazioni/capacitas/involture/terreni/jobs/{job_id}", headers=auth_headers())

    assert list_jobs_response.status_code == 200
    assert any(item["id"] == job_id for item in list_jobs_response.json())
    assert get_job_response.status_code == 200
    assert get_job_response.json()["status"] == "pending"
    assert get_job_response.json()["result_json"] is None

    rerun_job_response = client.post(
        f"/elaborazioni/capacitas/involture/terreni/jobs/{job_id}/run",
        headers=auth_headers(),
    )
    assert rerun_job_response.status_code == 200
    assert rerun_job_response.json()["status"] == "pending"

    db = TestingSessionLocal()
    try:
        job = db.get(CapacitasTerreniSyncJob, job_id)
        assert job is not None
        assert job.status == "pending"
        assert job.result_json is None
    finally:
        db.close()


def test_capacitas_terreni_job_create_rejects_inactive_credential() -> None:
    create_response = client.post(
        "/elaborazioni/capacitas/credentials",
        headers=auth_headers(),
        json={"label": "Terreni Inactive", "username": "capacitas-user", "password": "capacitas-secret", "active": False},
    )
    credential_id = create_response.json()["id"]

    response = client.post(
        "/elaborazioni/capacitas/involture/terreni/jobs",
        headers=auth_headers(),
        json={
            "credential_id": credential_id,
            "items": [{"comune": "Uras", "foglio": "1", "particella": "680"}],
        },
    )

    assert response.status_code == 503
    assert "non attiva" in response.json()["detail"]


def test_capacitas_terreni_job_delete_removes_terminal_job() -> None:
    db = TestingSessionLocal()
    try:
        job = CapacitasTerreniSyncJob(
            requested_by_user_id=1,
            credential_id=None,
            status="succeeded",
            mode="batch",
            payload_json={"items": [{"comune": "Uras", "foglio": "1", "particella": "680"}]},
            result_json={"processed_items": 1},
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id
    finally:
        db.close()

    response = client.delete(f"/elaborazioni/capacitas/involture/terreni/jobs/{job_id}", headers=auth_headers())
    assert response.status_code == 204

    db = TestingSessionLocal()
    try:
        assert db.get(CapacitasTerreniSyncJob, job_id) is None
    finally:
        db.close()


def test_capacitas_terreni_job_delete_rejects_processing_job() -> None:
    db = TestingSessionLocal()
    try:
        job = CapacitasTerreniSyncJob(
            requested_by_user_id=1,
            credential_id=None,
            status="processing",
            mode="batch",
            payload_json={"items": [{"comune": "Uras", "foglio": "1", "particella": "680"}]},
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id
    finally:
        db.close()

    response = client.delete(f"/elaborazioni/capacitas/involture/terreni/jobs/{job_id}", headers=auth_headers())
    assert response.status_code == 409
    assert "terminato" in response.json()["detail"]


def test_capacitas_particelle_jobs_list_expires_stale_processing_job() -> None:
    db = TestingSessionLocal()
    try:
        job = CapacitasParticelleSyncJob(
            requested_by_user_id=1,
            credential_id=None,
            status="processing",
            mode="progressive_catalog",
            payload_json={"only_due": True},
            result_json={"processed_items": 12, "current_label": "Cabras 28/1170"},
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        stale_at = datetime.now(timezone.utc) - timedelta(minutes=45)
        job.started_at = stale_at
        job.updated_at = stale_at
        db.commit()
        job_id = job.id
    finally:
        db.close()

    response = client.get("/elaborazioni/capacitas/involture/particelle/jobs", headers=auth_headers())
    assert response.status_code == 200

    payload = next(item for item in response.json() if item["id"] == job_id)
    assert payload["status"] == "failed"
    assert payload["error_detail"] is not None
    assert "job marcato come failed" in payload["error_detail"].lower()

    db = TestingSessionLocal()
    try:
        refreshed = db.get(CapacitasParticelleSyncJob, job_id)
        assert refreshed is not None
        assert refreshed.status == "failed"
        assert refreshed.completed_at is not None
    finally:
        db.close()


def test_prepare_particelle_sync_jobs_for_recovery_marks_progressive_jobs_as_queued_resume() -> None:
    db = TestingSessionLocal()
    try:
        recoverable = CapacitasParticelleSyncJob(
            requested_by_user_id=1,
            credential_id=None,
            status="processing",
            mode="progressive_catalog",
            payload_json={"only_due": True, "auto_resume": True},
            result_json={"processed_items": 27},
        )
        not_recoverable = CapacitasParticelleSyncJob(
            requested_by_user_id=1,
            credential_id=None,
            status="processing",
            mode="single_particella",
            payload_json={"auto_resume": True},
            result_json={"processed_items": 1},
        )
        db.add(recoverable)
        db.add(not_recoverable)
        db.commit()
        db.refresh(recoverable)
        db.refresh(not_recoverable)

        resumed_ids = prepare_particelle_sync_jobs_for_recovery(db)

        assert resumed_ids == [recoverable.id]
        db.refresh(recoverable)
        db.refresh(not_recoverable)
        assert recoverable.status == "queued_resume"
        assert isinstance(recoverable.result_json, dict)
        assert recoverable.result_json["resume_reason"] == "backend_restart"
        assert recoverable.result_json["resume_count"] == 1
        assert not_recoverable.status == "processing"
    finally:
        db.close()


def test_prepare_anagrafica_history_jobs_for_recovery_marks_jobs_as_queued_resume() -> None:
    db = TestingSessionLocal()
    try:
        recoverable = CapacitasAnagraficaHistoryImportJob(
            requested_by_user_id=1,
            credential_id=None,
            status="processing",
            mode="history_import",
            payload_json={"items": [{"idxana": "IDX-1"}], "auto_resume": True},
            result_json={"processed": 1},
        )
        not_recoverable = CapacitasAnagraficaHistoryImportJob(
            requested_by_user_id=1,
            credential_id=None,
            status="processing",
            mode="history_import",
            payload_json={"items": [{"idxana": "IDX-2"}], "auto_resume": False},
            result_json={"processed": 1},
        )
        db.add(recoverable)
        db.add(not_recoverable)
        db.commit()
        db.refresh(recoverable)
        db.refresh(not_recoverable)

        resumed_ids = prepare_anagrafica_history_jobs_for_recovery(db)

        assert resumed_ids == [recoverable.id]
        db.refresh(recoverable)
        db.refresh(not_recoverable)
        assert recoverable.status == "queued_resume"
        assert isinstance(recoverable.result_json, dict)
        assert recoverable.result_json["resume_reason"] == "backend_restart"
        assert not_recoverable.status == "processing"
    finally:
        db.close()


def test_prepare_terreni_sync_jobs_for_recovery_marks_auto_resume_jobs_as_queued_resume() -> None:
    db = TestingSessionLocal()
    try:
        recoverable = CapacitasTerreniSyncJob(
            requested_by_user_id=1,
            credential_id=None,
            status="processing",
            mode="batch",
            payload_json={
                "items": [{"comune": "Uras", "foglio": "1", "particella": "680"}],
                "auto_resume": True,
            },
            result_json={"processed_items": 3},
        )
        not_recoverable = CapacitasTerreniSyncJob(
            requested_by_user_id=1,
            credential_id=None,
            status="processing",
            mode="batch",
            payload_json={
                "items": [{"comune": "Uras", "foglio": "1", "particella": "681"}],
                "auto_resume": False,
            },
            result_json={"processed_items": 1},
        )
        db.add(recoverable)
        db.add(not_recoverable)
        db.commit()
        db.refresh(recoverable)
        db.refresh(not_recoverable)

        resumed_ids = prepare_terreni_sync_jobs_for_recovery(db)

        assert resumed_ids == [recoverable.id]
        db.refresh(recoverable)
        db.refresh(not_recoverable)
        assert recoverable.status == "queued_resume"
        assert isinstance(recoverable.result_json, dict)
        assert recoverable.result_json["resume_reason"] == "backend_restart"
        assert recoverable.result_json["resume_count"] == 1
        assert not_recoverable.status == "processing"
    finally:
        db.close()


def test_capacitas_terreni_jobs_list_expires_stale_processing_job() -> None:
    db = TestingSessionLocal()
    try:
        job = CapacitasTerreniSyncJob(
            requested_by_user_id=1,
            credential_id=None,
            status="processing",
            mode="batch",
            payload_json={"items": [{"comune": "Uras", "foglio": "1", "particella": "680"}]},
            result_json={"processed_items": 1, "current_label": "Uras 1/680"},
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        stale_at = datetime.now(timezone.utc) - timedelta(minutes=45)
        job.started_at = stale_at
        job.updated_at = stale_at
        db.commit()
        job_id = job.id
    finally:
        db.close()

    response = client.get("/elaborazioni/capacitas/involture/terreni/jobs", headers=auth_headers())
    assert response.status_code == 200

    payload = next(item for item in response.json() if item["id"] == job_id)
    assert payload["status"] == "failed"
    assert payload["error_detail"] is not None
    assert "job marcato come failed" in payload["error_detail"].lower()

    db = TestingSessionLocal()
    try:
        refreshed = db.get(CapacitasTerreniSyncJob, job_id)
        assert refreshed is not None
        assert refreshed.status == "failed"
        assert refreshed.completed_at is not None
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


# ---------------------------------------------------------------------------
# Session-expiry: detection, relogin, and retry logic
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_involture_lookup_raises_session_expired_on_NOSessione_response() -> None:
    import httpx

    from app.modules.elaborazioni.capacitas.apps.involture.client import (
        CapacitasSessionExpiredError,
        InVoltureClient,
    )
    from app.modules.elaborazioni.capacitas.session import CapacitasSession, CapacitasSessionManager

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="NOSessione scaduta")

    transport = httpx.MockTransport(handler)
    manager = CapacitasSessionManager("user", "pass")
    manager._http = httpx.AsyncClient(transport=transport)
    manager._session = CapacitasSession(token="tok-123")

    involture = InVoltureClient(manager)
    with pytest.raises(CapacitasSessionExpiredError, match="scaduta"):
        await involture.search_frazioni("uras")

    await manager.close()


@pytest.mark.anyio
async def test_involture_lookup_raises_session_expired_on_sessione_scaduta_variant() -> None:
    import httpx

    from app.modules.elaborazioni.capacitas.apps.involture.client import (
        CapacitasSessionExpiredError,
        InVoltureClient,
    )
    from app.modules.elaborazioni.capacitas.session import CapacitasSession, CapacitasSessionManager

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="Sessione scaduta per inattività")

    transport = httpx.MockTransport(handler)
    manager = CapacitasSessionManager("user", "pass")
    manager._http = httpx.AsyncClient(transport=transport)
    manager._session = CapacitasSession(token="tok-123")

    involture = InVoltureClient(manager)
    with pytest.raises(CapacitasSessionExpiredError):
        await involture.search_frazioni("uras")

    await manager.close()


@pytest.mark.anyio
async def test_involture_lookup_raises_generic_error_for_unrecognized_non_session_payload() -> None:
    import httpx

    from app.modules.elaborazioni.capacitas.apps.involture.client import (
        CapacitasSessionExpiredError,
        InVoltureClient,
    )
    from app.modules.elaborazioni.capacitas.session import CapacitasSession, CapacitasSessionManager

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="Errore generico del server")

    transport = httpx.MockTransport(handler)
    manager = CapacitasSessionManager("user", "pass")
    manager._http = httpx.AsyncClient(transport=transport)
    manager._session = CapacitasSession(token="tok-123")

    involture = InVoltureClient(manager)
    with pytest.raises(RuntimeError) as exc_info:
        await involture.search_frazioni("uras")
    assert not isinstance(exc_info.value, CapacitasSessionExpiredError)
    assert "payload non riconosciuto" in str(exc_info.value)

    await manager.close()


@pytest.mark.anyio
async def test_involture_client_relogin_calls_login_then_activate_involture() -> None:
    from app.modules.elaborazioni.capacitas.apps.involture.client import InVoltureClient
    from app.modules.elaborazioni.capacitas.session import CapacitasSession, CapacitasSessionManager

    login_calls: list[str] = []
    activate_calls: list[str] = []

    async def fake_login(self) -> CapacitasSession:
        login_calls.append("login")
        self._session = CapacitasSession(token="new-tok")
        return self._session

    async def fake_activate_app(self, app_name: str) -> None:
        activate_calls.append(app_name)

    manager = CapacitasSessionManager("user", "pass")
    manager.login = fake_login.__get__(manager, CapacitasSessionManager)  # type: ignore[method-assign]
    manager.activate_app = fake_activate_app.__get__(manager, CapacitasSessionManager)  # type: ignore[method-assign]

    involture = InVoltureClient(manager)
    await involture.relogin()

    assert login_calls == ["login"]
    assert activate_calls == ["involture"]


@pytest.mark.anyio
async def test_sync_particella_item_retries_once_after_session_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    from uuid import uuid4

    from app.modules.elaborazioni.capacitas.apps.involture.client import (
        CapacitasSessionExpiredError,
        InVoltureClient,
    )
    from app.modules.elaborazioni.capacitas.models import CapacitasParticelleSyncJobCreateRequest
    from app.services.elaborazioni_capacitas_particelle_sync import (
        ParticellaSyncItem,
        _sync_particella_item,
    )
    from app.modules.elaborazioni.capacitas.models import (
        CapacitasTerreniBatchItemResult,
        CapacitasTerreniBatchResponse,
    )

    call_count = 0
    relogin_calls: list[int] = []

    async def fake_sync_terreni_batch(db, client, request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise CapacitasSessionExpiredError("NOSessione scaduta")
        return CapacitasTerreniBatchResponse(
            processed_items=1,
            imported_rows=1,
            failed_items=0,
            total_rows=1,
            linked_units=0,
            linked_occupancies=0,
            imported_certificati=0,
            imported_details=0,
            items=[
                CapacitasTerreniBatchItemResult(
                    ok=True,
                    label="Uras 1/680",
                    search_key="Uras/1/680",
                    total_rows=1,
                    imported_rows=1,
                    imported_certificati=0,
                    imported_details=0,
                )
            ],
        )

    async def fake_relogin(self) -> None:
        relogin_calls.append(1)

    monkeypatch.setattr(
        "app.services.elaborazioni_capacitas_particelle_sync.sync_terreni_batch",
        fake_sync_terreni_batch,
    )

    db = TestingSessionLocal()
    try:
        from sqlalchemy import select as sa_select
        particella = db.scalar(sa_select(CatParticella).where(CatParticella.foglio == "1", CatParticella.particella == "680"))
        assert particella is not None

        job = CapacitasParticelleSyncJob(
            requested_by_user_id=1,
            credential_id=None,
            status="processing",
            mode="progressive_catalog",
            payload_json={"only_due": True},
            result_json={"processed_items": 0},
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        manager_stub = type("M", (), {})()
        involture = InVoltureClient.__new__(InVoltureClient)
        involture._manager = manager_stub  # type: ignore[attr-defined]
        involture.relogin = fake_relogin.__get__(involture, InVoltureClient)  # type: ignore[method-assign]

        item = ParticellaSyncItem(
            index=1,
            particella_id=particella.id,
            label="Uras 1/680",
            comune_label="Uras",
            sezione="",
            foglio="1",
            particella="680",
            sub="",
        )

        payload = CapacitasParticelleSyncJobCreateRequest(
            only_due=False,
            fetch_certificati=False,
            fetch_details=False,
        )

        result = await _sync_particella_item(
            db, involture, job_id=job.id, credential_id=None, payload=payload, item=item
        )

        assert result["status"] == "synced", f"expected synced, got {result}"
        assert call_count == 2, "sync_terreni_batch deve essere chiamato due volte"
        assert len(relogin_calls) == 1, "relogin deve essere chiamato esattamente una volta"
    finally:
        db.close()


@pytest.mark.anyio
async def test_sync_particella_item_marks_failed_if_retry_also_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.modules.elaborazioni.capacitas.apps.involture.client import (
        CapacitasSessionExpiredError,
        InVoltureClient,
    )
    from app.modules.elaborazioni.capacitas.models import CapacitasParticelleSyncJobCreateRequest
    from app.services.elaborazioni_capacitas_particelle_sync import (
        ParticellaSyncItem,
        _sync_particella_item,
    )

    relogin_calls: list[int] = []

    async def fake_sync_terreni_batch_always_fails(db, client, request):
        raise CapacitasSessionExpiredError("NOSessione scaduta")

    async def fake_relogin(self) -> None:
        relogin_calls.append(1)

    monkeypatch.setattr(
        "app.services.elaborazioni_capacitas_particelle_sync.sync_terreni_batch",
        fake_sync_terreni_batch_always_fails,
    )

    db = TestingSessionLocal()
    try:
        from sqlalchemy import select as sa_select
        particella = db.scalar(sa_select(CatParticella).where(CatParticella.foglio == "1", CatParticella.particella == "680"))
        assert particella is not None

        job = CapacitasParticelleSyncJob(
            requested_by_user_id=1,
            credential_id=None,
            status="processing",
            mode="progressive_catalog",
            payload_json={"only_due": True},
            result_json={"processed_items": 0},
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        involture = InVoltureClient.__new__(InVoltureClient)
        involture._manager = type("M", (), {})()  # type: ignore[attr-defined]
        involture.relogin = fake_relogin.__get__(involture, InVoltureClient)  # type: ignore[method-assign]

        item = ParticellaSyncItem(
            index=1,
            particella_id=particella.id,
            label="Uras 1/680",
            comune_label="Uras",
            sezione="",
            foglio="1",
            particella="680",
            sub="",
        )

        payload = CapacitasParticelleSyncJobCreateRequest(only_due=False, fetch_certificati=False, fetch_details=False)

        result = await _sync_particella_item(
            db, involture, job_id=job.id, credential_id=None, payload=payload, item=item
        )

        assert result["status"] == "failed"
        assert "scaduta" in result["message"].lower() or "NOSessione" in result["message"]
        assert len(relogin_calls) == 1, "relogin deve essere tentato anche quando il retry fallisce"
    finally:
        db.close()


@pytest.mark.anyio
async def test_run_particelle_sync_job_sequential_relogins_and_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.modules.elaborazioni.capacitas.apps.involture.client import (
        CapacitasSessionExpiredError,
        InVoltureClient,
    )
    from app.models.capacitas import CapacitasParticelleSyncJob
    from app.modules.elaborazioni.capacitas.models import CapacitasParticelleSyncJobCreateRequest
    from app.modules.elaborazioni.capacitas.models import (
        CapacitasTerreniBatchItemResult,
        CapacitasTerreniBatchResponse,
    )
    from app.services.elaborazioni_capacitas_particelle_sync import run_particelle_sync_job

    call_count = 0
    relogin_calls: list[int] = []

    async def fake_sync_terreni_batch(db, client, request, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise CapacitasSessionExpiredError("NOSessione scaduta")
        return CapacitasTerreniBatchResponse(
            processed_items=1,
            imported_rows=1,
            failed_items=0,
            total_rows=1,
            linked_units=0,
            linked_occupancies=0,
            imported_certificati=0,
            imported_details=0,
            items=[
                CapacitasTerreniBatchItemResult(
                    ok=True,
                    label="Uras 1/680",
                    search_key="Uras/1/680",
                    total_rows=1,
                    imported_rows=1,
                    imported_certificati=0,
                    imported_details=0,
                )
            ],
        )

    async def fake_relogin(self) -> None:
        relogin_calls.append(1)

    monkeypatch.setattr(
        "app.services.elaborazioni_capacitas_particelle_sync.sync_terreni_batch",
        fake_sync_terreni_batch,
    )

    db = TestingSessionLocal()
    try:
        # limit=1 so exactly one particella is processed: 1 expiry + 1 retry = 2 calls total
        job = CapacitasParticelleSyncJob(
            requested_by_user_id=1,
            credential_id=None,
            status="pending",
            mode="progressive_catalog",
            payload_json={"only_due": False, "limit": 1, "fetch_certificati": False, "fetch_details": False},
            result_json=None,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        involture = InVoltureClient.__new__(InVoltureClient)
        involture._manager = type("M", (), {})()  # type: ignore[attr-defined]
        involture.relogin = fake_relogin.__get__(involture, InVoltureClient)  # type: ignore[method-assign]

        completed_job = await run_particelle_sync_job(db, involture, job)

        assert completed_job.status in {"succeeded", "completed_with_errors"}, completed_job.status
        assert call_count == 2, f"sync_terreni_batch chiamato {call_count} volte invece di 2 (expiry + retry)"
        assert len(relogin_calls) == 1, f"relogin chiamato {len(relogin_calls)} volte invece di 1"
        result = completed_job.result_json
        assert isinstance(result, dict)
        assert result.get("success_items", 0) >= 1
    finally:
        db.close()


@pytest.mark.anyio
async def test_run_particelle_sync_job_sequential_marks_failed_after_double_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.modules.elaborazioni.capacitas.apps.involture.client import (
        CapacitasSessionExpiredError,
        InVoltureClient,
    )
    from app.models.capacitas import CapacitasParticelleSyncJob
    from app.services.elaborazioni_capacitas_particelle_sync import run_particelle_sync_job

    relogin_calls: list[int] = []

    async def fake_sync_terreni_batch_always_fails(db, client, request, **kwargs):
        raise CapacitasSessionExpiredError("NOSessione scaduta")

    async def fake_relogin(self) -> None:
        relogin_calls.append(1)

    monkeypatch.setattr(
        "app.services.elaborazioni_capacitas_particelle_sync.sync_terreni_batch",
        fake_sync_terreni_batch_always_fails,
    )

    db = TestingSessionLocal()
    try:
        job = CapacitasParticelleSyncJob(
            requested_by_user_id=1,
            credential_id=None,
            status="pending",
            mode="progressive_catalog",
            payload_json={"only_due": False, "limit": 1, "fetch_certificati": False, "fetch_details": False},
            result_json=None,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        involture = InVoltureClient.__new__(InVoltureClient)
        involture._manager = type("M", (), {})()  # type: ignore[attr-defined]
        involture.relogin = fake_relogin.__get__(involture, InVoltureClient)  # type: ignore[method-assign]

        completed_job = await run_particelle_sync_job(db, involture, job)

        assert completed_job.status == "completed_with_errors", completed_job.status
        result = completed_job.result_json
        assert isinstance(result, dict)
        assert result.get("failed_items", 0) >= 1
        assert len(relogin_calls) == 1, "relogin deve essere tentato esattamente una volta (non in loop)"
        recent = result.get("recent_items", [])
        assert any(
            "scaduta" in (item.get("message") or "").lower() or "NOSessione" in (item.get("message") or "")
            for item in recent
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Speed patch: PATCH /involture/particelle/jobs/{id}/speed
# ---------------------------------------------------------------------------


def test_patch_particelle_job_speed_updates_throttle_to_double() -> None:
    from app.services.elaborazioni_capacitas_particelle_sync import DAY_THROTTLE_MS, DOUBLE_SPEED_MULTIPLIER

    db = TestingSessionLocal()
    try:
        job = CapacitasParticelleSyncJob(
            requested_by_user_id=1,
            credential_id=None,
            status="processing",
            mode="progressive_catalog",
            payload_json={"only_due": False, "double_speed": False},
            result_json={"throttle_ms": DAY_THROTTLE_MS, "speed_multiplier": 1, "processed_items": 5},
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id
    finally:
        db.close()

    response = client.patch(
        f"/elaborazioni/capacitas/involture/particelle/jobs/{job_id}/speed",
        headers=auth_headers(),
        json={"double_speed": True},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    result = payload["result_json"]
    assert result["speed_multiplier"] == DOUBLE_SPEED_MULTIPLIER
    assert result["throttle_ms"] < DAY_THROTTLE_MS

    db = TestingSessionLocal()
    try:
        refreshed = db.get(CapacitasParticelleSyncJob, job_id)
        assert refreshed is not None
        assert isinstance(refreshed.result_json, dict)
        assert refreshed.result_json["speed_multiplier"] == DOUBLE_SPEED_MULTIPLIER
        assert isinstance(refreshed.payload_json, dict)
        assert refreshed.payload_json["double_speed"] is True
    finally:
        db.close()


def test_patch_particelle_job_speed_resets_to_standard() -> None:
    from app.services.elaborazioni_capacitas_particelle_sync import DAY_THROTTLE_MS, DOUBLE_SPEED_MULTIPLIER, MIN_THROTTLE_MS

    db = TestingSessionLocal()
    try:
        fast_throttle = max(MIN_THROTTLE_MS, DAY_THROTTLE_MS // DOUBLE_SPEED_MULTIPLIER)
        job = CapacitasParticelleSyncJob(
            requested_by_user_id=1,
            credential_id=None,
            status="processing",
            mode="progressive_catalog",
            payload_json={"only_due": False, "double_speed": True},
            result_json={"throttle_ms": fast_throttle, "speed_multiplier": DOUBLE_SPEED_MULTIPLIER, "processed_items": 10},
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id
    finally:
        db.close()

    response = client.patch(
        f"/elaborazioni/capacitas/involture/particelle/jobs/{job_id}/speed",
        headers=auth_headers(),
        json={"double_speed": False},
    )

    assert response.status_code == 200, response.text
    result = response.json()["result_json"]
    assert result["speed_multiplier"] == 1
    assert result["throttle_ms"] >= DAY_THROTTLE_MS // 2


def test_patch_particelle_job_speed_rejects_terminal_job() -> None:
    db = TestingSessionLocal()
    try:
        job = CapacitasParticelleSyncJob(
            requested_by_user_id=1,
            credential_id=None,
            status="succeeded",
            mode="progressive_catalog",
            payload_json={"only_due": False},
            result_json={"throttle_ms": 900, "speed_multiplier": 1},
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id
    finally:
        db.close()

    response = client.patch(
        f"/elaborazioni/capacitas/involture/particelle/jobs/{job_id}/speed",
        headers=auth_headers(),
        json={"double_speed": True},
    )

    assert response.status_code == 409


def test_patch_particelle_job_speed_returns_404_for_missing_job() -> None:
    response = client.patch(
        "/elaborazioni/capacitas/involture/particelle/jobs/999999/speed",
        headers=auth_headers(),
        json={"double_speed": True},
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_run_particelle_sync_job_picks_up_live_throttle_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Worker uses throttle_ms from result_json, so a live PATCH is picked up at next step."""
    from app.modules.elaborazioni.capacitas.apps.involture.client import InVoltureClient
    from app.models.capacitas import CapacitasParticelleSyncJob
    from app.modules.elaborazioni.capacitas.models import (
        CapacitasTerreniBatchItemResult,
        CapacitasTerreniBatchResponse,
    )
    from app.services.elaborazioni_capacitas_particelle_sync import run_particelle_sync_job

    sleeps_used: list[float] = []
    original_sleep = __import__("asyncio").sleep

    async def recording_sleep(delay: float) -> None:
        sleeps_used.append(delay)
        await original_sleep(0)

    monkeypatch.setattr("asyncio.sleep", recording_sleep)

    async def fake_sync_terreni_batch(db, client_arg, request, **kwargs):
        return CapacitasTerreniBatchResponse(
            processed_items=1,
            imported_rows=1,
            failed_items=0,
            total_rows=1,
            linked_units=0,
            linked_occupancies=0,
            imported_certificati=0,
            imported_details=0,
            items=[
                CapacitasTerreniBatchItemResult(
                    ok=True,
                    label="Uras 1/680",
                    search_key="Uras/1/680",
                    total_rows=1,
                    imported_rows=1,
                    imported_certificati=0,
                    imported_details=0,
                )
            ],
        )

    monkeypatch.setattr(
        "app.services.elaborazioni_capacitas_particelle_sync.sync_terreni_batch",
        fake_sync_terreni_batch,
    )

    db = TestingSessionLocal()
    try:
        # Pre-write 450ms (double-speed) in result_json to simulate a PATCH applied mid-run
        OVERRIDDEN_THROTTLE_MS = 450
        job = CapacitasParticelleSyncJob(
            requested_by_user_id=1,
            credential_id=None,
            status="pending",
            mode="progressive_catalog",
            payload_json={"only_due": False, "limit": 2, "fetch_certificati": False, "fetch_details": False},
            result_json={"throttle_ms": OVERRIDDEN_THROTTLE_MS, "speed_multiplier": 2},
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        involture = InVoltureClient.__new__(InVoltureClient)
        involture._manager = type("M", (), {})()  # type: ignore[attr-defined]

        await run_particelle_sync_job(db, involture, job)

        assert sleeps_used, "nessun sleep registrato tra i due item"
        assert abs(sleeps_used[-1] - OVERRIDDEN_THROTTLE_MS / 1000) < 0.01, (
            f"throttle atteso {OVERRIDDEN_THROTTLE_MS / 1000}s, usato {sleeps_used[-1]}s"
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Tests Bug Fix 1: _find_utenza_for_terreno_row anno fallback
# ---------------------------------------------------------------------------

class TestFindUtenzaForTerrenoRowAnnoFallback:
    """Verifica che _find_utenza_for_terreno_row usi il fallback anno quando
    l'anno della riga Capacitas non corrisponde a nessun anno_campagna in DB."""

    def _make_row(self, **kwargs):
        from app.modules.elaborazioni.capacitas.models import CapacitasTerrenoRow
        defaults = dict(cco="0A1462373", com="95", fra="38", foglio="24", particella="3", sub=None, anno="2024")
        defaults.update(kwargs)
        return CapacitasTerrenoRow.model_construct(**defaults)

    def _make_utenza(self, db: Session, *, anno: int, sub: str | None = None, cco: str = "0A1462373") -> CatUtenzaIrrigua:
        batch = db.query(CatImportBatch).first()
        utenza = CatUtenzaIrrigua(
            import_batch_id=batch.id if batch else None,
            anno_campagna=anno,
            cco=cco,
            cod_comune_capacitas=95,
            cod_frazione=38,
            foglio="24",
            particella="3",
            subalterno=sub,
        )
        db.add(utenza)
        db.flush()
        return utenza

    def test_exact_anno_match_returns_utenza(self) -> None:
        from app.services.elaborazioni_capacitas_terreni import _find_utenza_for_terreno_row
        db = TestingSessionLocal()
        try:
            utenza = self._make_utenza(db, anno=2024)
            row = self._make_row(anno="2024")
            result = _find_utenza_for_terreno_row(db, row)
            assert result is not None
            assert result.id == utenza.id
        finally:
            db.rollback()
            db.close()

    def test_anno_mismatch_falls_back_to_most_recent(self) -> None:
        from app.services.elaborazioni_capacitas_terreni import _find_utenza_for_terreno_row
        db = TestingSessionLocal()
        try:
            self._make_utenza(db, anno=2023)
            utenza_2025 = self._make_utenza(db, anno=2025)
            # row.anno=2024 non esiste a DB, deve restituire l'anno più recente (2025)
            row = self._make_row(anno="2024")
            result = _find_utenza_for_terreno_row(db, row)
            assert result is not None
            assert result.id == utenza_2025.id
        finally:
            db.rollback()
            db.close()

    def test_no_cco_returns_none(self) -> None:
        from app.services.elaborazioni_capacitas_terreni import _find_utenza_for_terreno_row
        db = TestingSessionLocal()
        try:
            row = self._make_row(cco=None)
            assert _find_utenza_for_terreno_row(db, row) is None
        finally:
            db.rollback()
            db.close()

    def test_cco_not_in_db_returns_none(self) -> None:
        from app.services.elaborazioni_capacitas_terreni import _find_utenza_for_terreno_row
        db = TestingSessionLocal()
        try:
            row = self._make_row(cco="XXXXXXXX", anno="2024")
            assert _find_utenza_for_terreno_row(db, row) is None
        finally:
            db.rollback()
            db.close()

    def test_missing_comune_returns_none_even_if_cco_exists(self) -> None:
        from app.services.elaborazioni_capacitas_terreni import _find_utenza_for_terreno_row
        db = TestingSessionLocal()
        try:
            self._make_utenza(db, anno=2024)
            row = self._make_row(com=None, anno="2024")
            assert _find_utenza_for_terreno_row(db, row) is None
        finally:
            db.rollback()
            db.close()

    def test_sub_filter_respected_in_fallback(self) -> None:
        from app.services.elaborazioni_capacitas_terreni import _find_utenza_for_terreno_row
        db = TestingSessionLocal()
        try:
            self._make_utenza(db, anno=2025, sub="b")   # sub diverso
            utenza_a = self._make_utenza(db, anno=2025, sub="a")
            # row chiede sub "a", anno=2024 (mismatch) → fallback su utenza sub a
            row = self._make_row(anno="2024", sub="a")
            result = _find_utenza_for_terreno_row(db, row)
            assert result is not None
            assert result.id == utenza_a.id
        finally:
            db.rollback()
            db.close()

    def test_same_cco_different_comuni_does_not_match_wrong_comune(self) -> None:
        from app.services.elaborazioni_capacitas_terreni import _find_utenza_for_terreno_row
        db = TestingSessionLocal()
        try:
            batch = db.query(CatImportBatch).first()
            assert batch is not None
            wrong = CatUtenzaIrrigua(
                import_batch_id=batch.id,
                anno_campagna=2024,
                cco="0A1462373",
                cod_comune_capacitas=165,
                cod_frazione=38,
                foglio="24",
                particella="3",
            )
            correct = CatUtenzaIrrigua(
                import_batch_id=batch.id,
                anno_campagna=2024,
                cco="0A1462373",
                cod_comune_capacitas=95,
                cod_frazione=38,
                foglio="24",
                particella="3",
            )
            db.add_all([wrong, correct])
            db.flush()

            row = self._make_row(com="95", anno="2024")
            result = _find_utenza_for_terreno_row(db, row)
            assert result is not None
            assert result.id == correct.id
        finally:
            db.rollback()
            db.close()


# ---------------------------------------------------------------------------
# Tests Bug Fix 2: refetch_certificati_senza_intestatari
# ---------------------------------------------------------------------------

def _make_cert_for_refetch(
    db: Session, *, cco: str = "0A1462373", has_intestatario: bool = False
) -> CatCapacitasCertificato:
    cert = CatCapacitasCertificato(
        cco=cco,
        fra="38",
        ccs="03",
        pvc="001",
        com="95",
        collected_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    db.add(cert)
    db.flush()
    if has_intestatario:
        db.add(CatCapacitasIntestatario(
            certificato_id=cert.id,
            denominazione="Mario Rossi",
            collected_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ))
        db.flush()
    return cert


@pytest.mark.anyio
async def test_refetch_certificati_richiama_sync_per_cert_senza_intestatari(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.elaborazioni_capacitas_terreni import refetch_certificati_senza_intestatari
    from app.modules.elaborazioni.capacitas.models import CapacitasTerrenoCertificato

    db = TestingSessionLocal()
    called_ccos: list[str] = []

    async def fake_sync_snapshot(db, client, *, cco, com, pvc, fra, ccs, **kwargs):
        called_ccos.append(cco)
        snap = CatCapacitasCertificato(
            cco=cco, fra=fra, ccs=ccs, pvc=pvc, com=com,
            collected_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        db.add(snap)
        db.flush()
        return CapacitasTerrenoCertificato(cco=cco, fra=fra, ccs=ccs, pvc=pvc, com=com), snap

    monkeypatch.setattr(
        "app.services.elaborazioni_capacitas_terreni.sync_certificato_snapshot",
        fake_sync_snapshot,
    )

    try:
        _make_cert_for_refetch(db, cco="0A1462373", has_intestatario=False)
        _make_cert_for_refetch(db, cco="0A1031735", has_intestatario=True)  # deve essere saltato
        db.commit()

        count = await refetch_certificati_senza_intestatari(db, None, limit=10)  # type: ignore[arg-type]

        assert count == 1
        assert called_ccos == ["0A1462373"]
    finally:
        db.rollback()
        db.close()


@pytest.mark.anyio
async def test_refetch_certificati_filters_target_utenza_by_comune_and_frazione(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.elaborazioni_capacitas_terreni import refetch_certificati_senza_intestatari
    from app.modules.elaborazioni.capacitas.models import CapacitasTerrenoCertificato

    db = TestingSessionLocal()
    captured_target_utenze_ids: list[uuid.UUID] = []

    async def fake_sync_snapshot(db, client, *, cco, com, pvc, fra, ccs, target_utenze=None, **kwargs):
        if target_utenze:
            captured_target_utenze_ids.extend(item.id for item in target_utenze)
        snap = CatCapacitasCertificato(
            cco=cco,
            fra=fra,
            ccs=ccs,
            pvc=pvc,
            com=com,
            collected_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        db.add(snap)
        db.flush()
        return CapacitasTerrenoCertificato(cco=cco, fra=fra, ccs=ccs, pvc=pvc, com=com), snap

    monkeypatch.setattr(
        "app.services.elaborazioni_capacitas_terreni.sync_certificato_snapshot",
        fake_sync_snapshot,
    )

    try:
        batch = db.query(CatImportBatch).first()
        assert batch is not None
        matching = CatUtenzaIrrigua(
            import_batch_id=batch.id,
            anno_campagna=2025,
            cco="0A1462373",
            cod_comune_capacitas=95,
            cod_frazione=38,
            foglio="24",
            particella="3",
        )
        wrong = CatUtenzaIrrigua(
            import_batch_id=batch.id,
            anno_campagna=2025,
            cco="0A1462373",
            cod_comune_capacitas=165,
            cod_frazione=31,
            foglio="24",
            particella="3",
        )
        db.add_all([matching, wrong])
        db.flush()

        _make_cert_for_refetch(db, cco="0A1462373", has_intestatario=False)
        cert = db.query(CatCapacitasCertificato).filter(CatCapacitasCertificato.cco == "0A1462373").one()
        cert.com = "95"
        cert.fra = "38"
        cert.pvc = "097"
        cert.ccs = "00000"
        db.commit()

        count = await refetch_certificati_senza_intestatari(db, None, limit=10)  # type: ignore[arg-type]

        assert count == 1
        assert captured_target_utenze_ids == [matching.id]
    finally:
        db.rollback()
        db.close()


def test_find_utenze_for_cert_context_requires_comune() -> None:
    from app.services.elaborazioni_capacitas_terreni import _find_utenze_for_cert_context

    db = TestingSessionLocal()
    try:
        batch = db.query(CatImportBatch).first()
        assert batch is not None
        db.add(
            CatUtenzaIrrigua(
                import_batch_id=batch.id,
                anno_campagna=2025,
                cco="0A1462373",
                cod_comune_capacitas=95,
                cod_frazione=38,
                foglio="24",
                particella="3",
            )
        )
        db.flush()

        assert _find_utenze_for_cert_context(db, cco="0A1462373", com=None, fra="38") == []
        assert _find_utenze_for_cert_context(db, cco="0A1462373", com="", fra="38") == []
    finally:
        db.rollback()
        db.close()


@pytest.mark.anyio
async def test_refetch_certificati_zero_se_tutti_hanno_intestatari(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.elaborazioni_capacitas_terreni import refetch_certificati_senza_intestatari

    db = TestingSessionLocal()
    sync_called = False

    async def fake_sync_snapshot(db, client, **kwargs):
        nonlocal sync_called
        sync_called = True

    monkeypatch.setattr(
        "app.services.elaborazioni_capacitas_terreni.sync_certificato_snapshot",
        fake_sync_snapshot,
    )

    try:
        _make_cert_for_refetch(db, cco="0A9999999", has_intestatario=True)
        db.commit()

        count = await refetch_certificati_senza_intestatari(db, None)  # type: ignore[arg-type]

        assert count == 0
        assert not sync_called
    finally:
        db.rollback()
        db.close()


@pytest.mark.anyio
async def test_refetch_certificati_gestisce_eccezioni_senza_propagare(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.elaborazioni_capacitas_terreni import refetch_certificati_senza_intestatari

    db = TestingSessionLocal()

    async def fake_sync_snapshot(db, client, **kwargs):
        raise RuntimeError("Capacitas error")

    monkeypatch.setattr(
        "app.services.elaborazioni_capacitas_terreni.sync_certificato_snapshot",
        fake_sync_snapshot,
    )

    try:
        _make_cert_for_refetch(db, cco="0A1111111", has_intestatario=False)
        db.commit()

        count = await refetch_certificati_senza_intestatari(db, None)  # type: ignore[arg-type]

        assert count == 0  # errore gestito, non propagato
    finally:
        db.rollback()
        db.close()


# ---------------------------------------------------------------------------
# Tests: CapacitasFrazioneAmbiguaError e rilevamento anomalia frazione
# ---------------------------------------------------------------------------


def _make_search_result(rows):
    """Costruisce un CapacitasTerreniSearchResult con le righe fornite."""
    return CapacitasTerreniSearchResult(total=len(rows), rows=rows)


def _make_terreno_row(**kwargs):
    from app.modules.elaborazioni.capacitas.models import CapacitasTerrenoRow
    defaults = dict(
        id="1", pvc="001", com="200", cco="004000308", fra="11",
        ccs="0", foglio="8", particella="48", sub="", anno="2022",
        voltura="", opcode="", data_reg="", bac_descr="",
        row_visual_state="current_black", superficie=None, ta_ext=None,
    )
    defaults.update(kwargs)
    return CapacitasTerrenoRow.model_construct(**defaults)


@pytest.mark.anyio
async def test_probe_frazioni_returns_only_frazioni_with_results(monkeypatch: pytest.MonkeyPatch) -> None:
    """_probe_frazioni_for_item restituisce solo le frazioni che hanno righe."""
    from app.modules.elaborazioni.capacitas.models import CapacitasTerreniBatchItem
    from app.services.elaborazioni_capacitas_terreni import _probe_frazioni_for_item

    search_calls: list[str] = []

    async def fake_search_terreni(self, req):
        search_calls.append(req.frazione_id)
        if req.frazione_id == "11":
            return _make_search_result([_make_terreno_row()])
        return _make_search_result([])

    from app.modules.elaborazioni.capacitas.apps.involture.client import InVoltureClient
    monkeypatch.setattr(InVoltureClient, "search_terreni", fake_search_terreni)

    client = InVoltureClient.__new__(InVoltureClient)
    item = CapacitasTerreniBatchItem(foglio="8", particella="48", comune="Oristano")

    hits = await _probe_frazioni_for_item(client, item, ["04", "05", "11", "18"])

    assert len(hits) == 1
    assert hits[0]["frazione_id"] == "11"
    assert hits[0]["n_rows"] == 1
    assert set(search_calls) == {"04", "05", "11", "18"}


@pytest.mark.anyio
async def test_probe_frazioni_ignora_eccezioni_singola_frazione(monkeypatch: pytest.MonkeyPatch) -> None:
    """_probe_frazioni_for_item non propaga eccezioni su singole frazioni."""
    from app.modules.elaborazioni.capacitas.models import CapacitasTerreniBatchItem
    from app.services.elaborazioni_capacitas_terreni import _probe_frazioni_for_item

    async def fake_search_terreni(self, req):
        if req.frazione_id == "04":
            raise RuntimeError("timeout")
        return _make_search_result([_make_terreno_row()])

    from app.modules.elaborazioni.capacitas.apps.involture.client import InVoltureClient
    monkeypatch.setattr(InVoltureClient, "search_terreni", fake_search_terreni)

    client = InVoltureClient.__new__(InVoltureClient)
    item = CapacitasTerreniBatchItem(foglio="8", particella="48", comune="Oristano")

    hits = await _probe_frazioni_for_item(client, item, ["04", "11"])

    assert len(hits) == 1
    assert hits[0]["frazione_id"] == "11"


@pytest.mark.anyio
async def test_sync_batch_item_raises_frazione_ambigua_when_multiple_frazioni_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_sync_batch_item_with_candidates alza CapacitasFrazioneAmbiguaError se
    più di una frazione restituisce risultati."""
    from app.modules.elaborazioni.capacitas.apps.involture.client import InVoltureClient
    from app.modules.elaborazioni.capacitas.models import (
        CapacitasTerreniBatchItem,
        CapacitasTerreniBatchRequest,
    )
    from app.services.elaborazioni_capacitas_terreni import (
        CapacitasFrazioneAmbiguaError,
        _sync_batch_item_with_candidates,
    )

    async def fake_search_terreni(self, req):
        return _make_search_result([_make_terreno_row(fra=req.frazione_id)])

    monkeypatch.setattr(InVoltureClient, "search_terreni", fake_search_terreni)
    client = InVoltureClient.__new__(InVoltureClient)

    db = TestingSessionLocal()
    try:
        item = CapacitasTerreniBatchItem(foglio="8", particella="48", comune="Oristano")
        batch_req = CapacitasTerreniBatchRequest(
            items=[item], credential_id=None, fetch_certificati=False, fetch_details=False
        )

        with pytest.raises(CapacitasFrazioneAmbiguaError) as exc_info:
            await _sync_batch_item_with_candidates(db, client, batch_req, item, ["04", "11"])

        err = exc_info.value
        assert len(err.candidates) == 2
        assert {c["frazione_id"] for c in err.candidates} == {"04", "11"}
    finally:
        db.close()


@pytest.mark.anyio
async def test_sync_batch_item_proceeds_when_single_frazione_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_sync_batch_item_with_candidates procede normalmente se una sola frazione ha risultati."""
    from app.modules.elaborazioni.capacitas.apps.involture.client import InVoltureClient
    from app.modules.elaborazioni.capacitas.models import (
        CapacitasTerreniBatchItem,
        CapacitasTerreniBatchRequest,
        CapacitasTerreniSyncResponse,
    )
    from app.services.elaborazioni_capacitas_terreni import _sync_batch_item_with_candidates

    async def fake_search_terreni(self, req):
        if req.frazione_id == "11":
            return _make_search_result([_make_terreno_row()])
        return _make_search_result([])

    sync_called_with: list[str] = []

    async def fake_sync_for_request(db, client, req, **kwargs):
        sync_called_with.append(req.frazione_id)
        return CapacitasTerreniSyncResponse(
            search_key="test", total_rows=1, imported_rows=1,
            imported_certificati=0, imported_details=0, linked_units=0, linked_occupancies=0,
        )

    monkeypatch.setattr(InVoltureClient, "search_terreni", fake_search_terreni)
    monkeypatch.setattr(
        "app.services.elaborazioni_capacitas_terreni.sync_terreni_for_request",
        fake_sync_for_request,
    )
    client = InVoltureClient.__new__(InVoltureClient)

    db = TestingSessionLocal()
    try:
        item = CapacitasTerreniBatchItem(foglio="8", particella="48", comune="Oristano")
        batch_req = CapacitasTerreniBatchRequest(
            items=[item], credential_id=None, fetch_certificati=False, fetch_details=False
        )

        result = await _sync_batch_item_with_candidates(db, client, batch_req, item, ["04", "11"])

        assert result.total_rows == 1
        assert sync_called_with == ["11"], "deve usare solo la frazione con risultati"
    finally:
        db.close()


@pytest.mark.anyio
async def test_sync_particella_item_marks_anomalia_on_frazione_ambigua(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_sync_particella_item salva capacitas_anomaly_type='frazione_ambigua' quando
    sync_terreni_batch alza CapacitasFrazioneAmbiguaError."""
    from sqlalchemy import select as sa_select

    from app.modules.elaborazioni.capacitas.apps.involture.client import InVoltureClient
    from app.modules.elaborazioni.capacitas.models import CapacitasParticelleSyncJobCreateRequest
    from app.services.elaborazioni_capacitas_particelle_sync import (
        ParticellaSyncItem,
        _sync_particella_item,
    )
    from app.services.elaborazioni_capacitas_terreni import CapacitasFrazioneAmbiguaError

    candidates = [
        {"frazione_id": "04", "n_rows": 5, "ccos": ["004000308"], "stati": ["historic_marker"]},
        {"frazione_id": "11", "n_rows": 3, "ccos": ["0A0436904"], "stati": ["current_black"]},
    ]

    async def fake_sync_terreni_batch(db, client, request):
        raise CapacitasFrazioneAmbiguaError(
            "Particella 8/48 trovata in 2 frazioni", candidates=candidates
        )

    monkeypatch.setattr(
        "app.services.elaborazioni_capacitas_particelle_sync.sync_terreni_batch",
        fake_sync_terreni_batch,
    )

    db = TestingSessionLocal()
    try:
        particella = db.scalar(
            sa_select(CatParticella).where(CatParticella.foglio == "1", CatParticella.particella == "680")
        )
        assert particella is not None

        job = CapacitasParticelleSyncJob(
            requested_by_user_id=1,
            credential_id=None,
            status="processing",
            mode="progressive_catalog",
            payload_json={"only_due": True},
            result_json={"processed_items": 0},
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        client_stub = InVoltureClient.__new__(InVoltureClient)
        item = ParticellaSyncItem(
            index=0,
            particella_id=particella.id,
            label="Oristano 8/48",
            comune_label="Oristano",
            sezione="",
            foglio="8",
            particella="48",
            sub="",
        )
        payload = CapacitasParticelleSyncJobCreateRequest(
            only_due=False, fetch_certificati=False, fetch_details=False
        )

        result = await _sync_particella_item(
            db, client_stub, job_id=job.id, credential_id=None, payload=payload, item=item
        )

        assert result["status"] == "anomalia"
        db.refresh(particella)
        assert particella.capacitas_last_sync_status == "anomalia"
        assert particella.capacitas_anomaly_type == "frazione_ambigua"
        assert particella.capacitas_anomaly_data is not None
        assert len(particella.capacitas_anomaly_data["candidates"]) == 2
    finally:
        db.rollback()
        db.close()


def test_list_particelle_anomalie_returns_only_anomalous(monkeypatch: pytest.MonkeyPatch) -> None:
    """GET /involture/particelle/anomalie restituisce solo le particelle con anomalia."""
    import json
    from sqlalchemy import select as sa_select

    db = TestingSessionLocal()
    try:
        particella = db.scalar(
            sa_select(CatParticella).where(CatParticella.foglio == "1", CatParticella.particella == "680")
        )
        assert particella is not None
        particella.capacitas_anomaly_type = "frazione_ambigua"
        particella.capacitas_anomaly_data = {
            "candidates": [
                {"frazione_id": "04", "n_rows": 5, "ccos": ["004000308"], "stati": ["historic_marker"]},
                {"frazione_id": "11", "n_rows": 3, "ccos": ["0A0436904"], "stati": ["current_black"]},
            ]
        }
        db.commit()
    finally:
        db.close()

    response = client.get(
        "/elaborazioni/capacitas/involture/particelle/anomalie",
        headers={"Authorization": "Bearer " + _get_admin_token()},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["anomaly_type"] == "frazione_ambigua"
    assert len(data[0]["candidates"]) == 2


def _get_admin_token() -> str:
    resp = client.post("/auth/login", json={"username": "elaborazioni-admin", "password": "secret123"})
    return resp.json()["access_token"]
