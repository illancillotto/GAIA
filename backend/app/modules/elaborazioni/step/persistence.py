"""Persist STEP list rows and schede into the archive tables.

A *scheda* has the shape produced by the STEP scraper (archive import and
live worker share it)::

    {"summary": {...list row...}, "anagrafica": {...}, "situazioneContabile": {...},
     "sections": [{"section", "fields", "rows", ...}], "documentReconciliation": {...},
     "documents": [{"document": {...}, "tributi": {"rows": [...]}, "pdf": {...}}]}

Documents, tributi and payments of a contribuente are a snapshot: when the
detail fingerprint changes they are rewritten and the previous version
survives in ``step_observations``.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.elaborazioni.step import parsing
from app.modules.elaborazioni.step.models import (
    StepContribuente,
    StepDocumento,
    StepObservation,
    StepPagamento,
    StepTributo,
)


@dataclass(frozen=True)
class StoredPdf:
    status: str
    path: str | None = None
    sha256: str | None = None
    bytes: int | None = None
    original_filename: str | None = None
    unavailable_reason: str | None = None


PdfStore = Callable[[StepContribuente, dict], StoredPdf]


@dataclass(frozen=True)
class SummaryResult:
    contribuente: StepContribuente
    created: bool
    summary_changed: bool


@dataclass(frozen=True)
class SchedaResult:
    contribuente: StepContribuente
    changed: bool
    documents: int
    tributi: int
    pagamenti: int
    document_ids: tuple[uuid.UUID, ...] = ()


def summary_key(summary: dict) -> tuple[str, str]:
    cod_ent = parsing.text(summary.get("COD_ENT"))
    codice_fiscale = parsing.text(summary.get("COD_FIS_NEW"))
    if cod_ent is None or codice_fiscale is None:
        raise ValueError("Riga STEP senza codice ente o codice fiscale")
    return cod_ent, codice_fiscale


def _apply_summary(contribuente: StepContribuente, summary: dict) -> None:
    contribuente.tipo_anagrafica = parsing.text(summary.get("TIP_ANA"))
    contribuente.denominazione = parsing.text(summary.get("DENOMINAZIONE"))
    contribuente.numero_documenti = parsing.integer(summary.get("NUMERODOC"))
    contribuente.importo = parsing.amount(summary.get("IMPORTO"))
    contribuente.pagato = parsing.amount(summary.get("PAGATO"))
    contribuente.residuo = parsing.amount(summary.get("RESIDUO"))
    contribuente.importo_aggiornato = parsing.amount(summary.get("IMPORTO_AGGIORNATO"))
    contribuente.stato_documenti = parsing.text(summary.get("STATODOC"))
    contribuente.summary_raw_json = summary
    contribuente.summary_fingerprint = parsing.fingerprint(summary)


def upsert_summary(
    db: Session, summary: dict, *, job_id: int | None, now: datetime
) -> SummaryResult:
    cod_ent, codice_fiscale = summary_key(summary)
    contribuente = db.scalar(
        select(StepContribuente).where(
            StepContribuente.cod_ent == cod_ent,
            StepContribuente.codice_fiscale == codice_fiscale,
        )
    )
    created = contribuente is None
    if contribuente is None:
        contribuente = StepContribuente(
            id=uuid.uuid4(), cod_ent=cod_ent, codice_fiscale=codice_fiscale
        )
        db.add(contribuente)
    changed = contribuente.summary_fingerprint != parsing.fingerprint(summary)
    if changed:
        _apply_summary(contribuente, summary)
    contribuente.last_seen_job_id = job_id
    contribuente.last_seen_at = now
    db.flush()
    return SummaryResult(contribuente=contribuente, created=created, summary_changed=changed)


# Interest accrues daily on these list columns: they are refreshed from the list
# but must not trigger a new scheda download on their own.
_ACCRUING_SUMMARY_FIELDS = frozenset({"RESIDUO", "IMPORTO_AGGIORNATO"})


def detail_trigger(summary: dict) -> str:
    return parsing.fingerprint(
        {key: value for key, value in summary.items() if key not in _ACCRUING_SUMMARY_FIELDS}
    )


def needs_detail(contribuente: StepContribuente) -> bool:
    """A scheda is (re)downloaded when never fetched or when a non-accruing list column changed after it."""

    if contribuente.detail_fingerprint is None:
        return True
    stored = (contribuente.document_reconciliation_json or {}).get("detail_trigger")
    return stored != detail_trigger(contribuente.summary_raw_json)


def _labeled(values: dict | None) -> dict:
    return {key: value for key, value in (values or {}).items() if not str(key).startswith("isc_")}


def _sections(sections: list[dict]) -> list[dict]:
    return [
        {
            "section": section.get("section"),
            "fields": [field.get("name") for field in section.get("fields") or []],
            "rows": section.get("rows") or [],
        }
        for section in sections
    ]


def _document_sections(sections: list[dict]) -> dict[tuple[str, str], str | None]:
    located: dict[tuple[str, str], str | None] = {}
    for section in sections:
        if "NUM_TRIB" not in {field.get("name") for field in section.get("fields") or []}:
            continue
        for row in section.get("rows") or []:
            located[(str(row.get("NUM_DOC")), str(row.get("PRG_COO") or "1"))] = section.get(
                "section"
            )
    return located


def _observation_payload(scheda: dict) -> dict:
    """Source facts of a scheda; derived data (reconciliation, file names) is excluded."""

    return {
        "summary": scheda.get("summary"),
        "anagrafica": scheda.get("anagrafica"),
        "situazione": scheda.get("situazioneContabile"),
        "sections": _sections(scheda.get("sections") or []),
        "documents": [
            {
                "document": entry.get("document"),
                "tributi": (entry.get("tributi") or {}).get("rows"),
                "pdf_sha256": (entry.get("pdf") or {}).get("sha256"),
            }
            for entry in scheda.get("documents") or []
        ],
    }


def _build_documento(
    contribuente: StepContribuente,
    entry: dict,
    located: dict[tuple[str, str], str | None],
) -> StepDocumento:
    raw = entry["document"]
    key = (str(raw["NUM_DOC"]), str(raw.get("PRG_COO") or "1"))
    return StepDocumento(
        id=uuid.uuid4(),
        contribuente_id=contribuente.id,
        num_doc=key[0],
        prg_coo=key[1],
        section=located.get(key),
        tipo_lista=parsing.text(raw.get("TIPO_LISTA")),
        cod_trib=parsing.text(raw.get("COD_TRIB")),
        des_trib=parsing.text(raw.get("DES_TRIB")),
        des_doc=parsing.text(raw.get("DES_DOC")),
        anno_rif=parsing.text(raw.get("ANNO_RIF")),
        data_notifica=parsing.parse_date(raw.get("DATA_NOTIFICA")),
        tot_dovuto=parsing.amount(raw.get("TOTDOVUTO")),
        imp_carico=parsing.amount(raw.get("IMP_CAR")),
        imp_discaricato=parsing.amount(raw.get("IMP_DIS")),
        tot_pagato=parsing.amount(raw.get("TOTPAGATO")),
        residuo=parsing.amount(raw.get("RESIDUO")),
        num_tributi=parsing.integer(raw.get("NUM_TRIB")),
        raw_json=raw,
        source_fingerprint=parsing.fingerprint(raw),
    )


def _apply_pdf(documento: StepDocumento, pdf: StoredPdf) -> None:
    documento.pdf_status = pdf.status
    documento.pdf_path = pdf.path
    documento.pdf_sha256 = pdf.sha256
    documento.pdf_bytes = pdf.bytes
    documento.pdf_original_filename = pdf.original_filename
    documento.pdf_unavailable_reason = pdf.unavailable_reason


def _build_tributi(documento: StepDocumento, rows: list[dict]) -> list[StepTributo]:
    tributi = []
    for position, row in enumerate(rows, 1):
        reference, cnc = parsing.avviso_reference(row.get("DES_TRI1"))
        tributi.append(
            StepTributo(
                id=uuid.uuid4(),
                documento_id=documento.id,
                position=position,
                partita=parsing.text(row.get("PARTITA")),
                prg=parsing.text(row.get("PRG")),
                cod_tributo=parsing.text(row.get("COD_TRI")),
                des_tributo=parsing.text(row.get("DES_TRI")),
                tipo_tributo=parsing.text(row.get("TIP_TRI")),
                anno_rif=parsing.year(row.get("ANNO_RIF")),
                imp_carico=parsing.amount(row.get("IMP_CAR")),
                imp_carico_pagato=parsing.amount(row.get("IMP_CARPAG")),
                imp_discaricato=parsing.amount(row.get("IMP_DIS")),
                avviso_reference_raw=reference,
                codice_cnc=cnc,
                raw_json=row,
            )
        )
    return tributi


def _build_pagamenti(
    contribuente: StepContribuente,
    sections: list[dict],
    documenti: dict[tuple[str, str], StepDocumento],
) -> list[StepPagamento]:
    rows = [
        row
        for section in sections
        if "NUM_QUI" in {field.get("name") for field in section.get("fields") or []}
        for row in section.get("rows") or []
    ]
    pagamenti = []
    for position, row in enumerate(rows, 1):
        documento = documenti.get((str(row.get("NUM_DOC")), str(row.get("PRG_COO") or "1")))
        pagamenti.append(
            StepPagamento(
                id=uuid.uuid4(),
                contribuente_id=contribuente.id,
                documento_id=documento.id if documento else None,
                position=position,
                num_quietanza=parsing.text(row.get("NUM_QUI")),
                num_doc=parsing.text(row.get("NUM_DOC")),
                data_pagamento=parsing.parse_date(row.get("DAT_PAG")),
                data_accredito=parsing.parse_date(row.get("DAT_ACC")),
                modalita=parsing.text(row.get("MOD_PAG")),
                importo=parsing.amount(row.get("IMPORTO")),
                importo_pagato=parsing.amount(row.get("IMP_PAG")),
                annullato=str(row.get("FLG_ANN") or "0") != "0",
                stato=parsing.text(row.get("STATO")),
                riferimento=parsing.text(row.get("RIF_PAG")),
                raw_json=row,
            )
        )
    return pagamenti


def _replace_children(db: Session, contribuente: StepContribuente) -> None:
    db.execute(delete(StepPagamento).where(StepPagamento.contribuente_id == contribuente.id))
    document_ids = select(StepDocumento.id).where(StepDocumento.contribuente_id == contribuente.id)
    db.execute(delete(StepTributo).where(StepTributo.documento_id.in_(document_ids)))
    db.execute(delete(StepDocumento).where(StepDocumento.contribuente_id == contribuente.id))
    db.flush()


def _validate_scheda(scheda: dict) -> None:
    summary = scheda.get("summary") or {}
    anagrafica = scheda.get("anagrafica") or {}
    if anagrafica.get("Codice fiscale") != summary.get("COD_FIS_NEW"):
        raise ValueError("Scheda STEP di un contribuente diverso dalla riga elenco")
    for entry in scheda.get("documents") or []:
        rows = (entry.get("tributi") or {}).get("rows") or []
        if len(rows) != parsing.integer(entry["document"].get("NUM_TRIB")):
            raise ValueError(
                f"Tributi incompleti per il documento STEP {entry['document'].get('NUM_DOC')}"
            )


def persist_scheda(
    db: Session,
    scheda: dict,
    *,
    job_id: int | None,
    now: datetime,
    pdf_store: PdfStore,
) -> SchedaResult:
    _validate_scheda(scheda)
    contribuente = upsert_summary(db, scheda["summary"], job_id=job_id, now=now).contribuente
    observation = _observation_payload(scheda)
    detail_fingerprint = parsing.fingerprint(observation)
    if contribuente.detail_fingerprint == detail_fingerprint:
        _mark_detail_current(contribuente, scheda, now)
        return SchedaResult(contribuente, False, 0, 0, 0)

    _replace_children(db, contribuente)
    sections = scheda.get("sections") or []
    located = _document_sections(sections)
    documenti: dict[tuple[str, str], StepDocumento] = {}
    tributi_count = 0
    for entry in scheda.get("documents") or []:
        documento = _build_documento(contribuente, entry, located)
        _apply_pdf(documento, pdf_store(contribuente, entry))
        db.add(documento)
        tributi = _build_tributi(documento, (entry.get("tributi") or {}).get("rows") or [])
        db.add_all(tributi)
        tributi_count += len(tributi)
        documenti[(documento.num_doc, documento.prg_coo)] = documento
    pagamenti = _build_pagamenti(contribuente, sections, documenti)
    db.add_all(pagamenti)

    contribuente.anagrafica_json = _labeled(scheda.get("anagrafica"))
    contribuente.situazione_contabile_json = _labeled(scheda.get("situazioneContabile"))
    contribuente.sections_json = _sections(sections)
    contribuente.detail_fingerprint = detail_fingerprint
    _mark_detail_current(contribuente, scheda, now)
    db.add(
        StepObservation(
            id=uuid.uuid4(),
            contribuente_id=contribuente.id,
            job_id=job_id,
            kind="scheda",
            fingerprint=detail_fingerprint,
            payload_json=observation,
            observed_at=now,
        )
    )
    db.flush()
    return SchedaResult(
        contribuente,
        True,
        len(documenti),
        tributi_count,
        len(pagamenti),
        tuple(item.id for item in documenti.values()),
    )


def _mark_detail_current(contribuente: StepContribuente, scheda: dict, now: datetime) -> None:
    contribuente.document_reconciliation_json = {
        **(scheda.get("documentReconciliation") or {}),
        "detail_trigger": detail_trigger(scheda["summary"]),
    }
    contribuente.detail_synced_at = now
