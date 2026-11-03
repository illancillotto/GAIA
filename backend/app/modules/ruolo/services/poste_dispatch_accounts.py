"""The Poste account of a lot is explicit and immutable, including for reconciliation."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.posta_online import PostaOnlineCredential, PostaOnlineRegisteredMailSyncJob
from app.modules.ruolo.poste_dispatch_models import PosteDispatchLot
from app.modules.ruolo.services.poste_dispatch_state import DispatchConflict, get_lot


def list_accounts(db: Session) -> list[dict]:
    return [
        {"id": c.id, "label": c.label, "username": c.username, "active": c.active}
        for c in db.scalars(select(PostaOnlineCredential).order_by(PostaOnlineCredential.label))
    ]


def selected_account(db: Session, credential_id: int) -> PostaOnlineCredential:
    credential = db.get(PostaOnlineCredential, credential_id)
    if credential is None or not credential.active:
        raise DispatchConflict("Account Poste inesistente o non attivo")
    return credential


def assign_account(lot: PosteDispatchLot, credential: PostaOnlineCredential) -> None:
    if lot.credential_id is not None:
        raise DispatchConflict("L'account Poste del lotto non può essere cambiato")
    lot.credential_id = credential.id
    lot.poste_username = credential.username
    lot.credential_label = credential.label


def lot_account(db: Session, lot: PosteDispatchLot) -> PostaOnlineCredential:
    if lot.credential_id is None:
        raise DispatchConflict("Associare esplicitamente un account Poste al lotto storico")
    credential = selected_account(db, lot.credential_id)
    if credential.username != lot.poste_username:
        raise DispatchConflict("Lo username della credenziale non coincide con l'account del lotto")
    return credential


def job_account(db: Session, job: PostaOnlineRegisteredMailSyncJob) -> PosteDispatchLot:
    lot = get_lot(db, UUID((job.payload_json or {})["lot_id"]))
    credential = lot_account(db, lot)
    if (
        job.credential_id != credential.id
        or (job.payload_json or {}).get("poste_username") != lot.poste_username
    ):
        raise DispatchConflict("Account del job Poste diverso da quello del lotto")
    return lot


def checked_job(db: Session, lot_id: UUID, job_id: int) -> PostaOnlineRegisteredMailSyncJob:
    job = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
    if job is None or job_account(db, job).id != lot_id:
        raise DispatchConflict("Operazione Poste non coerente con l'account dell'avviso")
    return job
