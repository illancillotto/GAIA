from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.catasto.routes.anagrafica.exports import _has_rpt_certificato_context
from app.modules.catasto.routes.anagrafica.intestatari import (
    _best_occupancy_for_unit,
    _context_from_occupancy,
    _utenza_summary_from_occupancy,
)
from app.modules.catasto.routes.anagrafica.normalization import (
    CapacitasLiveAuthoritativeSanitizer,
    _normalize_cf,
)
from app.modules.catasto.routes.anagrafica.persons import (
    _build_person_payload_from_current_capacitas,
    _person_response_from_db,
)
from app.modules.catasto.routes.anagrafica.resolvers import _CapacitasLiveResolver
from app.modules.elaborazioni.capacitas.models import (
    CapacitasAnagraficaDetail,
    CapacitasIntestatario,
)
from app.modules.utenze.models import (
    AnagraficaPerson,
    AnagraficaSubject,
    AnagraficaSubjectStatus,
    AnagraficaSubjectType,
)
from app.modules.utenze.services.person_history_service import snapshot_person_if_changed
from app.schemas.catasto_phase1 import CatAnagraficaMatch, CatIntestatarioResponse

# fmt: off

class _CapacitasAuthoritativeResolver(_CapacitasLiveResolver):
    """Resolver for the authoritative cadastral bulk flow."""

    def __init__(self, db: Session) -> None:
        super().__init__(db)
        self._sanitizer = CapacitasLiveAuthoritativeSanitizer()

    async def enrich_match(self, p, match: CatAnagraficaMatch) -> CatAnagraficaMatch:
        original_match = match.model_copy(deep=True)
        historical_sub_note = (original_match.note or "").strip().casefold()
        if match.unit_id is not None and historical_sub_note.startswith("presenti dati non aggiornati/storici del sub:"):
            occupancy = _best_occupancy_for_unit(self._db, match.unit_id)
            cert_context = _context_from_occupancy(occupancy)
            if occupancy is not None and not occupancy.is_current and occupancy.cco and all(cert_context[:3]):
                match.utenza_latest = _utenza_summary_from_occupancy(occupancy)
                match.cert_com, match.cert_pvc, match.cert_fra, match.cert_ccs = cert_context
        # Strip any DB-cached owners/status before handing off to the live path.
        # The only valid output is: ricerca terreni → cert context → certificato.
        # If the live path cannot complete that chain, sanitize() will blank the match.
        match.intestatari = []
        match.stato_ruolo = None
        match.stato_cnc = None
        enriched = await super().enrich_match(p, match)
        sanitized = self._sanitizer.sanitize(enriched)
        if self._disabled and _has_rpt_certificato_context(original_match):
            return original_match
        return sanitized

    async def find_live_only_matches(
        self,
        *,
        comune: str,
        foglio: str,
        particella: str,
        sub: str | None = None,
    ) -> list[CatAnagraficaMatch]:
        matches = await super().find_live_only_matches(
            comune=comune,
            foglio=foglio,
            particella=particella,
            sub=sub,
        )
        return [self._sanitizer.sanitize(match) for match in matches]

    def _find_local_intestatario(self, intestatario: CapacitasIntestatario) -> CatIntestatarioResponse | None:
        normalized_cf = _normalize_cf(intestatario.codice_fiscale)
        person: AnagraficaPerson | None = None
        subject: AnagraficaSubject | None = None

        if normalized_cf:
            person = self._db.scalar(select(AnagraficaPerson).where(AnagraficaPerson.codice_fiscale == normalized_cf))
            if person is not None:
                subject = self._db.get(AnagraficaSubject, person.subject_id)

        if person is None and intestatario.idxana:
            subject = self._db.scalar(
                select(AnagraficaSubject).where(
                    AnagraficaSubject.source_system == "capacitas",
                    AnagraficaSubject.source_external_id == intestatario.idxana,
                )
            )
            if subject is not None:
                person = self._db.get(AnagraficaPerson, subject.id)

        if person is None or subject is None:
            return None
        return _person_response_from_db(person, subject, deceduto=intestatario.deceduto)

    def _upsert_live_intestatario(
        self,
        intestatario: CapacitasIntestatario,
        detail: CapacitasAnagraficaDetail | None,
    ) -> CatIntestatarioResponse | None:
        normalized_cf = _normalize_cf((detail.codice_fiscale if detail else None) or intestatario.codice_fiscale)
        person: AnagraficaPerson | None = None
        subject: AnagraficaSubject | None = None

        if normalized_cf:
            person = self._db.scalar(select(AnagraficaPerson).where(AnagraficaPerson.codice_fiscale == normalized_cf))
            if person is not None:
                subject = self._db.get(AnagraficaSubject, person.subject_id)

        if person is None and (detail.idxana if detail else intestatario.idxana):
            subject = self._db.scalar(
                select(AnagraficaSubject).where(
                    AnagraficaSubject.source_system == "capacitas",
                    AnagraficaSubject.source_external_id == ((detail.idxana if detail else None) or intestatario.idxana),
                )
            )
            if subject is not None:
                person = self._db.get(AnagraficaPerson, subject.id)

        if person is None and not normalized_cf:
            return None

        person_data = _build_person_payload_from_current_capacitas(detail, intestatario, normalized_cf)
        collected_at = datetime.now(UTC)

        if person is None:
            assert normalized_cf is not None
            subject = AnagraficaSubject(
                subject_type=AnagraficaSubjectType.PERSON.value,
                status=AnagraficaSubjectStatus.ACTIVE.value,
                source_system="capacitas",
                source_external_id=(detail.idxana if detail else None) or intestatario.idxana,
                source_name_raw=(detail.denominazione if detail else None) or intestatario.denominazione or normalized_cf,
                requires_review=False,
            )
            self._db.add(subject)
            self._db.flush()
            person = AnagraficaPerson(subject_id=subject.id, **person_data)
            self._db.add(person)
            self._db.flush()
            self.dirty = True
            return _person_response_from_db(person, subject, deceduto=intestatario.deceduto)

        if subject is None:
            subject = self._db.get(AnagraficaSubject, person.subject_id)
        if subject is None:
            return None

        snapshot_person_if_changed(
            self._db,
            person,
            person_data,
            source_system="capacitas",
            source_ref=(detail.idxana if detail else None) or intestatario.idxana,
            collected_at=collected_at,
        )
        for key, value in person_data.items():
            setattr(person, key, value)
        if ((detail.idxana if detail else None) or intestatario.idxana) and subject.source_external_id is None:
            subject.source_external_id = (detail.idxana if detail else None) or intestatario.idxana
        if not subject.source_name_raw:
            subject.source_name_raw = (detail.denominazione if detail else None) or intestatario.denominazione or normalized_cf
        self._db.flush()
        self.dirty = True
        return _person_response_from_db(person, subject, deceduto=intestatario.deceduto)
