"""One resolver for list filters, composition and the authorization fingerprint.

A typed contact works for people and companies. A legacy field remains usable
only until that address/channel is classified. Multiple active addresses are
ambiguous: the operator must review them, never pick an arbitrary recipient.
"""

from sqlalchemy import case, exists, func, or_, select

from app.modules.utenze.contact_models import AnagraficaElectronicContact as Contact
from app.modules.utenze.models import (
    AnagraficaAuditLog,
    AnagraficaCompany,
    AnagraficaPerson,
    AnagraficaSubject,
)


class ContactConflict(ValueError):
    pass


class ContactMissing(LookupError):
    pass


def resolved_address(subject_id, channel, legacy):
    relevant = Contact.subject_id == subject_id
    typed = (
        select(case((func.count(Contact.id) == 1, func.max(Contact.address))))
        .where(relevant, Contact.channel == channel, Contact.state == "active")
        .correlate_except(Contact)
        .scalar_subquery()
    )
    classified = (
        exists()
        .where(
            relevant,
            or_(Contact.channel == channel, Contact.address == func.lower(func.trim(legacy))),
        )
        .correlate_except(Contact)
    )
    return case((classified, typed), else_=func.nullif(func.trim(legacy), ""))


def contact_columns(subject_id):
    return {
        "email": resolved_address(subject_id, "email", AnagraficaPerson.email),
        "pec": resolved_address(subject_id, "pec", AnagraficaCompany.email_pec),
    }


def contact_values(db, subject_id):
    subject = AnagraficaSubject
    row = db.execute(
        select(*contact_columns(subject.id).values())
        .select_from(subject)
        .outerjoin(AnagraficaPerson, AnagraficaPerson.subject_id == subject.id)
        .outerjoin(AnagraficaCompany, AnagraficaCompany.subject_id == subject.id)
        .where(subject.id == subject_id)
    ).one_or_none()
    return {"email": row[0], "pec": row[1]} if row else {"email": None, "pec": None}


def public_contact(value):
    return {
        key: getattr(value, key)
        for key in (
            "id",
            "subject_id",
            "address",
            "channel",
            "state",
            "source",
            "evidence_reference",
            "version",
            "updated_by",
            "updated_at",
        )
    }


def classify(db, subject_id, payload, actor_id):
    subject = db.scalar(
        select(AnagraficaSubject).where(AnagraficaSubject.id == subject_id).with_for_update()
    )
    if subject is None:
        raise ContactMissing("Anagrafica non trovata")
    if subject.status != "active":
        raise ContactConflict("Anagrafica non attiva")
    contact = db.scalar(
        select(Contact)
        .where(Contact.subject_id == subject_id, Contact.address == payload.address)
        .execution_options(populate_existing=True)
    )
    current_version = contact.version if contact else 0
    if payload.expected_version != current_version:
        raise ContactConflict("Recapito modificato: ricaricare la classificazione")
    before = public_contact(contact) if contact else None
    if contact is None:
        contact = Contact(subject_id=subject_id, address=payload.address)
        db.add(contact)
    for key in ("channel", "state", "source", "evidence_reference"):
        setattr(contact, key, getattr(payload, key))
    contact.version = current_version + 1
    contact.updated_by = actor_id
    db.flush()
    db.add(
        AnagraficaAuditLog(
            subject_id=subject_id,
            changed_by_user_id=actor_id,
            action="electronic_contact_classified",
            diff_json={
                "address": contact.address,
                "before": _audit_state(before),
                "after": _audit_state(public_contact(contact)),
            },
        )
    )
    db.flush()
    return contact


def _audit_state(value):
    if value is None:
        return None
    return {
        key: value[key]
        for key in ("address", "channel", "state", "source", "evidence_reference", "version")
    }
