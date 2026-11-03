"""Account routing, immutable template versions and operator configuration audit."""

from uuid import uuid4

from sqlalchemy import func, select

from .models import CommunicationAccount, CommunicationJob, CommunicationTemplate
from .policy import Conflict, Missing, now, render_template
from .store import event

VARIABLES = {
    key: "esempio"
    for key in ("contribuente_nome", "numero_avviso", "anno_tributario", "importo", "ente_nome")
}


def account(db, identity):
    value = db.scalar(
        select(CommunicationAccount)
        .where(CommunicationAccount.id == identity)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if value is None:
        raise Missing("Account non trovato")
    return value


def allowed(value, channel, actor_id):
    return (
        value.active
        and value.channel == channel
        and "ruolo" in value.allowed_modules
        and (not value.allowed_user_ids or actor_id in value.allowed_user_ids)
    )


def route_account(db, channel, actor_id, explicit=None):
    if explicit:
        value = account(db, explicit)
        if not allowed(value, channel, actor_id):
            raise Conflict("Account disabilitato, canale errato o utilizzo non autorizzato")
        return value
    values = db.scalars(
        select(CommunicationAccount)
        .where(CommunicationAccount.channel == channel, CommunicationAccount.active.is_(True))
        .order_by(CommunicationAccount.priority, CommunicationAccount.id)
    )
    usable = [value for value in values if allowed(value, channel, actor_id)]
    for value in usable:
        if "ruolo" in value.default_modules:
            return value
    for value in usable:
        if value.is_default:
            return value
    raise Conflict("Nessun account predefinito autorizzato per il canale")


def save_account(db, payload, actor_id, identity=None):
    value = account(db, identity) if identity else CommunicationAccount(id=uuid4())
    if identity and value.version != payload.expected_version:
        raise Conflict("Configurazione account obsoleta")
    fields = payload.model_dump(exclude={"expected_version"})
    for key, field in fields.items():
        setattr(value, key, field)
    value.version = value.version + 1 if identity else 1
    value.health = "untested"
    db.add(value)
    db.flush()
    event(
        db,
        value.id,
        "account_changed",
        actor_id=actor_id,
        version=value.version,
        changed_fields=sorted(fields),
    )
    return value


def create_template(db, payload, actor_id):
    render_template(payload.subject, VARIABLES)
    render_template(payload.body, VARIABLES)
    if "\n" in payload.subject or "\r" in payload.subject:
        raise Conflict("Oggetto template non valido")
    version = (
        db.scalar(
            select(func.max(CommunicationTemplate.version)).where(
                CommunicationTemplate.code == payload.code
            )
        )
        or 0
    ) + 1
    value = CommunicationTemplate(**payload.model_dump(), version=version)
    db.add(value)
    db.flush()
    event(db, value.id, "template_created", actor_id=actor_id, version=version)
    return value


def approved_template(db, identity, channel):
    template = db.get(CommunicationTemplate, identity)
    if (
        template is None
        or template.status != "approved"
        or template.module != "ruolo"
        or template.channel != channel
    ):
        raise Conflict("Template non approvato o incompatibile")
    return template


def approve_template(db, identity, actor_id):
    value = db.scalar(
        select(CommunicationTemplate).where(CommunicationTemplate.id == identity).with_for_update()
    )
    if value is None:
        raise Missing("Template non trovato")
    if value.status != "draft":
        raise Conflict("Solo una versione bozza può essere approvata")
    value.status, value.approved_by, value.approved_at = "approved", actor_id, now()
    event(db, value.id, "template_approved", actor_id=actor_id)
    return value


def request_account_job(db, identity, kind, actor_id):
    value = account(db, identity)
    job = CommunicationJob(account_id=value.id, kind=kind, idempotency_key=str(uuid4()))
    db.add(job)
    db.flush()
    event(
        db, value.id, "account_job_requested", actor_id=actor_id, job_id=str(job.id), job_kind=kind
    )
    return job
