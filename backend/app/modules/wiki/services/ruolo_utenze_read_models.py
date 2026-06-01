from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser


def get_utenze_stats_read_model(db: Session, current_user: ApplicationUser) -> dict[str, object]:
    from app.modules.utenze.router import get_stats

    response = get_stats(_=current_user, __=current_user, db=db)
    return response.model_dump(mode="json")


def get_ruolo_dashboard_summary_read_model(db: Session, current_user: ApplicationUser) -> dict[str, object]:
    from app.modules.ruolo.routes.query_routes import get_stats

    response = get_stats(anno=None, db=db, current_user=current_user)
    return response.model_dump(mode="json")


def get_utenze_subject_by_identifier_read_model(
    db: Session,
    current_user: ApplicationUser,
    identifier: str,
) -> dict[str, object] | None:
    from app.modules.utenze.models import AnagraficaCompany, AnagraficaPerson
    from app.modules.utenze.router import _build_subject_detail
    from app.modules.utenze.services.subject_identity import is_probable_vat_number

    subject_id = None
    if is_probable_vat_number(identifier):
        company = db.scalar(
            select(AnagraficaCompany).where(
                (func.upper(func.replace(AnagraficaCompany.partita_iva, " ", "")) == identifier)
                | (func.upper(func.replace(func.coalesce(AnagraficaCompany.codice_fiscale, ""), " ", "")) == identifier)
            )
        )
        if company is not None:
            subject_id = company.subject_id
    else:
        person = db.scalar(
            select(AnagraficaPerson).where(func.upper(func.replace(AnagraficaPerson.codice_fiscale, " ", "")) == identifier)
        )
        if person is not None:
            subject_id = person.subject_id
        else:
            company = db.scalar(
                select(AnagraficaCompany).where(
                    func.upper(func.replace(func.coalesce(AnagraficaCompany.codice_fiscale, ""), " ", "")) == identifier
                )
            )
            if company is not None:
                subject_id = company.subject_id

    if subject_id is None:
        return None

    response = _build_subject_detail(db, subject_id)
    display_name = (
        f"{response.person.nome} {response.person.cognome}" if response.person is not None
        else response.company.ragione_sociale if response.company is not None
        else response.source_name_raw or str(response.id)
    )
    return {
        "id": str(response.id),
        "display_name": display_name,
        "status": response.status,
        "subject_type": response.subject_type,
        "requires_review": response.requires_review,
        "documents_count": len(response.documents),
    }


def get_ruolo_subject_by_identifier_read_model(
    db: Session,
    current_user: ApplicationUser,
    identifier: str,
) -> dict[str, object] | None:
    from app.modules.ruolo.models import RuoloAvviso
    from app.modules.utenze.models import AnagraficaCompany, AnagraficaPerson
    from app.modules.utenze.services.subject_identity import is_probable_vat_number

    subject_id = None
    display_name = None
    if is_probable_vat_number(identifier):
        company = db.scalar(
            select(AnagraficaCompany).where(
                (func.upper(func.replace(AnagraficaCompany.partita_iva, " ", "")) == identifier)
                | (func.upper(func.replace(func.coalesce(AnagraficaCompany.codice_fiscale, ""), " ", "")) == identifier)
            )
        )
        if company is not None:
            subject_id = company.subject_id
            display_name = company.ragione_sociale
    else:
        person = db.scalar(
            select(AnagraficaPerson).where(func.upper(func.replace(AnagraficaPerson.codice_fiscale, " ", "")) == identifier)
        )
        if person is not None:
            subject_id = person.subject_id
            display_name = f"{person.nome} {person.cognome}".strip()

    if subject_id is None:
        return None

    avvisi = db.scalars(
        select(RuoloAvviso)
        .where(RuoloAvviso.subject_id == subject_id)
        .order_by(RuoloAvviso.anno_tributario.desc(), RuoloAvviso.codice_cnc.desc())
    ).all()
    total_importo = sum(float(item.importo_totale_euro or 0) for item in avvisi)
    return {
        "subject_id": str(subject_id),
        "display_name": display_name,
        "identifier": identifier,
        "avvisi_count": len(avvisi),
        "linked_count": len([item for item in avvisi if item.subject_id is not None]),
        "unlinked_count": len([item for item in avvisi if item.subject_id is None]),
        "total_importo": total_importo,
        "latest_items": [
            {
                "id": str(item.id),
                "anno_tributario": item.anno_tributario,
                "codice_cnc": item.codice_cnc,
                "importo_totale_euro": float(item.importo_totale_euro or 0),
            }
            for item in avvisi[:5]
        ],
    }


def get_ruolo_subject_by_reference_read_model(
    db: Session,
    current_user: ApplicationUser,
    reference: str,
) -> dict[str, object] | None:
    import uuid

    from app.modules.ruolo.models import RuoloAvviso

    try:
        subject_id = uuid.UUID(reference)
    except ValueError:
        return get_ruolo_subject_by_identifier_read_model(db, current_user, reference)

    avvisi = db.scalars(
        select(RuoloAvviso)
        .where(RuoloAvviso.subject_id == subject_id)
        .order_by(RuoloAvviso.anno_tributario.desc(), RuoloAvviso.codice_cnc.desc())
    ).all()
    if not avvisi:
        return None
    total_importo = sum(float(item.importo_totale_euro or 0) for item in avvisi)
    return {
        "subject_id": str(subject_id),
        "display_name": None,
        "identifier": reference,
        "avvisi_count": len(avvisi),
        "linked_count": len(avvisi),
        "unlinked_count": 0,
        "total_importo": total_importo,
        "latest_items": [
            {
                "id": str(item.id),
                "anno_tributario": item.anno_tributario,
                "codice_cnc": item.codice_cnc,
                "importo_totale_euro": float(item.importo_totale_euro or 0),
            }
            for item in avvisi[:5]
        ],
    }
