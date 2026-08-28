from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.models.catasto import CatastoDocument
from app.models.catasto_phase1 import CatParticella, CatUtenzaIntestatario, CatUtenzaIrrigua
from app.modules.ruolo.models import RuoloAvviso
from app.modules.search.schemas import OperationalSearchResponse, OperationalSearchResult, SearchModule
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPaymentNotice, AnagraficaPerson


_MODULE_PRIORITY: dict[SearchModule, int] = {"utenze": 0, "ruolo": 1, "catasto": 2}
_SUBJECT_RESULT_TYPES = frozenset({"subject_person", "subject_company"})


def search_operational(db: Session, current_user: ApplicationUser, query: str, limit: int = 12) -> OperationalSearchResponse:
    normalized = _normalize_query(query)
    if not normalized:
        return OperationalSearchResponse(query="", items=[], total=0, modules=[])

    module_hits: list[OperationalSearchResult] = []
    modules: list[SearchModule] = []
    per_module_limit = max(limit, 3)

    if _can_search_module(current_user, "utenze"):
        modules.append("utenze")
        module_hits.extend(_search_utenze(db, normalized, per_module_limit))
    if _can_search_module(current_user, "ruolo"):
        modules.append("ruolo")
        module_hits.extend(_search_ruolo(db, normalized, per_module_limit))
    if _can_search_module(current_user, "catasto"):
        modules.append("catasto")
        module_hits.extend(_search_catasto(db, normalized, per_module_limit))

    items = _sort_results(module_hits, limit)
    return OperationalSearchResponse(query=normalized, items=items, total=len(items), modules=modules)


def _normalize_query(query: str) -> str:
    return " ".join(query.strip().split())


def _sort_results(items: list[OperationalSearchResult], limit: int) -> list[OperationalSearchResult]:
    return sorted(
        items,
        key=lambda item: (
            _MODULE_PRIORITY[item.module],
            0 if item.type in _SUBJECT_RESULT_TYPES else 1,
            -item.score,
            item.title.lower(),
        ),
    )[:limit]


def _can_search_module(user: ApplicationUser, module: SearchModule) -> bool:
    return user.is_super_admin or module in user.enabled_modules


def _contains(column: Any, query: str) -> Any:
    return func.lower(func.coalesce(column, "")).contains(query.lower())


def _query_tokens(query: str) -> list[str]:
    return [token for token in query.lower().split() if token]


def _matches_tokens(columns: Iterable[Any], query: str) -> Any:
    tokens = _query_tokens(query)
    return and_(*(or_(*(_contains(column, token) for column in columns)) for token in tokens))


def _score(query: str, values: Iterable[str | None]) -> int:
    normalized_query = query.lower()
    best = 0
    for raw in values:
        value = (raw or "").strip().lower()
        if not value:
            continue
        if value == normalized_query:
            best = max(best, 100)
        elif value.startswith(normalized_query):
            best = max(best, 86)
        elif normalized_query in value:
            best = max(best, 68)
        elif all(token in value for token in normalized_query.split()):
            best = max(best, 64)
    return best or 40


def _clean_parts(*values: object | None) -> str:
    return " · ".join(str(value) for value in values if value not in (None, ""))


def _search_utenze(db: Session, query: str, limit: int) -> list[OperationalSearchResult]:
    hits: list[OperationalSearchResult] = []

    people = db.scalars(
        select(AnagraficaPerson)
        .where(
            or_(
                _contains(AnagraficaPerson.codice_fiscale, query),
                _contains(AnagraficaPerson.cognome, query),
                _contains(AnagraficaPerson.nome, query),
                _matches_tokens(
                    [AnagraficaPerson.codice_fiscale, AnagraficaPerson.cognome, AnagraficaPerson.nome],
                    query,
                ),
            )
        )
        .order_by(AnagraficaPerson.cognome, AnagraficaPerson.nome)
        .limit(limit)
    ).all()
    for person in people:
        title = _clean_parts(person.cognome, person.nome)
        hits.append(
            OperationalSearchResult(
                id=str(person.subject_id),
                module="utenze",
                type="subject_person",
                title=title,
                subtitle="Utenze · Persona",
                description=_clean_parts(person.codice_fiscale, person.comune_residenza),
                href=f"/utenze/{person.subject_id}",
                score=_score(query, [person.codice_fiscale, person.cognome, person.nome, title]),
                metadata={"subject_id": str(person.subject_id), "codice_fiscale": person.codice_fiscale},
            )
        )

    companies = db.scalars(
        select(AnagraficaCompany)
        .where(
            or_(
                _contains(AnagraficaCompany.ragione_sociale, query),
                _contains(AnagraficaCompany.partita_iva, query),
                _contains(AnagraficaCompany.codice_fiscale, query),
                _matches_tokens(
                    [AnagraficaCompany.ragione_sociale, AnagraficaCompany.partita_iva, AnagraficaCompany.codice_fiscale],
                    query,
                ),
            )
        )
        .order_by(AnagraficaCompany.ragione_sociale)
        .limit(limit)
    ).all()
    for company in companies:
        hits.append(
            OperationalSearchResult(
                id=str(company.subject_id),
                module="utenze",
                type="subject_company",
                title=company.ragione_sociale,
                subtitle="Utenze · Azienda",
                description=_clean_parts(company.partita_iva, company.codice_fiscale, company.comune_sede),
                href=f"/utenze/{company.subject_id}",
                score=_score(query, [company.ragione_sociale, company.partita_iva, company.codice_fiscale]),
                metadata={"subject_id": str(company.subject_id), "partita_iva": company.partita_iva},
            )
        )

    notices = db.scalars(
        select(AnagraficaPaymentNotice)
        .where(
            or_(
                _contains(AnagraficaPaymentNotice.source_notice_id, query),
                _contains(AnagraficaPaymentNotice.codice_fiscale, query),
                _contains(AnagraficaPaymentNotice.partita_iva, query),
                _contains(AnagraficaPaymentNotice.display_name, query),
                _matches_tokens(
                    [
                        AnagraficaPaymentNotice.source_notice_id,
                        AnagraficaPaymentNotice.codice_fiscale,
                        AnagraficaPaymentNotice.partita_iva,
                        AnagraficaPaymentNotice.display_name,
                    ],
                    query,
                ),
            )
        )
        .order_by(AnagraficaPaymentNotice.anno.desc().nullslast(), AnagraficaPaymentNotice.updated_at.desc())
        .limit(limit)
    ).all()
    for notice in notices:
        href = f"/utenze/{notice.subject_id}" if notice.subject_id else "/utenze/import#utenze-soggetti"
        hits.append(
            OperationalSearchResult(
                id=str(notice.id),
                module="utenze",
                type="payment_notice",
                title=f"Avviso inCASS {notice.source_notice_id}",
                subtitle="Utenze · Avviso pagamento",
                description=_clean_parts(notice.display_name, notice.anno, notice.stato_label),
                href=href,
                score=_score(query, [notice.source_notice_id, notice.codice_fiscale, notice.partita_iva, notice.display_name]),
                metadata={"subject_id": str(notice.subject_id) if notice.subject_id else None, "anno": notice.anno},
            )
        )

    return hits


def _search_ruolo(db: Session, query: str, limit: int) -> list[OperationalSearchResult]:
    avvisi = db.scalars(
        select(RuoloAvviso)
        .where(
            or_(
                _contains(RuoloAvviso.codice_cnc, query),
                _contains(RuoloAvviso.codice_utenza, query),
                _contains(RuoloAvviso.codice_fiscale_raw, query),
                _contains(RuoloAvviso.nominativo_raw, query),
                _matches_tokens(
                    [
                        RuoloAvviso.codice_cnc,
                        RuoloAvviso.codice_utenza,
                        RuoloAvviso.codice_fiscale_raw,
                        RuoloAvviso.nominativo_raw,
                    ],
                    query,
                ),
            )
        )
        .order_by(RuoloAvviso.anno_tributario.desc(), RuoloAvviso.codice_cnc)
        .limit(limit)
    ).all()
    return [
        OperationalSearchResult(
            id=str(avviso.id),
            module="ruolo",
            type="avviso",
            title=f"Avviso {avviso.codice_cnc}",
            subtitle=f"Ruolo · {avviso.anno_tributario}",
            description=_clean_parts(avviso.nominativo_raw, avviso.codice_fiscale_raw, avviso.codice_utenza),
            href=f"/ruolo/avvisi/{avviso.id}",
            score=_score(query, [avviso.codice_cnc, avviso.codice_utenza, avviso.codice_fiscale_raw, avviso.nominativo_raw]),
            metadata={"anno_tributario": avviso.anno_tributario, "subject_id": str(avviso.subject_id) if avviso.subject_id else None},
        )
        for avviso in avvisi
    ]


def _search_catasto(db: Session, query: str, limit: int) -> list[OperationalSearchResult]:
    hits: list[OperationalSearchResult] = []

    particelle = db.scalars(
        select(CatParticella)
        .where(
            or_(
                _contains(CatParticella.foglio, query),
                _contains(CatParticella.particella, query),
                _contains(CatParticella.subalterno, query),
                _contains(CatParticella.nome_comune, query),
                _contains(CatParticella.cfm, query),
                _matches_tokens(
                    [
                        CatParticella.foglio,
                        CatParticella.particella,
                        CatParticella.subalterno,
                        CatParticella.nome_comune,
                        CatParticella.cfm,
                    ],
                    query,
                ),
            )
        )
        .order_by(CatParticella.nome_comune, CatParticella.foglio, CatParticella.particella)
        .limit(limit)
    ).all()
    for particella in particelle:
        title = _clean_parts(particella.nome_comune, f"F. {particella.foglio}", f"P. {particella.particella}", particella.subalterno)
        hits.append(
            OperationalSearchResult(
                id=str(particella.id),
                module="catasto",
                type="particella",
                title=title,
                subtitle="Catasto · Particella",
                description=_clean_parts(particella.cfm, particella.nome_distretto),
                href=f"/catasto/particelle/{particella.id}",
                score=_score(query, [particella.foglio, particella.particella, particella.subalterno, particella.nome_comune, particella.cfm]),
                metadata={"foglio": particella.foglio, "particella": particella.particella, "comune": particella.nome_comune},
            )
        )

    seen_particella_ids = {item.id for item in particelle}
    utenze_particelle = db.scalars(
        select(CatParticella)
        .join(CatUtenzaIrrigua, CatUtenzaIrrigua.particella_id == CatParticella.id)
        .where(
            or_(
                _contains(CatUtenzaIrrigua.denominazione, query),
                _contains(CatUtenzaIrrigua.codice_fiscale, query),
                _contains(CatUtenzaIrrigua.nome_comune, query),
                _contains(CatUtenzaIrrigua.foglio, query),
                _contains(CatUtenzaIrrigua.particella, query),
                _matches_tokens(
                    [
                        CatUtenzaIrrigua.denominazione,
                        CatUtenzaIrrigua.codice_fiscale,
                        CatUtenzaIrrigua.nome_comune,
                        CatUtenzaIrrigua.foglio,
                        CatUtenzaIrrigua.particella,
                    ],
                    query,
                ),
            )
        )
        .order_by(CatUtenzaIrrigua.anno_campagna.desc(), CatParticella.nome_comune, CatParticella.foglio, CatParticella.particella)
        .limit(limit)
    ).all()
    for particella in utenze_particelle:
        if particella.id in seen_particella_ids:
            continue
        seen_particella_ids.add(particella.id)
        title = _clean_parts(particella.nome_comune, f"F. {particella.foglio}", f"P. {particella.particella}", particella.subalterno)
        hits.append(
            OperationalSearchResult(
                id=str(particella.id),
                module="catasto",
                type="particella",
                title=title,
                subtitle="Catasto · Particella",
                description=_clean_parts(particella.cfm, particella.nome_distretto),
                href=f"/catasto/particelle/{particella.id}",
                score=_score(query, [particella.foglio, particella.particella, particella.subalterno, particella.nome_comune, particella.cfm]),
                metadata={"foglio": particella.foglio, "particella": particella.particella, "comune": particella.nome_comune},
            )
        )

    intestatari_particelle = db.scalars(
        select(CatParticella)
        .join(CatUtenzaIrrigua, CatUtenzaIrrigua.particella_id == CatParticella.id)
        .join(CatUtenzaIntestatario, CatUtenzaIntestatario.utenza_id == CatUtenzaIrrigua.id)
        .where(
            or_(
                _contains(CatUtenzaIntestatario.denominazione, query),
                _contains(CatUtenzaIntestatario.codice_fiscale, query),
                _contains(CatUtenzaIntestatario.partita_iva, query),
                _contains(CatUtenzaIntestatario.comune_residenza, query),
                _matches_tokens(
                    [
                        CatUtenzaIntestatario.denominazione,
                        CatUtenzaIntestatario.codice_fiscale,
                        CatUtenzaIntestatario.partita_iva,
                        CatUtenzaIntestatario.comune_residenza,
                    ],
                    query,
                ),
            )
        )
        .order_by(CatUtenzaIntestatario.anno_riferimento.desc().nullslast(), CatParticella.nome_comune, CatParticella.foglio, CatParticella.particella)
        .limit(limit)
    ).all()
    for particella in intestatari_particelle:
        if particella.id in seen_particella_ids:
            continue
        seen_particella_ids.add(particella.id)
        title = _clean_parts(particella.nome_comune, f"F. {particella.foglio}", f"P. {particella.particella}", particella.subalterno)
        hits.append(
            OperationalSearchResult(
                id=str(particella.id),
                module="catasto",
                type="particella",
                title=title,
                subtitle="Catasto · Particella",
                description=_clean_parts(particella.cfm, particella.nome_distretto),
                href=f"/catasto/particelle/{particella.id}",
                score=_score(query, [particella.foglio, particella.particella, particella.subalterno, particella.nome_comune, particella.cfm]),
                metadata={"foglio": particella.foglio, "particella": particella.particella, "comune": particella.nome_comune},
            )
        )

    documents = db.scalars(
        select(CatastoDocument)
        .where(
            or_(
                _contains(CatastoDocument.filename, query),
                _contains(CatastoDocument.codice_fiscale, query),
                _contains(CatastoDocument.intestazione, query),
                _contains(CatastoDocument.comune, query),
                _contains(CatastoDocument.foglio, query),
                _contains(CatastoDocument.particella, query),
                _matches_tokens(
                    [
                        CatastoDocument.filename,
                        CatastoDocument.codice_fiscale,
                        CatastoDocument.intestazione,
                        CatastoDocument.comune,
                        CatastoDocument.foglio,
                        CatastoDocument.particella,
                    ],
                    query,
                ),
            )
        )
        .order_by(CatastoDocument.created_at.desc())
        .limit(limit)
    ).all()
    for document in documents:
        hits.append(
            OperationalSearchResult(
                id=str(document.id),
                module="catasto",
                type="document",
                title=document.filename,
                subtitle="Catasto · Documento",
                description=_clean_parts(document.intestazione, document.codice_fiscale, document.comune, document.foglio, document.particella),
                href=f"/catasto/documents/{document.id}",
                score=_score(query, [document.filename, document.codice_fiscale, document.intestazione, document.comune, document.foglio, document.particella]),
                metadata={"request_id": str(document.request_id) if document.request_id else None, "tipo_visura": document.tipo_visura},
            )
        )

    return hits
