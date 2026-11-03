"""Append-only campaign snapshots in the existing private draft archive, never the ledger."""

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modules.ruolo.notice_draft_models import NoticeDraft
from app.modules.ruolo.services.campaign_2021_excel import parse_excel
from app.modules.ruolo.services.campaign_2021_pdf import build_payload, render_preview
from app.modules.ruolo.services.campaign_2021_read_model import read_positions
from app.modules.ruolo.services.campaign_2021_reconciliation import reconcile
from app.modules.ruolo.services.notice_import_excel import digest, json_bytes
from app.modules.ruolo.services.notice_register import RegisterConflict, RegisterNotFound

IMPORT = "campaign_2021_import"
APPROVAL = "campaign_2021_approval"
PREVIEW = "campaign_2021_preview"


def code_sha256() -> str:
    sources = sorted(Path(__file__).parent.glob("campaign_2021*.py"))
    sources.extend(
        Path(__file__).parent / name
        for name in ("notice_summary.py", "tributi_reminder_service.py")
    )
    return digest(b"".join(p.name.encode() + p.read_bytes() for p in sources))


def analyze(db, content: bytes) -> dict:
    parsed = parse_excel(content)
    facts = read_positions(db, parsed["rows"])
    rows = [
        {
            **row,
            "current": facts[row["number"]],
            "reconciliation": reconcile(row, facts[row["number"]], parsed["summary"]["parameters"]),
        }
        for row in parsed["rows"]
    ]
    result = {
        **parsed,
        "rows": rows,
        "code_sha256": code_sha256(),
        "code_reference": "686e529e",
        "outcomes": dict(Counter(row["reconciliation"]["kind"] for row in rows)),
    }
    return {
        **result,
        "report_sha256": digest(json_bytes(result)),
        "acquired_at": datetime.now(UTC).isoformat(),
    }


def _find(db, source, source_id):
    return db.scalar(
        select(NoticeDraft).where(
            NoticeDraft.source_system == source, NoticeDraft.source_id == source_id
        )
    )


def _save(db, source, key, manifest, content, actor_id):
    source_id = uuid5(NAMESPACE_URL, f"gaia:{source}:{key}")
    existing = _find(db, source, source_id)
    if existing is not None:
        return existing
    record = NoticeDraft(
        source_system=source,
        source_id=source_id,
        actor_id=actor_id,
        manifest=manifest,
        artifact=content,
        artifact_format={IMPORT: "xlsx", APPROVAL: "json", PREVIEW: "pdf"}[source],
        artifact_sha256=digest(content),
        input_basis={"campaign_2021": True},
    )
    try:
        with db.begin_nested():
            db.add(record)
            db.flush()
    except IntegrityError:
        existing = _find(db, source, source_id)
        if existing is None:
            raise
        return existing
    return record


def require(db, record_id: UUID, source: str):
    record = db.get(NoticeDraft, record_id)
    if record is None or record.source_system != source:
        raise RegisterNotFound("Snapshot della campagna 2021 non trovato")
    if digest(record.artifact) != record.artifact_sha256:
        raise RegisterConflict("Snapshot della campagna non integro")
    return record


def stage(db, content, filename, expected_hash, actor_id):
    report = analyze(db, content)
    if report["report_sha256"] != expected_hash:
        raise RegisterConflict("Dati cambiati dopo l'analisi: ripetere il confronto")
    record = _save(
        db, IMPORT, expected_hash, {**report, "filename": filename[:255]}, content, actor_id
    )
    return view(record)


def view(record):
    return {
        "id": str(record.id),
        "actor_id": record.actor_id,
        "created_at": str(record.created_at),
        **record.manifest,
    }


def list_campaigns(db):
    records = db.scalars(
        select(NoticeDraft)
        .where(NoticeDraft.source_system == IMPORT)
        .order_by(NoticeDraft.created_at.desc(), NoticeDraft.id)
        .limit(100)
    ).all()
    return [
        {
            "id": str(r.id),
            "filename": r.manifest["filename"],
            "created_at": str(r.created_at),
            "summary": r.manifest["summary"],
        }
        for r in records
    ]


def _fresh(db, row):
    db.expire_all()
    db.info.pop("ruolo_step_assigned_avviso_ids", None)
    facts = read_positions(db, [row])[row["number"]]
    if facts["sha256"] != row["current"]["sha256"]:
        raise RegisterConflict("Posizione, policy o storico cambiati: acquisire un nuovo snapshot")


def approve(db, campaign_id, command, actor_id):
    campaign = require(db, campaign_id, IMPORT)
    report = campaign.manifest
    if command.report_sha256 != report["report_sha256"] or report["code_sha256"] != code_sha256():
        raise RegisterConflict("Versione del report o del codice cambiata")
    rows = [r for r in report["rows"] if r["row"] == command.row_number]
    if len(rows) != 1:
        raise ValueError("Riga della campagna assente o ambigua")
    row = rows[0]
    checks = row["reconciliation"]
    if checks["blockers"]:
        raise ValueError("Posizione bloccata: " + ", ".join(checks["blockers"]))
    if not set(checks["reviews"]) <= set(command.resolutions):
        raise ValueError("Riferimento di verifica obbligatorio per ogni differenza")
    if command.notification_fee != "0.00" and command.channel != "raccomandata":
        raise ValueError("Spese di notifica incoerenti con il canale approvato")
    _fresh(db, row)
    approved_at = datetime.now(UTC).isoformat()
    payload = build_payload(db, row, row["current"], command, approved_at)
    key = digest(json_bytes({"campaign": str(campaign_id), "command": command.model_dump()}))
    record = _save(
        db,
        APPROVAL,
        key,
        {
            "campaign_id": str(campaign_id),
            "row": row,
            "approval": command.model_dump(),
            "approved_at": approved_at,
            "payload": payload,
            "code_sha256": report["code_sha256"],
            "state": "snapshot_contabile_approvato",
        },
        json_bytes(payload),
        actor_id,
    )
    return {
        "id": str(record.id),
        "state": record.manifest["state"],
        "actor_id": record.actor_id,
        "approved_at": record.manifest["approved_at"],
        "sent": False,
        "notified": False,
    }


def preview(db, approval_id, actor_id):
    approval = require(db, approval_id, APPROVAL)
    manifest = approval.manifest
    if manifest["code_sha256"] != code_sha256():
        raise RegisterConflict("Codice cambiato: serve nuova approvazione")
    _fresh(db, manifest["row"])
    key = str(approval.id)
    existing = _find(db, PREVIEW, uuid5(NAMESPACE_URL, f"gaia:{PREVIEW}:{key}"))
    if existing is not None:
        return require(db, existing.id, PREVIEW).artifact
    content = render_preview(manifest["payload"])
    return _save(
        db,
        PREVIEW,
        key,
        {"approval_id": key, "state": "anteprima_generata", "sent": False, "notified": False},
        content,
        actor_id,
    ).artifact
