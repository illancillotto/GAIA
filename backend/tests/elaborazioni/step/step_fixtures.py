from __future__ import annotations

import hashlib
import io
import json
import uuid
from zipfile import ZipFile

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob

PDF = b"%PDF-1.4\nstep test\n%%EOF\n"


def login(client: TestClient, username: str = "step-admin") -> dict[str, str]:
    response = client.post("/auth/login", json={"username": username, "password": "secret123"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def add_avviso(db: Session, codice_cnc: str, anno: int) -> uuid.UUID:
    job = RuoloImportJob(id=uuid.uuid4(), anno_tributario=anno, status="completed")
    avviso = RuoloAvviso(
        id=uuid.uuid4(), import_job_id=job.id, codice_cnc=codice_cnc, anno_tributario=anno
    )
    db.add_all([job, avviso])
    db.commit()
    return avviso.id


def summary(cf: str = "RSSMRA80A01G113X", **overrides) -> dict:
    row = {
        "COD_FIS_NEW": cf,
        "TIP_ANA": "1",
        "DENOMINAZIONE": "ROSSI MARIO",
        "NUMERODOC": "1",
        "IMPORTO": "1.405,12",
        "PAGATO": "0,00",
        "RESIDUO": "1.405,12",
        "CONRESIDUO": "1",
        "STATODOC": "Non Pagato",
        "IMPORTO_AGGIORNATO": "1.405,12",
        "COD_ENT": "14215",
    }
    row.update(overrides)
    return row


def tributo(num_doc: str, des: str, anno: str = "2019", **overrides) -> dict:
    row = {
        "PARTITA": "1110315",
        "PRG": "1",
        "COD_TRI": "0985",
        "DES_TRI": "Consorzio - quote ordinarie",
        "TIP_TRI": "Imposta",
        "IMP_CAR": "50,00",
        "IMP_CARPAG": "10,00",
        "IMP_DIS": "0,00",
        "ANNO_RIF": anno,
        "NUM_DOC": num_doc,
        "DES_TRI1": des,
    }
    row.update(overrides)
    return row


def scheda(
    cf: str = "RSSMRA80A01G113X",
    *,
    tributi: list[dict] | None = None,
    pdf: dict | None = None,
    **summary_overrides,
) -> dict:
    num_doc = "20241421500000003"
    rows = (
        tributi
        if tributi is not None
        else [tributo(num_doc, "Avv. N. 020190006018040 Not. 31/01/2021 ")]
    )
    document = {
        "COD_ENT": "14215",
        "NUM_DOC": num_doc,
        "PRG_COO": 1,
        "NUM_TRIB": str(len(rows)),
        "TIPO_LISTA": 4,
        "COD_TRIB": "0985",
        "DES_TRIB": "Avv. N. 020190006018040 Not. 31/01/2021 ",
        "DES_DOC": "Consorzio - quote ordinarie",
        "ANNO_RIF": "2019",
        "DATA_NOTIFICA": "16/11/2024",
        "TOTDOVUTO": "1.405,12",
        "IMP_CAR": "1.405,12",
        "IMP_DIS": "0,00",
        "TOTPAGATO": "0,00",
        "RESIDUO": "1.405,12",
        "NOME_PDF": "doc.pdf",
    }
    return {
        "summary": summary(cf, **summary_overrides),
        "anagrafica": {
            "Codice fiscale": cf,
            "Denominazione": "ROSSI MARIO",
            "isc_TextItem_15": "Tipo persona ",
        },
        "situazioneContabile": {"Tot. Dovuto": "1.405,12"},
        "forms": [],
        "sections": [
            {
                "id": "isc_1",
                "section": "Documenti Emessi",
                "fields": [{"name": "NUM_DOC"}, {"name": "NUM_TRIB"}],
                "rows": [document],
                "totalRows": 1,
            },
            {
                "id": "isc_2",
                "section": "Pagamenti",
                "fields": [{"name": "NUM_QUI"}],
                "rows": [
                    {
                        "NUM_QUI": "0001",
                        "FLG_ANN": 0,
                        "DAT_PAG": "18/07/2025",
                        "DAT_ACC": "21/07/2025",
                        "MOD_PAG": "PagoPA",
                        "IMPORTO": 1869.26,
                        "IMP_PAG": 1679.12,
                        "NUM_DOC": num_doc,
                        "PRG_COO": 1,
                        "RIF_PAG": "Rif",
                        "STATO": "",
                    },
                    {
                        "NUM_QUI": "0002",
                        "FLG_ANN": 2,
                        "DAT_PAG": "",
                        "IMPORTO": "-217.4",
                        "NUM_DOC": "999",
                        "STATO": "ANNULLATO",
                    },
                ],
                "totalRows": 2,
            },
        ],
        "documents": [
            {
                "document": document,
                "tributi": {"total": len(rows), "pages": [], "rows": rows},
                "pdf": pdf
                if pdf is not None
                else {
                    "status": "downloaded",
                    "sha256": hashlib.sha256(PDF).hexdigest(),
                    "bytes": len(PDF),
                    "file": "doc.pdf",
                    "originalFilename": "Doc_1.pdf",
                },
            }
        ],
    }


def build_archive(
    path, schede: list[dict], *, verification: dict | None = None, pdf: bytes = PDF
) -> None:
    totals = {
        "contributors": 0,
        "documents": 0,
        "tributi": 0,
        "pdfs": 0,
        "unavailablePdfs": 0,
        "sha256": "abc",
    }
    with ZipFile(path, "w") as archive:
        for index, item in enumerate(schede):
            folder = f"contributors/{index:04d}_{item['summary']['COD_FIS_NEW']}"
            archive.writestr(f"{folder}/scheda.json", json.dumps(item))
            totals["contributors"] += 1
            for entry in item["documents"]:
                totals["documents"] += 1
                totals["tributi"] += len(entry["tributi"]["rows"])
                if entry["pdf"].get("status") == "downloaded":
                    totals["pdfs"] += 1
                    archive.writestr(f"{folder}/{entry['pdf']['file']}", pdf)
                else:
                    totals["unavailablePdfs"] += 1
        archive.writestr("contributors/readme.txt", "ignored")
        archive.writestr("verification.json", json.dumps(verification or totals))


def zip_bytes(schede: list[dict]) -> bytes:
    buffer = io.BytesIO()
    build_archive(buffer, schede)
    return buffer.getvalue()
