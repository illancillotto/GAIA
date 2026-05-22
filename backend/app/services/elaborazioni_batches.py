from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
import re
import unicodedata
from uuid import UUID
from zoneinfo import ZoneInfo

import pandas as pd
from pandas.errors import EmptyDataError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.elaborazioni import (
    ElaborazioneBatch,
    ElaborazioneBatchStatus,
    ElaborazioneRichiesta,
    ElaborazioneRichiestaStatus,
)
from app.schemas.elaborazioni import ElaborazioneRichiestaCreateRequest
from app.services.catasto_comuni import get_catasto_comuni_lookup
from app.services.elaborazioni_credentials import (
    ElaborazioneCredentialNotFoundError,
    require_credentials_for_user,
)


UPLOAD_COLUMN_ALIASES = {
    "search_mode": "search_mode",
    "modalita_ricerca": "search_mode",
    "citta": "comune",
    "comune": "comune",
    "catasto": "catasto",
    "sezione": "sezione",
    "foglio": "foglio",
    "fg": "foglio",
    "particella": "particella",
    "mapp": "particella",
    "subalterno": "subalterno",
    "tipo_visura": "tipo_visura",
    "tipovisura": "tipo_visura",
    "codice_fiscale": "subject_id",
    "cf": "subject_id",
    "partita_iva": "subject_id",
    "partita iva": "subject_id",
    "piva": "subject_id",
    "tipo_soggetto": "subject_kind",
    "tipo_richiesta": "request_type",
    "intestazione": "intestazione",
}
ALLOWED_CATASTO = {
    "terreni": "Terreni",
    "terreni e fabbricati": "Terreni e Fabbricati",
}
ALLOWED_TIPO_VISURA = {
    "sintetica": "Sintetica",
    "completa": "Completa",
}
ALLOWED_SEARCH_MODE = {"immobile", "soggetto"}
ALLOWED_SUBJECT_KIND = {"PF", "PNF"}
ALLOWED_REQUEST_TYPE = {"ATTUALITA", "STORICA"}
IMMOBILE_REQUIRED_UPLOAD_COLUMNS = {"comune", "catasto", "foglio", "particella"}
UTC = timezone.utc

CF_PF_RE = re.compile(r"^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$")
PIVA_RE = re.compile(r"^\d{11}$")


class BatchValidationError(Exception):
    def __init__(self, message: str, errors: list[dict[str, object]] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.errors = errors or []

    def to_detail(self) -> dict[str, object]:
        return {"message": self.message, "errors": self.errors}


class BatchNotFoundError(Exception):
    pass


class BatchConflictError(Exception):
    pass


class RequestNotFoundError(Exception):
    pass


RELEASE_REQUESTED_OPERATION = "Release requested by user"
RELEASE_REQUESTED_MESSAGE = "Credenziale SISTER liberata su richiesta utente"


@dataclass(slots=True)
class ValidatedVisuraRow:
    row_index: int
    search_mode: str
    comune: str | None
    comune_codice: str | None
    catasto: str | None
    sezione: str | None
    foglio: str | None
    particella: str | None
    subalterno: str | None
    tipo_visura: str
    subject_kind: str | None = None
    subject_id: str | None = None
    request_type: str | None = None
    intestazione: str | None = None
    status: str = ElaborazioneRichiestaStatus.PENDING.value
    current_operation: str = "Pending"
    error_message: str | None = None


def normalize_lookup_value(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", normalized.lower()).strip()


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _get_operation_window_snapshot(now_utc: datetime | None = None) -> dict[str, object]:
    now_utc = now_utc or datetime.now(UTC)
    timezone_name = settings.elaborazioni_operation_timezone
    try:
        window_tz = ZoneInfo(timezone_name)
    except Exception:
        window_tz = ZoneInfo("Europe/Rome")
        timezone_name = "Europe/Rome"

    start_hour = min(max(settings.elaborazioni_operation_start_hour, 0), 23)
    end_hour = min(max(settings.elaborazioni_operation_end_hour, 0), 23)
    enabled = settings.elaborazioni_operation_window_enabled

    if not enabled:
        return {
            "enabled": False,
            "timezone": timezone_name,
            "start_hour": start_hour,
            "end_hour": end_hour,
            "is_within_window": True,
            "state_label": "Sempre attiva",
            "next_resume_at": None,
        }

    local_now = now_utc.astimezone(window_tz)
    current_hour = local_now.hour
    if start_hour <= end_hour:
        is_within_window = start_hour <= current_hour <= end_hour
    else:
        is_within_window = current_hour >= start_hour or current_hour <= end_hour

    if is_within_window:
        return {
            "enabled": True,
            "timezone": timezone_name,
            "start_hour": start_hour,
            "end_hour": end_hour,
            "is_within_window": True,
            "state_label": "Operativa",
            "next_resume_at": None,
        }

    next_resume_local = local_now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    if local_now.hour > end_hour or (start_hour <= end_hour and current_hour > end_hour):
        next_resume_local = next_resume_local.replace(day=local_now.day) + timedelta(days=1)
    elif next_resume_local <= local_now:
        next_resume_local = next_resume_local + timedelta(days=1)

    return {
        "enabled": True,
        "timezone": timezone_name,
        "start_hour": start_hour,
        "end_hour": end_hour,
        "is_within_window": False,
        "state_label": "In pausa",
        "next_resume_at": next_resume_local.astimezone(UTC),
    }


def normalize_column_name(value: str) -> str:
    return normalize_lookup_value(value).replace(" ", "_")


def clean_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def infer_subject_kind(subject_id: str) -> str:
    normalized = clean_cell(subject_id).upper()
    if CF_PF_RE.match(normalized):
        return "PF"
    if PIVA_RE.match(normalized):
        return "PNF"
    return "PF" if any(char.isalpha() for char in normalized) else "PNF"


def _is_legacy_excel_layout(columns: set[str]) -> bool:
    return {"comune", "foglio", "particella"}.issubset(columns) and "catasto" not in columns and "tipo_visura" not in columns


def _build_comune_code_lookup(db: Session) -> dict[str, object]:
    by_name = get_catasto_comuni_lookup(db)
    by_code: dict[str, object] = {}
    for comune in by_name.values():
        code_prefix = clean_cell(comune.codice_sister).split("#", maxsplit=1)[0].upper()
        if code_prefix:
            by_code[code_prefix] = comune
    return by_code


def load_upload_records(filename: str, content: bytes) -> list[dict[str, str]]:
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".csv":
            dataframe = pd.read_csv(BytesIO(content), dtype=str, keep_default_na=False)
        elif suffix == ".xlsx":
            dataframe = pd.read_excel(BytesIO(content), dtype=str, keep_default_na=False)
        else:
            raise BatchValidationError("Unsupported file format. Use CSV or XLSX.")
    except EmptyDataError as exc:
        raise BatchValidationError("The uploaded file is empty.") from exc
    except ValueError as exc:
        raise BatchValidationError("The uploaded file could not be parsed.") from exc

    if dataframe.empty:
        raise BatchValidationError("The uploaded file does not contain any rows.")

    rename_map: dict[str, str] = {}
    for column in dataframe.columns:
        normalized = normalize_column_name(str(column))
        canonical = UPLOAD_COLUMN_ALIASES.get(normalized)
        if canonical is None:
            continue
        if canonical in rename_map.values():
            raise BatchValidationError(
                "Duplicate upload columns detected after normalization.",
                errors=[{"column": canonical}],
            )
        rename_map[column] = canonical

    dataframe = dataframe.rename(columns=rename_map)
    for optional_column in ("sezione", "subalterno"):
        if optional_column not in dataframe.columns:
            dataframe[optional_column] = ""

    if _is_legacy_excel_layout(set(dataframe.columns)):
        dataframe["catasto"] = "Terreni"
        dataframe["tipo_visura"] = "Sintetica"

    return [{key: clean_cell(value) for key, value in row.items()} for row in dataframe.to_dict(orient="records")]


def _detect_search_mode(record: dict[str, str]) -> str:
    explicit_mode = normalize_lookup_value(clean_cell(record.get("search_mode")))
    if explicit_mode in ALLOWED_SEARCH_MODE:
        return explicit_mode
    if clean_cell(record.get("subject_id")):
        return "soggetto"
    return "immobile"


def _normalize_tipo_visura(value: str) -> str | None:
    normalized = normalize_lookup_value(clean_cell(value))
    if not normalized:
        return ALLOWED_TIPO_VISURA["sintetica"]
    return ALLOWED_TIPO_VISURA.get(normalized)


def _normalize_request_type(value: str) -> str:
    normalized = normalize_lookup_value(clean_cell(value))
    if normalized in {"storica", "s"}:
        return "STORICA"
    return "ATTUALITA"


def _normalize_subject_kind(value: str, subject_id: str) -> str:
    normalized = normalize_lookup_value(clean_cell(value))
    if normalized in {"pg", "persona giuridica", "giuridica", "pnf"}:
        return "PNF"
    if normalized in {"pf", "persona fisica", "fisica"}:
        return "PF"
    return infer_subject_kind(subject_id)


def validate_visure_records(db: Session, records: list[dict[str, str]]) -> list[ValidatedVisuraRow]:
    comune_lookup = get_catasto_comuni_lookup(db)
    comune_code_lookup = _build_comune_code_lookup(db)
    errors: list[dict[str, object]] = []
    validated_rows: list[ValidatedVisuraRow] = []

    for row_index, record in enumerate(records, start=1):
        row_errors: list[str] = []
        search_mode = _detect_search_mode(record)
        tipo_visura_value = _normalize_tipo_visura(clean_cell(record.get("tipo_visura")))

        if tipo_visura_value is None:
            row_errors.append("Tipo visura deve essere 'Sintetica' o 'Completa'.")

        if search_mode == "soggetto":
            subject_id = clean_cell(record.get("subject_id")).upper()
            if not subject_id:
                row_errors.append("subject_id obbligatorio per la ricerca soggetto.")
            request_type = _normalize_request_type(clean_cell(record.get("request_type")))
            subject_kind = _normalize_subject_kind(clean_cell(record.get("subject_kind")), subject_id)
            if subject_kind not in ALLOWED_SUBJECT_KIND:
                row_errors.append("Tipo soggetto deve essere PF o PNF.")

            if row_errors:
                errors.append({"row_index": row_index, "errors": row_errors, "values": record})
                continue

            assert tipo_visura_value is not None
            validated_rows.append(
                ValidatedVisuraRow(
                    row_index=row_index,
                    search_mode="soggetto",
                    comune=None,
                    comune_codice=None,
                    catasto=None,
                    sezione=None,
                    foglio=None,
                    particella=None,
                    subalterno=None,
                    tipo_visura=tipo_visura_value,
                    subject_kind=subject_kind,
                    subject_id=subject_id,
                    request_type=request_type,
                    intestazione=clean_cell(record.get("intestazione")) or None,
                )
            )
            continue

        comune_value = clean_cell(record.get("comune"))
        if comune_value.upper() in {"UE", "EU"}:
            validated_rows.append(
                ValidatedVisuraRow(
                    row_index=row_index,
                    search_mode="immobile",
                    comune=comune_value.upper(),
                    comune_codice=comune_value.upper(),
                    catasto=ALLOWED_CATASTO["terreni"],
                    sezione=None,
                    foglio=clean_cell(record.get("foglio")) or "-",
                    particella=clean_cell(record.get("particella")) or "-",
                    subalterno=clean_cell(record.get("subalterno")) or None,
                    tipo_visura=ALLOWED_TIPO_VISURA["sintetica"],
                    status=ElaborazioneRichiestaStatus.SKIPPED.value,
                    current_operation=f"Record {comune_value.upper()} saltato in import",
                    error_message=f"Record saltato: il valore Comune e' {comune_value.upper()}.",
                )
            )
            continue

        missing_immobile_columns = [
            column_name for column_name in IMMOBILE_REQUIRED_UPLOAD_COLUMNS if not clean_cell(record.get(column_name))
        ]
        if missing_immobile_columns:
            row_errors.append(
                f"Campi obbligatori mancanti per ricerca immobile: {', '.join(sorted(missing_immobile_columns))}."
            )

        comune = None
        if comune_value:
            comune = comune_lookup.get(normalize_lookup_value(comune_value))
            if comune is None:
                comune = comune_code_lookup.get(comune_value.upper())
        catasto_value = ALLOWED_CATASTO.get(normalize_lookup_value(clean_cell(record.get("catasto"))))
        foglio_value = clean_cell(record.get("foglio"))
        particella_value = clean_cell(record.get("particella"))
        subalterno_value = clean_cell(record.get("subalterno"))
        sezione_value = clean_cell(record.get("sezione"))

        if comune is None:
            row_errors.append("Comune non valido o non censito in catasto_comuni.")
        if catasto_value is None:
            row_errors.append("Catasto deve essere 'Terreni' o 'Terreni e Fabbricati'.")
        if not foglio_value or not foglio_value.isdigit():
            row_errors.append("Foglio obbligatorio e numerico.")
        if not particella_value or not particella_value.isdigit():
            row_errors.append("Particella obbligatoria e numerica.")
        if subalterno_value and not subalterno_value.isdigit():
            row_errors.append("Subalterno deve essere numerico se valorizzato.")
        if tipo_visura_value is None:
            row_errors.append("Tipo visura deve essere 'Sintetica' o 'Completa'.")

        if row_errors:
            errors.append({"row_index": row_index, "errors": row_errors, "values": record})
            continue

        assert comune is not None
        assert catasto_value is not None
        assert tipo_visura_value is not None
        validated_rows.append(
            ValidatedVisuraRow(
                row_index=row_index,
                search_mode="immobile",
                comune=comune.nome,
                comune_codice=comune.codice_sister,
                catasto=catasto_value,
                sezione=sezione_value or None,
                foglio=foglio_value,
                particella=particella_value,
                subalterno=subalterno_value or None,
                tipo_visura=tipo_visura_value,
            )
        )

    if errors:
        raise BatchValidationError("File validation failed", errors)
    return validated_rows


def create_batch_from_upload(
    db: Session,
    user_id: int,
    filename: str,
    content: bytes,
    name: str | None = None,
) -> ElaborazioneBatch:
    records = load_upload_records(filename, content)
    rows = validate_visure_records(db, records)
    batch_name = name.strip() if name and name.strip() else Path(filename).stem
    batch, _ = create_batch_from_validated_rows(db, user_id, rows, batch_name, filename)
    return batch


def create_single_visura_batch(
    db: Session,
    user_id: int,
    payload: ElaborazioneRichiestaCreateRequest,
) -> ElaborazioneBatch:
    row = validate_visure_records(db, [payload.model_dump()])[0]
    if row.search_mode == "soggetto":
        batch_name = f"Visura soggetto {row.subject_kind or 'PF'} {row.subject_id}"
    else:
        batch_name = f"Visura singola {row.comune} Fg.{row.foglio} Part.{row.particella}"
    batch, _ = create_batch_from_validated_rows(db, user_id, [row], batch_name, None)
    return start_batch(db, user_id, batch.id)


def create_batch_from_validated_rows(
    db: Session,
    user_id: int,
    rows: list[ValidatedVisuraRow],
    name: str,
    source_filename: str | None,
) -> tuple[ElaborazioneBatch, list[ElaborazioneRichiesta]]:
    batch = ElaborazioneBatch(
        user_id=user_id,
        name=name,
        source_filename=source_filename,
        total_items=len(rows),
        status=ElaborazioneBatchStatus.PENDING.value,
        current_operation="Awaiting start",
        not_found_items=0,
    )
    db.add(batch)
    db.flush()

    requests = [
        ElaborazioneRichiesta(
            batch_id=batch.id,
            user_id=user_id,
            row_index=row.row_index,
            search_mode=row.search_mode,
            comune=row.comune,
            comune_codice=row.comune_codice,
            catasto=row.catasto,
            sezione=row.sezione,
            foglio=row.foglio,
            particella=row.particella,
            subalterno=row.subalterno,
            tipo_visura=row.tipo_visura,
            subject_kind=row.subject_kind,
            subject_id=row.subject_id,
            request_type=row.request_type,
            intestazione=row.intestazione,
            status=row.status,
            current_operation=row.current_operation,
            error_message=row.error_message,
            processed_at=datetime.now(UTC) if row.status == ElaborazioneRichiestaStatus.SKIPPED.value else None,
        )
        for row in rows
    ]
    db.add_all(requests)
    recalculate_batch_counters(batch, requests)
    if batch.skipped_items:
        batch.current_operation = f"{batch.skipped_items} record saltati in import"
    db.commit()
    db.refresh(batch)
    return batch, requests


def expire_stale_pending_batches(db: Session, user_id: int | None = None) -> int:
    timeout_minutes = max(settings.elaborazioni_pending_start_timeout_minutes, 1)
    now = datetime.now(UTC)
    stale_cutoff = now.timestamp() - (timeout_minutes * 60)
    statement = select(ElaborazioneBatch).where(
        ElaborazioneBatch.status == ElaborazioneBatchStatus.PENDING.value,
        ElaborazioneBatch.started_at.is_(None),
        ElaborazioneBatch.completed_at.is_(None),
    )
    if user_id is not None:
        statement = statement.where(ElaborazioneBatch.user_id == user_id)

    stale_batches = list(db.scalars(statement).all())
    expired_count = 0
    for batch in stale_batches:
        reference_at = batch.created_at
        if reference_at is None:
            continue
        if reference_at.tzinfo is None:
            reference_at = reference_at.replace(tzinfo=UTC)
        if reference_at.timestamp() >= stale_cutoff:
            continue

        requests = get_batch_requests(db, batch.id)
        for request in requests:
            if request.status != ElaborazioneRichiestaStatus.PENDING.value:
                continue
            request.status = ElaborazioneRichiestaStatus.FAILED.value
            request.current_operation = "Scaduta prima dell'avvio"
            request.error_message = (
                f"Richiesta non eseguita entro {timeout_minutes} minuti dalla creazione batch."
            )
            request.processed_at = now

        batch.status = ElaborazioneBatchStatus.FAILED.value
        batch.current_operation = f"Batch scaduto prima dell'avvio ({timeout_minutes} min)"
        batch.completed_at = now
        recalculate_batch_counters(batch, requests)
        expired_count += 1

    if expired_count:
        db.commit()
    return expired_count


def list_batches_for_user(db: Session, user_id: int, status: str | None = None) -> list[ElaborazioneBatch]:
    expire_stale_pending_batches(db, user_id)
    statement = select(ElaborazioneBatch).where(ElaborazioneBatch.user_id == user_id)
    if status:
        statement = statement.where(ElaborazioneBatch.status == status)
    return list(db.scalars(statement.order_by(ElaborazioneBatch.created_at.desc())).all())


def get_batch_for_user(db: Session, user_id: int, batch_id: UUID) -> ElaborazioneBatch:
    expire_stale_pending_batches(db, user_id)
    batch = db.scalar(
        select(ElaborazioneBatch).where(ElaborazioneBatch.id == batch_id, ElaborazioneBatch.user_id == user_id),
    )
    if batch is None:
        raise BatchNotFoundError(f"Batch {batch_id} not found")
    return batch


def get_batch_requests(db: Session, batch_id: UUID) -> list[ElaborazioneRichiesta]:
    statement = (
        select(ElaborazioneRichiesta)
        .where(ElaborazioneRichiesta.batch_id == batch_id)
        .order_by(ElaborazioneRichiesta.row_index.asc())
    )
    return list(db.scalars(statement).all())


def get_request_for_user(db: Session, user_id: int, request_id: UUID) -> ElaborazioneRichiesta:
    request = db.scalar(
        select(ElaborazioneRichiesta).where(
            ElaborazioneRichiesta.id == request_id,
            ElaborazioneRichiesta.user_id == user_id,
        ),
    )
    if request is None:
        raise RequestNotFoundError(f"Request {request_id} not found")
    return request


def ensure_no_processing_batch(db: Session, user_id: int, current_batch_id: UUID | None = None) -> None:
    existing = db.scalar(
        select(ElaborazioneBatch).where(
            ElaborazioneBatch.user_id == user_id,
            ElaborazioneBatch.status == ElaborazioneBatchStatus.PROCESSING.value,
        ),
    )
    if existing is not None and existing.id != current_batch_id:
        raise BatchConflictError("Only one processing batch per user is allowed")


def start_batch(db: Session, user_id: int, batch_id: UUID) -> ElaborazioneBatch:
    expire_stale_pending_batches(db, user_id)
    batch = get_batch_for_user(db, user_id, batch_id)
    try:
        require_credentials_for_user(db, user_id)
    except ElaborazioneCredentialNotFoundError as exc:
        raise BatchConflictError(str(exc)) from exc
    ensure_no_processing_batch(db, user_id, current_batch_id=batch.id)

    if batch.status not in {
        ElaborazioneBatchStatus.PENDING.value,
        ElaborazioneBatchStatus.FAILED.value,
        ElaborazioneBatchStatus.CANCELLED.value,
    }:
        raise BatchConflictError(f"Batch cannot be started from status '{batch.status}'")

    requests = get_batch_requests(db, batch.id)
    resumed_after_release = False
    if batch.status == ElaborazioneBatchStatus.CANCELLED.value:
        for request in requests:
            if (
                request.status == ElaborazioneRichiestaStatus.SKIPPED.value
                and request.current_operation == RELEASE_REQUESTED_OPERATION
                and request.error_message == RELEASE_REQUESTED_MESSAGE
            ):
                request.status = ElaborazioneRichiestaStatus.PENDING.value
                request.current_operation = "Queued after release"
                request.error_message = None
                request.processed_at = None
                request.document_id = None
                request.captcha_manual_solution = None
                request.captcha_skip_requested = False
                request.captcha_requested_at = None
                request.captcha_expires_at = None
                request.captcha_image_path = None
                resumed_after_release = True

        if not resumed_after_release:
            raise BatchConflictError("No released requests available to resume")

    batch.status = ElaborazioneBatchStatus.PROCESSING.value
    batch.started_at = batch.started_at or datetime.now(UTC)
    batch.completed_at = None
    batch.current_operation = "Queued after release" if resumed_after_release else "Queued for worker"
    batch.report_json_path = None
    batch.report_md_path = None
    recalculate_batch_counters(batch, requests)
    db.commit()
    db.refresh(batch)
    return batch


def cancel_batch(db: Session, user_id: int, batch_id: UUID) -> ElaborazioneBatch:
    expire_stale_pending_batches(db, user_id)
    batch = get_batch_for_user(db, user_id, batch_id)
    if batch.status in {ElaborazioneBatchStatus.COMPLETED.value, ElaborazioneBatchStatus.CANCELLED.value}:
        raise BatchConflictError(f"Batch cannot be cancelled from status '{batch.status}'")

    now = datetime.now(UTC)
    requests = get_batch_requests(db, batch.id)
    for request in requests:
        if request.status in {
            ElaborazioneRichiestaStatus.PENDING.value,
            ElaborazioneRichiestaStatus.PROCESSING.value,
            ElaborazioneRichiestaStatus.AWAITING_CAPTCHA.value,
        }:
            request.status = ElaborazioneRichiestaStatus.SKIPPED.value
            request.current_operation = "Cancelled"
            request.error_message = "Batch cancelled by user"
            request.processed_at = now
    batch.status = ElaborazioneBatchStatus.CANCELLED.value
    batch.completed_at = now
    batch.current_operation = "Cancelled by user"
    recalculate_batch_counters(batch, requests)
    db.commit()
    db.refresh(batch)
    return batch


def release_processing_batches_for_user(db: Session, user_id: int) -> tuple[int, list[UUID]]:
    expire_stale_pending_batches(db, user_id)
    batches = list(
        db.scalars(
            select(ElaborazioneBatch).where(
                ElaborazioneBatch.user_id == user_id,
                ElaborazioneBatch.status == ElaborazioneBatchStatus.PROCESSING.value,
            )
        ).all()
    )
    if not batches:
        return 0, []

    released_ids: list[UUID] = []
    now = datetime.now(UTC)
    for batch in batches:
        requests = get_batch_requests(db, batch.id)
        for request in requests:
            if request.status in {
                ElaborazioneRichiestaStatus.PENDING.value,
                ElaborazioneRichiestaStatus.PROCESSING.value,
                ElaborazioneRichiestaStatus.AWAITING_CAPTCHA.value,
            }:
                request.status = ElaborazioneRichiestaStatus.SKIPPED.value
                request.current_operation = RELEASE_REQUESTED_OPERATION
                request.error_message = RELEASE_REQUESTED_MESSAGE
                request.processed_at = now
        batch.status = ElaborazioneBatchStatus.CANCELLED.value
        batch.completed_at = now
        batch.current_operation = RELEASE_REQUESTED_OPERATION
        recalculate_batch_counters(batch, requests)
        released_ids.append(batch.id)

    db.commit()
    return len(released_ids), released_ids


def retry_failed_batch(db: Session, user_id: int, batch_id: UUID) -> ElaborazioneBatch:
    expire_stale_pending_batches(db, user_id)
    batch = get_batch_for_user(db, user_id, batch_id)
    if batch.status == ElaborazioneBatchStatus.PROCESSING.value:
        raise BatchConflictError("Cannot retry failed items while batch is processing")

    requests = get_batch_requests(db, batch.id)
    retried = False
    retry_queued_at = datetime.now(UTC)
    for request in requests:
        if request.status == ElaborazioneRichiestaStatus.FAILED.value:
            request.status = ElaborazioneRichiestaStatus.PENDING.value
            request.current_operation = "Queued for retry"
            request.error_message = None
            request.processed_at = None
            request.document_id = None
            request.captcha_manual_solution = None
            request.captcha_skip_requested = False
            request.captcha_requested_at = None
            request.captcha_expires_at = None
            request.captcha_image_path = None
            retried = True

    if not retried:
        raise BatchConflictError("No failed requests available for retry")

    batch.status = ElaborazioneBatchStatus.PENDING.value
    # Re-queued batches must not be expired immediately using the original creation timestamp.
    batch.started_at = retry_queued_at
    batch.completed_at = None
    batch.current_operation = "Retry queued"
    batch.report_json_path = None
    batch.report_md_path = None
    recalculate_batch_counters(batch, requests)
    db.commit()
    db.refresh(batch)
    return batch


def recalculate_batch_counters(batch: ElaborazioneBatch, requests: list[ElaborazioneRichiesta]) -> None:
    batch.total_items = len(requests)
    batch.completed_items = sum(1 for item in requests if item.status == ElaborazioneRichiestaStatus.COMPLETED.value)
    batch.failed_items = sum(1 for item in requests if item.status == ElaborazioneRichiestaStatus.FAILED.value)
    batch.skipped_items = sum(1 for item in requests if item.status == ElaborazioneRichiestaStatus.SKIPPED.value)
    batch.not_found_items = sum(1 for item in requests if item.status == ElaborazioneRichiestaStatus.NOT_FOUND.value)


def sync_batch_counters(
    db: Session,
    batch: ElaborazioneBatch,
    requests: list[ElaborazioneRichiesta] | None = None,
) -> bool:
    requests = requests if requests is not None else get_batch_requests(db, batch.id)
    previous = (
        batch.total_items,
        batch.completed_items,
        batch.failed_items,
        batch.skipped_items,
        batch.not_found_items,
    )
    recalculate_batch_counters(batch, requests)
    current = (
        batch.total_items,
        batch.completed_items,
        batch.failed_items,
        batch.skipped_items,
        batch.not_found_items,
    )
    if current != previous:
        db.commit()
        db.refresh(batch)
        return True
    return False


def get_runtime_metrics_for_user(db: Session, user_id: int) -> dict[str, object]:
    now = datetime.now(UTC)
    requests = list(
        db.scalars(
            select(ElaborazioneRichiesta).where(ElaborazioneRichiesta.user_id == user_id)
        ).all()
    )
    batches = list_batches_for_user(db, user_id)

    for batch in batches:
        sync_batch_counters(db, batch)

    terminal_statuses = {
        ElaborazioneRichiestaStatus.COMPLETED.value,
        ElaborazioneRichiestaStatus.FAILED.value,
        ElaborazioneRichiestaStatus.SKIPPED.value,
        ElaborazioneRichiestaStatus.NOT_FOUND.value,
    }

    def build_block(lookback_hours: int | None = None) -> dict[str, object]:
        relevant_requests = requests
        relevant_batches = batches
        if lookback_hours is not None:
            cutoff = now - timedelta(hours=lookback_hours)
            relevant_requests = [
                item for item in requests
                if _as_utc(item.processed_at) is not None and _as_utc(item.processed_at) >= cutoff
            ]
            relevant_batches = [
                item for item in batches
                if _as_utc(item.completed_at) is not None and _as_utc(item.completed_at) >= cutoff
            ]

        completed = sum(1 for item in relevant_requests if item.status == ElaborazioneRichiestaStatus.COMPLETED.value)
        failed = sum(1 for item in relevant_requests if item.status == ElaborazioneRichiestaStatus.FAILED.value)
        skipped = sum(1 for item in relevant_requests if item.status == ElaborazioneRichiestaStatus.SKIPPED.value)
        not_found = sum(1 for item in relevant_requests if item.status == ElaborazioneRichiestaStatus.NOT_FOUND.value)
        processed = sum(1 for item in relevant_requests if item.status in terminal_statuses)

        request_durations: list[float] = []
        for item in relevant_requests:
            created_at = _as_utc(item.created_at)
            processed_at = _as_utc(item.processed_at)
            if created_at is None or processed_at is None:
                continue
            request_durations.append(max((processed_at - created_at).total_seconds(), 0.0))

        batch_durations: list[float] = []
        for item in relevant_batches:
            started_at = _as_utc(item.started_at)
            completed_at = _as_utc(item.completed_at)
            if started_at is None or completed_at is None:
                continue
            batch_durations.append(max((completed_at - started_at).total_seconds() / 60, 0.0))

        throughput = None
        if lookback_hours:
            throughput = round(processed / lookback_hours, 2)

        success_rate = None
        if processed > 0:
            success_rate = round((completed / processed) * 100, 2)

        latest_processed_at = None
        processed_times = [_as_utc(item.processed_at) for item in relevant_requests if _as_utc(item.processed_at) is not None]
        if processed_times:
            latest_processed_at = max(processed_times)

        return {
            "batches_total": len(relevant_batches),
            "requests_total": len(relevant_requests),
            "requests_completed": completed,
            "requests_failed": failed,
            "requests_skipped": skipped,
            "requests_not_found": not_found,
            "processed_requests": processed,
            "success_rate": success_rate,
            "throughput_per_hour": throughput,
            "average_batch_duration_minutes": round(sum(batch_durations) / len(batch_durations), 2) if batch_durations else None,
            "average_request_duration_seconds": round(sum(request_durations) / len(request_durations), 2) if request_durations else None,
            "latest_processed_at": latest_processed_at,
        }

    recent_daily: list[dict[str, object]] = []
    operation_window = _get_operation_window_snapshot(now)
    try:
        metrics_tz = ZoneInfo(str(operation_window["timezone"]))
    except Exception:
        metrics_tz = ZoneInfo("Europe/Rome")

    daily_rows: dict[str, Counter[str]] = {}
    for item in requests:
        processed_at = _as_utc(item.processed_at)
        if processed_at is None or processed_at < now - timedelta(days=7):
            continue
        day_key = processed_at.astimezone(metrics_tz).date().isoformat()
        counter = daily_rows.setdefault(day_key, Counter())
        counter["processed_requests"] += 1
        counter[item.status] += 1

    for day_key in sorted(daily_rows.keys(), reverse=True):
        counter = daily_rows[day_key]
        recent_daily.append(
            {
                "date": day_key,
                "processed_requests": counter.get("processed_requests", 0),
                "completed": counter.get(ElaborazioneRichiestaStatus.COMPLETED.value, 0),
                "failed": counter.get(ElaborazioneRichiestaStatus.FAILED.value, 0),
                "skipped": counter.get(ElaborazioneRichiestaStatus.SKIPPED.value, 0),
                "not_found": counter.get(ElaborazioneRichiestaStatus.NOT_FOUND.value, 0),
            }
        )

    return {
        "operating_window": operation_window,
        "totals": build_block(),
        "last_24_hours": build_block(24),
        "last_7_days": build_block(24 * 7),
        "recent_daily": recent_daily,
    }
