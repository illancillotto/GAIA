from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import UUID

import pandas as pd
from pandas.errors import EmptyDataError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.elaborazioni.capacitas.client import InVoltureClient
from app.modules.elaborazioni.capacitas.models import (
    CapacitasAnagrafica,
    CapacitasAnagraficaDetail,
    CapacitasAnagraficaHistoryImportItem,
    CapacitasAnagraficaHistoryImportItemResult,
    CapacitasAnagraficaHistoryImportRequest,
    CapacitasAnagraficaHistoryImportResponse,
    CapacitasStoricoAnagraficaRow,
)
from app.modules.utenze.models import (
    AnagraficaPerson,
    AnagraficaSubject,
    AnagraficaSubjectStatus,
    AnagraficaSubjectType,
)
from app.modules.utenze.services.person_history_service import persist_person_source_snapshot
from app.services.elaborazioni_capacitas_terreni import (
    _compose_address,
    _normalize_cf,
    _parse_datetime_value,
    _split_denominazione,
)


class CapacitasAnagraficaHistoryImportError(Exception):
    pass


@dataclass(slots=True)
class _ResolvedTarget:
    subject: AnagraficaSubject | None
    person: AnagraficaPerson | None
    idxana: str | None


def load_anagrafica_history_import_request(
    *,
    filename: str,
    content: bytes,
    credential_id: int | None = None,
) -> CapacitasAnagraficaHistoryImportRequest:
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".csv":
            dataframe = pd.read_csv(BytesIO(content), dtype=str, keep_default_na=False)
        elif suffix == ".xlsx":
            dataframe = pd.read_excel(BytesIO(content), dtype=str, keep_default_na=False)
        else:
            raise CapacitasAnagraficaHistoryImportError("Formato file non supportato. Usare CSV o XLSX.")
    except EmptyDataError as exc:
        raise CapacitasAnagraficaHistoryImportError("Il file batch non contiene righe.") from exc
    except ValueError as exc:
        raise CapacitasAnagraficaHistoryImportError("Il file batch non puo essere letto.") from exc

    if dataframe.empty:
        raise CapacitasAnagraficaHistoryImportError("Il file batch non contiene righe.")

    normalized_columns = {str(column).strip().lower(): column for column in dataframe.columns}
    subject_col = normalized_columns.get("subject_id")
    idxana_col = normalized_columns.get("idxana")
    if subject_col is None and idxana_col is None:
        raise CapacitasAnagraficaHistoryImportError("Il file batch deve contenere almeno una colonna tra subject_id e idxana.")

    items: list[CapacitasAnagraficaHistoryImportItem] = []
    for _, row in dataframe.iterrows():
        subject_id_raw = str(row.get(subject_col, "")).strip() if subject_col is not None else ""
        idxana_raw = str(row.get(idxana_col, "")).strip() if idxana_col is not None else ""
        if not subject_id_raw and not idxana_raw:
            continue
        items.append(
            CapacitasAnagraficaHistoryImportItem(
                subject_id=UUID(subject_id_raw) if subject_id_raw else None,
                idxana=idxana_raw or None,
            )
        )

    if not items:
        raise CapacitasAnagraficaHistoryImportError("Il file batch non contiene righe valide.")

    return CapacitasAnagraficaHistoryImportRequest(items=items, credential_id=credential_id)


async def import_anagrafica_history_batch(
    db: Session,
    client: InVoltureClient,
    request: CapacitasAnagraficaHistoryImportRequest,
) -> CapacitasAnagraficaHistoryImportResponse:
    totals = {
        "processed": 0,
        "imported": 0,
        "skipped": 0,
        "failed": 0,
        "snapshot_records_imported": 0,
    }
    items: list[CapacitasAnagraficaHistoryImportItemResult] = []
    storico_cache: dict[str, list[CapacitasStoricoAnagraficaRow]] = {}
    detail_cache: dict[str, CapacitasAnagraficaDetail] = {}

    for item in request.items:
        totals["processed"] += 1
        try:
            result = await _import_single_item(
                db,
                client,
                item,
                storico_cache=storico_cache,
                detail_cache=detail_cache,
            )
            items.append(result)
            if result.status == "imported":
                totals["imported"] += 1
                totals["snapshot_records_imported"] += result.imported_records
            elif result.status == "skipped":
                totals["skipped"] += 1
        except Exception as exc:
            db.rollback()
            items.append(
                CapacitasAnagraficaHistoryImportItemResult(
                    subject_id=str(item.subject_id) if item.subject_id else None,
                    idxana=item.idxana,
                    status="failed",
                    error=str(exc),
                )
            )
            totals["failed"] += 1
            if not request.continue_on_error:
                break

    return CapacitasAnagraficaHistoryImportResponse(items=items, **totals)


async def _import_single_item(
    db: Session,
    client: InVoltureClient,
    item: CapacitasAnagraficaHistoryImportItem,
    *,
    storico_cache: dict[str, list[CapacitasStoricoAnagraficaRow]],
    detail_cache: dict[str, CapacitasAnagraficaDetail],
) -> CapacitasAnagraficaHistoryImportItemResult:
    resolved = await _resolve_target(db, client, item)
    if resolved.subject is not None and resolved.subject.subject_type != AnagraficaSubjectType.PERSON.value:
        raise CapacitasAnagraficaHistoryImportError("Lo storico anagrafico e supportato solo per soggetti persona.")
    if not resolved.idxana:
        raise CapacitasAnagraficaHistoryImportError("Impossibile determinare IDXANA per il soggetto richiesto.")

    history_rows = storico_cache.get(resolved.idxana)
    if history_rows is None:
        history_rows = await client.fetch_anagrafica_history(idxana=resolved.idxana)
        history_rows = _sort_history_rows(history_rows)
        storico_cache[resolved.idxana] = history_rows

    if not history_rows:
        return CapacitasAnagraficaHistoryImportItemResult(
            subject_id=str(item.subject_id) if item.subject_id else None,
            resolved_subject_id=str(resolved.subject.id) if resolved.subject is not None else None,
            idxana=resolved.idxana,
            status="skipped",
            message="Nessuno storico presente.",
        )

    latest_row = history_rows[-1]
    latest_detail = await _load_detail(client, latest_row.history_id, detail_cache)
    subject, person = _ensure_subject_person(
        db,
        subject=resolved.subject,
        person=resolved.person,
        idxana=resolved.idxana,
        latest_row=latest_row,
        latest_detail=latest_detail,
    )

    imported_records = 0
    for history_row in history_rows:
        detail = await _load_detail(client, history_row.history_id, detail_cache)
        snapshot_payload = _build_person_payload(detail, history_row)
        imported = persist_person_source_snapshot(
            db,
            person,
            snapshot_payload,
            source_system="capacitas",
            source_ref=history_row.history_id,
            collected_at=_parse_datetime_value(history_row.data_agg) or datetime.now(UTC),
            valid_from=_parse_datetime_value(history_row.data_agg),
            is_capacitas_history=True,
        )
        if imported:
            imported_records += 1

    if subject.source_external_id != resolved.idxana:
        subject.source_external_id = resolved.idxana
    if subject.source_system != "capacitas":
        subject.source_system = "capacitas"

    db.commit()
    db.refresh(subject)

    if imported_records == 0:
        return CapacitasAnagraficaHistoryImportItemResult(
            subject_id=str(item.subject_id) if item.subject_id else None,
            resolved_subject_id=str(subject.id),
            idxana=resolved.idxana,
            status="skipped",
            history_records_total=len(history_rows),
            skipped_records=len(history_rows),
            message="Storico gia importato.",
        )

    return CapacitasAnagraficaHistoryImportItemResult(
        subject_id=str(item.subject_id) if item.subject_id else None,
        resolved_subject_id=str(subject.id),
        idxana=resolved.idxana,
        status="imported",
        history_records_total=len(history_rows),
        imported_records=imported_records,
        skipped_records=len(history_rows) - imported_records,
        message=f"Importati {imported_records} record storici.",
    )


async def _resolve_target(
    db: Session,
    client: InVoltureClient,
    item: CapacitasAnagraficaHistoryImportItem,
) -> _ResolvedTarget:
    subject: AnagraficaSubject | None = None
    person: AnagraficaPerson | None = None
    idxana = item.idxana.strip() if item.idxana else None

    if item.subject_id is not None:
        subject = db.get(AnagraficaSubject, item.subject_id)
        if subject is None:
            raise CapacitasAnagraficaHistoryImportError(f"Soggetto {item.subject_id} non trovato.")
        person = db.get(AnagraficaPerson, item.subject_id)
        if person is None:
            raise CapacitasAnagraficaHistoryImportError(f"Soggetto {item.subject_id} non associato a una persona.")

    if idxana is None and subject is not None and subject.source_system == "capacitas" and subject.source_external_id:
        idxana = subject.source_external_id

    if idxana is None and person is not None:
        idxana = await _resolve_idxana_from_cf(client, person.codice_fiscale)

    if subject is None and idxana is not None:
        subject = db.scalar(
            select(AnagraficaSubject).where(
                AnagraficaSubject.source_system == "capacitas",
                AnagraficaSubject.source_external_id == idxana,
            )
        )
        if subject is not None:
            person = db.get(AnagraficaPerson, subject.id)

    return _ResolvedTarget(subject=subject, person=person, idxana=idxana)


async def _resolve_idxana_from_cf(client: InVoltureClient, codice_fiscale: str | None) -> str | None:
    normalized_cf = _normalize_cf(codice_fiscale)
    if not normalized_cf:
        return None
    search_result = await client.search_by_cf(normalized_cf)
    for row in search_result.rows:
        if _normalize_cf(row.codice_fiscale) == normalized_cf and row.id_ana:
            return row.id_ana
    matching_row = _pick_best_search_row(search_result.rows)
    return matching_row.id_ana if matching_row is not None else None


def _pick_best_search_row(rows: list[CapacitasAnagrafica]) -> CapacitasAnagrafica | None:
    for row in rows:
        if row.id_ana:
            return row
    return None


def _ensure_subject_person(
    db: Session,
    *,
    subject: AnagraficaSubject | None,
    person: AnagraficaPerson | None,
    idxana: str,
    latest_row: CapacitasStoricoAnagraficaRow,
    latest_detail: CapacitasAnagraficaDetail,
) -> tuple[AnagraficaSubject, AnagraficaPerson]:
    if subject is not None and person is not None:
        return subject, person

    normalized_cf = _normalize_cf(latest_detail.codice_fiscale or latest_row.codice_fiscale)
    if person is None and normalized_cf:
        person = db.scalar(select(AnagraficaPerson).where(AnagraficaPerson.codice_fiscale == normalized_cf))
        if person is not None and subject is None:
            subject = db.get(AnagraficaSubject, person.subject_id)

    if subject is None:
        if not normalized_cf:
            raise CapacitasAnagraficaHistoryImportError("Storico privo di codice fiscale utilizzabile per creare il soggetto.")
        payload = _build_person_payload(latest_detail, latest_row)
        subject = AnagraficaSubject(
            subject_type=AnagraficaSubjectType.PERSON.value,
            status=AnagraficaSubjectStatus.ACTIVE.value,
            source_system="capacitas",
            source_external_id=idxana,
            source_name_raw=latest_detail.denominazione or latest_row.denominazione or normalized_cf,
            requires_review=False,
        )
        db.add(subject)
        db.flush()
        person = AnagraficaPerson(subject_id=subject.id, **payload)
        db.add(person)
        db.flush()
        return subject, person

    if person is None:
        person = db.get(AnagraficaPerson, subject.id)
    if person is None:
        raise CapacitasAnagraficaHistoryImportError("Soggetto risolto senza record persona associato.")
    return subject, person


def _build_person_payload(
    detail: CapacitasAnagraficaDetail,
    history_row: CapacitasStoricoAnagraficaRow,
) -> dict[str, object | None]:
    cognome, nome = _split_denominazione(
        detail.denominazione or history_row.denominazione,
        fallback_cognome=detail.cognome,
        fallback_nome=detail.nome,
    )
    indirizzo = _compose_address(
        detail.residenza_toponimo,
        detail.residenza_indirizzo,
        detail.residenza_civico,
        detail.residenza_sub,
    )
    note_parts = [value.strip() for value in detail.note if value and value.strip()]
    return {
        "cognome": detail.cognome or cognome,
        "nome": detail.nome or nome,
        "codice_fiscale": _normalize_cf(detail.codice_fiscale or history_row.codice_fiscale) or "",
        "data_nascita": detail.data_nascita,
        "comune_nascita": history_row.luogo_nascita or detail.luogo_nascita,
        "indirizzo": indirizzo,
        "comune_residenza": detail.residenza_belfiore,
        "cap": detail.residenza_cap,
        "email": detail.email,
        "telefono": detail.telefono or detail.cellulare,
        "note": " | ".join(note_parts) if note_parts else None,
    }


def _sort_history_rows(rows: list[CapacitasStoricoAnagraficaRow]) -> list[CapacitasStoricoAnagraficaRow]:
    return sorted(
        rows,
        key=lambda row: (
            _parse_datetime_value(row.data_agg) or datetime.min.replace(tzinfo=UTC),
            row.history_id,
        ),
    )


async def _load_detail(
    client: InVoltureClient,
    history_id: str,
    cache: dict[str, CapacitasAnagraficaDetail],
) -> CapacitasAnagraficaDetail:
    detail = cache.get(history_id)
    if detail is None:
        detail = await client.fetch_anagrafica_detail(history_id=history_id)
        cache[history_id] = detail
    return detail
