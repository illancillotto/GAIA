from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import CatDistretto, CatIndiceOverviewSnapshot, CatParticella, CatUtenzaIrrigua
from app.modules.catasto.services.indici import get_indice_metadata, normalize_num_distretto
from app.modules.catasto.services.irrigation_tariffs import build_irrigation_tariff_preview
from app.modules.ruolo.models import RuoloAvviso, RuoloParticella, RuoloPartita
from app.schemas.catasto_phase1 import (
    CatIndiceBreakdownSummaryResponse,
    CatIndiceColturaSummaryResponse,
    CatIndiceDistrettoSummaryResponse,
    CatIndiceGroupSummaryResponse,
    CatIndiceOverviewResponse,
    CatIndiceRuoloExcludedParticellaResponse,
    CatIndiceRuoloExcludedParticelleResponse,
    CatIndiceRuoloReconciliationReasonResponse,
    CatIndiceRuoloReconciliationResponse,
)


@dataclass(slots=True)
class _IndiceAccumulator:
    key: str
    label: str
    sort_order: int
    distretti: list[CatIndiceDistrettoSummaryResponse] = field(default_factory=list)
    particelle_count: int = 0
    ruolo_particelle_count: int = 0
    particelle_con_anagrafica_count: int = 0
    superficie_catastale_mq: Decimal = Decimal("0")
    superficie_irrigata_ha: Decimal = Decimal("0")
    importo_stimato: Decimal = Decimal("0")
    importo_ruolo: Decimal = Decimal("0")
    importo_ruolo_manutenzione: Decimal = Decimal("0")
    importo_ruolo_irrigazione: Decimal = Decimal("0")
    importo_ruolo_istituzionale: Decimal = Decimal("0")
    ruolo_metrics_valid_count: int = 0
    ruolo_metrics_invalid_count: int = 0
    hectares_reference_total: Decimal = Decimal("0")
    colture: dict[tuple[str, str | None], dict[str, object]] = field(default_factory=dict)
    comuni: dict[str, dict[str, object]] = field(default_factory=dict)
    distretti_analytics: dict[str, dict[str, object]] = field(default_factory=dict)


_ROLE_SURFACE_MAX_REASONABLE_HA = Decimal("1000")
_ROLE_SURFACE_MAX_RATIO = Decimal("2")

_RUOLO_RECONCILIATION_REASONS: dict[str, tuple[str, str]] = {
    "non_collegata": (
        "Ruolo non collegato al catasto corrente",
        "Righe ruolo senza un aggancio sicuro a cat_particelle: la particella puo' essere soppressa, variata o non risolta nel catasto AE corrente.",
    ),
    "catasto_non_corrente_o_assente": (
        "Aggancio non corrente o non disponibile",
        "Righe ruolo con cat_particella_id valorizzato ma non riferibile a una particella corrente utilizzabile per gli indici.",
    ),
    "senza_distretto": (
        "Particella corrente senza distretto",
        "La particella esiste nel catasto AE corrente, ma non ha num_distretto: non puo' essere attribuita ad Alta/Bassa/Canaletta.",
    ),
    "swapped_arborea_terralba": (
        "Particella Arborea/Terralba risolta sul comune storico alternativo",
        "La particella e' stata agganciata applicando la regola storica Arborea/Terralba. Se manca il distretto, va verificata come caso storico prima di assegnarla agli indici.",
    ),
}

_SWAPPED_ARBOREA_TERRALBA_REASON = "swapped_arborea_terralba"


def _ruolo_exclusion_reason_key(row: object) -> str | None:
    if row.cat_particella_id is None:
        return "non_collegata"
    if row.linked_particella_id is None or row.linked_is_current is not True:
        return "catasto_non_corrente_o_assente"
    if row.linked_num_distretto is None:
        if getattr(row, "cat_particella_match_reason", None) == _SWAPPED_ARBOREA_TERRALBA_REASON:
            return _SWAPPED_ARBOREA_TERRALBA_REASON
        return "senza_distretto"
    return None


def _decimal_or_none(value: object | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _has_text(value: str | None) -> bool:
    return value is not None and bool(value.strip())


def _has_positive_decimal(value: Decimal | None) -> bool:
    return value is not None and value > 0


@dataclass(slots=True)
class _PreferredRuoloRow:
    particella_id: UUID
    coltura: str | None
    anno_tributario: int
    sup_irrigata_ha: Decimal | None
    sup_catastale_ha: Decimal | None
    importo_manut: Decimal = Decimal("0")
    importo_irrig: Decimal = Decimal("0")
    importo_ist: Decimal = Decimal("0")

    @property
    def importo_ruolo(self) -> Decimal:
        return self.importo_manut + self.importo_irrig + self.importo_ist


@dataclass(slots=True)
class _RuoloReconciliationAccumulator:
    righe_ruolo_count: int = 0
    particelle_ruolo_keys: set[tuple[str, str, str, str]] = field(default_factory=set)
    cat_particella_ids: set[UUID] = field(default_factory=set)
    superficie_irrigata_ha: Decimal = Decimal("0")
    importo_ruolo_manutenzione: Decimal = Decimal("0")
    importo_ruolo_irrigazione: Decimal = Decimal("0")
    importo_ruolo_istituzionale: Decimal = Decimal("0")

    @property
    def particelle_ruolo_distinte_count(self) -> int:
        return len(self.particelle_ruolo_keys)

    @property
    def cat_particelle_count(self) -> int:
        return len(self.cat_particella_ids)

    @property
    def importo_ruolo(self) -> Decimal:
        return self.importo_ruolo_manutenzione + self.importo_ruolo_irrigazione + self.importo_ruolo_istituzionale


def _is_role_surface_plausible(*, sup_irrigata_ha: Decimal | None, sup_catastale_ha: Decimal | None) -> bool:
    if sup_irrigata_ha is None or sup_irrigata_ha <= 0:
        return True
    if sup_irrigata_ha > _ROLE_SURFACE_MAX_REASONABLE_HA:
        return False
    if sup_catastale_ha is not None and sup_catastale_ha > 0 and sup_irrigata_ha > (sup_catastale_ha * _ROLE_SURFACE_MAX_RATIO):
        return False
    return True


def _distretto_breakdown_label(code: str, nome: str | None) -> str:
    lowered = code.lower()
    if lowered == "fd":
        return "FD · Fuori distretto"
    if lowered.startswith("fd_"):
        return f"{code.upper()} · Fuori distretto (zona {code[3:]})"
    return f"{code} · {nome or 'Distretto'}"


def _empty_breakdown_entry(*, key: str, label: str) -> dict[str, object]:
    return {
        "key": key,
        "label": label,
        "particelle_count": 0,
        "ruolo_particelle_count": 0,
        "particelle_con_anagrafica_count": 0,
        "superficie_irrigata_ha": Decimal("0"),
        "importo_stimato": Decimal("0"),
        "importo_ruolo": Decimal("0"),
        "importo_ruolo_manutenzione": Decimal("0"),
        "importo_ruolo_irrigazione": Decimal("0"),
        "importo_ruolo_istituzionale": Decimal("0"),
    }


def _serialize_breakdowns(items: dict[str, dict[str, object]]) -> list[CatIndiceBreakdownSummaryResponse]:
    return sorted(
        [
            CatIndiceBreakdownSummaryResponse(
                key=str(value["key"]),
                label=str(value["label"]),
                particelle_count=int(value["particelle_count"]),
                ruolo_particelle_count=int(value["ruolo_particelle_count"]),
                particelle_con_anagrafica_count=int(value["particelle_con_anagrafica_count"]),
                superficie_irrigata_ha=Decimal(value["superficie_irrigata_ha"]),
                importo_stimato=Decimal(value["importo_stimato"]),
                importo_ruolo=Decimal(value["importo_ruolo"]),
                importo_ruolo_manutenzione=Decimal(value["importo_ruolo_manutenzione"]),
                importo_ruolo_irrigazione=Decimal(value["importo_ruolo_irrigazione"]),
                importo_ruolo_istituzionale=Decimal(value["importo_ruolo_istituzionale"]),
            )
            for value in items.values()
        ],
        key=lambda item: (-item.importo_ruolo, -item.importo_stimato, -item.superficie_irrigata_ha, item.label.lower()),
    )


def _ruolo_particella_key(*, comune_nome: str | None, foglio: str, particella: str, subalterno: str | None) -> tuple[str, str, str, str]:
    return (
        (comune_nome or "").strip().upper(),
        foglio.strip().upper(),
        particella.strip().upper(),
        (subalterno or "").strip().upper(),
    )


def _add_ruolo_reconciliation_row(
    accumulator: _RuoloReconciliationAccumulator,
    *,
    comune_nome: str | None,
    foglio: str,
    particella: str,
    subalterno: str | None,
    cat_particella_id: UUID | None,
    superficie_irrigata_ha: object | None,
    importo_manutenzione: object | None,
    importo_irrigazione: object | None,
    importo_istituzionale: object | None,
) -> None:
    accumulator.righe_ruolo_count += 1
    accumulator.particelle_ruolo_keys.add(
        _ruolo_particella_key(
            comune_nome=comune_nome,
            foglio=foglio,
            particella=particella,
            subalterno=subalterno,
        )
    )
    if cat_particella_id is not None:
        accumulator.cat_particella_ids.add(cat_particella_id)
    accumulator.superficie_irrigata_ha += _decimal_or_none(superficie_irrigata_ha) or Decimal("0")
    accumulator.importo_ruolo_manutenzione += _decimal_or_none(importo_manutenzione) or Decimal("0")
    accumulator.importo_ruolo_irrigazione += _decimal_or_none(importo_irrigazione) or Decimal("0")
    accumulator.importo_ruolo_istituzionale += _decimal_or_none(importo_istituzionale) or Decimal("0")


def build_ruolo_reconciliation(db: Session, anno_riferimento: int | None) -> CatIndiceRuoloReconciliationResponse:
    if anno_riferimento is None:
        return CatIndiceRuoloReconciliationResponse()

    rows = db.execute(
        select(
            RuoloParticella.cat_particella_id.label("cat_particella_id"),
            RuoloParticella.foglio.label("foglio"),
            RuoloParticella.particella.label("particella"),
            RuoloParticella.subalterno.label("subalterno"),
            RuoloParticella.sup_irrigata_ha.label("sup_irrigata_ha"),
            RuoloParticella.importo_manut.label("importo_manut"),
            RuoloParticella.importo_irrig.label("importo_irrig"),
            RuoloParticella.importo_ist.label("importo_ist"),
            RuoloPartita.comune_nome.label("comune_nome"),
            CatParticella.id.label("linked_particella_id"),
            CatParticella.is_current.label("linked_is_current"),
            CatParticella.num_distretto.label("linked_num_distretto"),
            RuoloParticella.cat_particella_match_reason.label("cat_particella_match_reason"),
        )
        .join(RuoloPartita, RuoloPartita.id == RuoloParticella.partita_id)
        .outerjoin(CatParticella, CatParticella.id == RuoloParticella.cat_particella_id)
        .where(RuoloParticella.anno_tributario == anno_riferimento)
    ).all()

    included = _RuoloReconciliationAccumulator()
    excluded_by_reason = {
        key: _RuoloReconciliationAccumulator()
        for key in _RUOLO_RECONCILIATION_REASONS
    }

    for row in rows:
        bucket_key = _ruolo_exclusion_reason_key(row) or "inclusa"

        bucket = included if bucket_key == "inclusa" else excluded_by_reason[bucket_key]
        _add_ruolo_reconciliation_row(
            bucket,
            comune_nome=row.comune_nome,
            foglio=row.foglio,
            particella=row.particella,
            subalterno=row.subalterno,
            cat_particella_id=row.cat_particella_id,
            superficie_irrigata_ha=row.sup_irrigata_ha,
            importo_manutenzione=row.importo_manut,
            importo_irrigazione=row.importo_irrig,
            importo_istituzionale=row.importo_ist,
        )

    excluded = _RuoloReconciliationAccumulator()
    for reason_accumulator in excluded_by_reason.values():
        excluded.righe_ruolo_count += reason_accumulator.righe_ruolo_count
        excluded.particelle_ruolo_keys.update(reason_accumulator.particelle_ruolo_keys)
        excluded.cat_particella_ids.update(reason_accumulator.cat_particella_ids)
        excluded.superficie_irrigata_ha += reason_accumulator.superficie_irrigata_ha
        excluded.importo_ruolo_manutenzione += reason_accumulator.importo_ruolo_manutenzione
        excluded.importo_ruolo_irrigazione += reason_accumulator.importo_ruolo_irrigazione
        excluded.importo_ruolo_istituzionale += reason_accumulator.importo_ruolo_istituzionale

    total = _RuoloReconciliationAccumulator()
    for accumulator in (included, excluded):
        total.righe_ruolo_count += accumulator.righe_ruolo_count
        total.particelle_ruolo_keys.update(accumulator.particelle_ruolo_keys)
        total.cat_particella_ids.update(accumulator.cat_particella_ids)
        total.superficie_irrigata_ha += accumulator.superficie_irrigata_ha
        total.importo_ruolo_manutenzione += accumulator.importo_ruolo_manutenzione
        total.importo_ruolo_irrigazione += accumulator.importo_ruolo_irrigazione
        total.importo_ruolo_istituzionale += accumulator.importo_ruolo_istituzionale

    reasons = []
    for key, (label, description) in _RUOLO_RECONCILIATION_REASONS.items():
        accumulator = excluded_by_reason[key]
        if accumulator.righe_ruolo_count == 0:
            continue
        reasons.append(
            CatIndiceRuoloReconciliationReasonResponse(
                key=key,
                label=label,
                description=description,
                righe_ruolo_count=accumulator.righe_ruolo_count,
                particelle_ruolo_distinte_count=accumulator.particelle_ruolo_distinte_count,
                cat_particelle_count=accumulator.cat_particelle_count,
                superficie_irrigata_ha=accumulator.superficie_irrigata_ha,
                importo_ruolo=accumulator.importo_ruolo,
                importo_ruolo_manutenzione=accumulator.importo_ruolo_manutenzione,
                importo_ruolo_irrigazione=accumulator.importo_ruolo_irrigazione,
                importo_ruolo_istituzionale=accumulator.importo_ruolo_istituzionale,
            )
        )

    coverage_percent = (included.importo_ruolo / total.importo_ruolo * Decimal("100")) if total.importo_ruolo > 0 else None
    return CatIndiceRuoloReconciliationResponse(
        righe_ruolo_totali_count=total.righe_ruolo_count,
        particelle_ruolo_totali_count=total.particelle_ruolo_distinte_count,
        righe_ruolo_incluse_count=included.righe_ruolo_count,
        particelle_ruolo_incluse_count=included.particelle_ruolo_distinte_count,
        righe_ruolo_escluse_count=excluded.righe_ruolo_count,
        particelle_ruolo_escluse_count=excluded.particelle_ruolo_distinte_count,
        importo_ruolo_totale=total.importo_ruolo,
        importo_ruolo_incluso=included.importo_ruolo,
        importo_ruolo_escluso=excluded.importo_ruolo,
        importo_ruolo_escluso_manutenzione=excluded.importo_ruolo_manutenzione,
        importo_ruolo_escluso_irrigazione=excluded.importo_ruolo_irrigazione,
        importo_ruolo_escluso_istituzionale=excluded.importo_ruolo_istituzionale,
        superficie_irrigata_esclusa_ha=excluded.superficie_irrigata_ha,
        coverage_percent=coverage_percent,
        reasons=sorted(reasons, key=lambda item: (-item.importo_ruolo, item.label.lower())),
    )


def build_ruolo_excluded_particelle(db: Session, anno_riferimento: int | None) -> CatIndiceRuoloExcludedParticelleResponse:
    if anno_riferimento is None:
        return CatIndiceRuoloExcludedParticelleResponse()

    rows = db.execute(
        select(
            RuoloParticella.cat_particella_id.label("cat_particella_id"),
            RuoloParticella.foglio.label("foglio"),
            RuoloParticella.particella.label("particella"),
            RuoloParticella.subalterno.label("subalterno"),
            RuoloParticella.sup_irrigata_ha.label("sup_irrigata_ha"),
            RuoloParticella.importo_manut.label("importo_manut"),
            RuoloParticella.importo_irrig.label("importo_irrig"),
            RuoloParticella.importo_ist.label("importo_ist"),
            RuoloPartita.comune_nome.label("comune_nome"),
            RuoloPartita.codice_partita.label("codice_partita"),
            RuoloAvviso.codice_cnc.label("codice_cnc"),
            RuoloAvviso.nominativo_raw.label("nominativo_raw"),
            CatParticella.id.label("linked_particella_id"),
            CatParticella.is_current.label("linked_is_current"),
            CatParticella.num_distretto.label("linked_num_distretto"),
            RuoloParticella.cat_particella_match_reason.label("cat_particella_match_reason"),
        )
        .join(RuoloPartita, RuoloPartita.id == RuoloParticella.partita_id)
        .join(RuoloAvviso, RuoloAvviso.id == RuoloPartita.avviso_id)
        .outerjoin(CatParticella, CatParticella.id == RuoloParticella.cat_particella_id)
        .where(RuoloParticella.anno_tributario == anno_riferimento)
    ).all()

    grouped: dict[tuple[str, str, str, str, str], dict[str, object]] = {}
    for row in rows:
        reason_key = _ruolo_exclusion_reason_key(row)
        if reason_key is None:
            continue

        key_tuple = _ruolo_particella_key(
            comune_nome=row.comune_nome,
            foglio=row.foglio,
            particella=row.particella,
            subalterno=row.subalterno,
        )
        group_key = (reason_key, *key_tuple)
        if group_key not in grouped:
            grouped[group_key] = {
                "reason_key": reason_key,
                "comune_nome": row.comune_nome,
                "foglio": row.foglio,
                "particella": row.particella,
                "subalterno": row.subalterno,
                "cat_particella_id": row.cat_particella_id,
                "catasto_is_current": row.linked_is_current,
                "catasto_num_distretto": row.linked_num_distretto,
                "righe_ruolo_count": 0,
                "superficie_irrigata_ha": Decimal("0"),
                "importo_ruolo_manutenzione": Decimal("0"),
                "importo_ruolo_irrigazione": Decimal("0"),
                "importo_ruolo_istituzionale": Decimal("0"),
                "avvisi": set(),
                "nominativi": set(),
                "partite": set(),
            }

        item = grouped[group_key]
        item["righe_ruolo_count"] = int(item["righe_ruolo_count"]) + 1
        item["superficie_irrigata_ha"] = Decimal(item["superficie_irrigata_ha"]) + (_decimal_or_none(row.sup_irrigata_ha) or Decimal("0"))
        item["importo_ruolo_manutenzione"] = Decimal(item["importo_ruolo_manutenzione"]) + (_decimal_or_none(row.importo_manut) or Decimal("0"))
        item["importo_ruolo_irrigazione"] = Decimal(item["importo_ruolo_irrigazione"]) + (_decimal_or_none(row.importo_irrig) or Decimal("0"))
        item["importo_ruolo_istituzionale"] = Decimal(item["importo_ruolo_istituzionale"]) + (_decimal_or_none(row.importo_ist) or Decimal("0"))
        if _has_text(row.codice_cnc):
            item["avvisi"].add(row.codice_cnc.strip())  # type: ignore[union-attr]
        if _has_text(row.nominativo_raw):
            item["nominativi"].add(row.nominativo_raw.strip())  # type: ignore[union-attr]
        if _has_text(row.codice_partita):
            item["partite"].add(row.codice_partita.strip())  # type: ignore[union-attr]

    response_items: list[CatIndiceRuoloExcludedParticellaResponse] = []
    for group_key, item in grouped.items():
        reason_key = str(item["reason_key"])
        reason_label = _RUOLO_RECONCILIATION_REASONS[reason_key][0]
        importo_manutenzione = Decimal(item["importo_ruolo_manutenzione"])
        importo_irrigazione = Decimal(item["importo_ruolo_irrigazione"])
        importo_istituzionale = Decimal(item["importo_ruolo_istituzionale"])
        response_items.append(
            CatIndiceRuoloExcludedParticellaResponse(
                key="|".join(group_key),
                reason_key=reason_key,
                reason_label=reason_label,
                comune_nome=str(item["comune_nome"]) if item["comune_nome"] is not None else None,
                foglio=str(item["foglio"]),
                particella=str(item["particella"]),
                subalterno=str(item["subalterno"]) if item["subalterno"] is not None else None,
                righe_ruolo_count=int(item["righe_ruolo_count"]),
                cat_particella_id=item["cat_particella_id"],
                catasto_is_current=item["catasto_is_current"],
                catasto_num_distretto=str(item["catasto_num_distretto"]) if item["catasto_num_distretto"] is not None else None,
                superficie_irrigata_ha=Decimal(item["superficie_irrigata_ha"]),
                importo_ruolo=importo_manutenzione + importo_irrigazione + importo_istituzionale,
                importo_ruolo_manutenzione=importo_manutenzione,
                importo_ruolo_irrigazione=importo_irrigazione,
                importo_ruolo_istituzionale=importo_istituzionale,
                avvisi=sorted(item["avvisi"]),  # type: ignore[arg-type]
                nominativi=sorted(item["nominativi"]),  # type: ignore[arg-type]
                partite=sorted(item["partite"]),  # type: ignore[arg-type]
            )
        )

    response_items.sort(
        key=lambda item: (
            -item.importo_ruolo,
            item.reason_label.lower(),
            (item.comune_nome or "").lower(),
            item.foglio,
            item.particella,
            item.subalterno or "",
        )
    )
    return CatIndiceRuoloExcludedParticelleResponse(
        anno_riferimento=anno_riferimento,
        total=len(response_items),
        items=response_items,
    )


def resolve_anno_riferimento(db: Session, anno: int | None) -> int | None:
    if anno is not None:
        return anno
    latest = db.scalar(select(func.max(RuoloParticella.anno_tributario)))
    return int(latest) if latest is not None else None


def _load_latest_ruolo_rows(db: Session, particella_ids: list) -> dict:
    if not particella_ids:
        return {}
    rows_by_particella: dict[UUID, _PreferredRuoloRow] = {}
    chunk_size = 2000
    for start in range(0, len(particella_ids), chunk_size):
        chunk = particella_ids[start:start + chunk_size]
        rows = db.execute(
            select(
                RuoloParticella.cat_particella_id.label("particella_id"),
                RuoloParticella.coltura.label("coltura"),
                RuoloParticella.anno_tributario.label("anno_tributario"),
                RuoloParticella.sup_irrigata_ha.label("sup_irrigata_ha"),
                RuoloParticella.sup_catastale_ha.label("sup_catastale_ha"),
                RuoloParticella.importo_manut.label("importo_manut"),
                RuoloParticella.importo_irrig.label("importo_irrig"),
                RuoloParticella.importo_ist.label("importo_ist"),
                RuoloParticella.created_at.label("created_at"),
                RuoloParticella.id.label("ruolo_particella_id"),
            )
            .where(
                RuoloParticella.cat_particella_id.in_(chunk),
                RuoloParticella.cat_particella_id.is_not(None),
            )
            .order_by(
                RuoloParticella.cat_particella_id,
                desc(RuoloParticella.anno_tributario),
                desc(RuoloParticella.created_at),
                desc(RuoloParticella.id),
            )
        ).all()
        grouped: dict[UUID, list] = {}
        for row in rows:
            if row.particella_id is None:  # pragma: no cover - guarded by the SQL predicate above.
                continue
            grouped.setdefault(row.particella_id, []).append(row)

        for particella_id, grouped_rows in grouped.items():
            selected_year = int(grouped_rows[0].anno_tributario)
            year_rows = [row for row in grouped_rows if int(row.anno_tributario) == selected_year]
            preferred_row = min(
                year_rows,
                key=lambda row: (
                    0 if _has_text(row.coltura) else 1,
                    0 if _has_positive_decimal(_decimal_or_none(row.sup_irrigata_ha)) else 1,
                    0 if _has_positive_decimal(_decimal_or_none(row.sup_catastale_ha)) else 1,
                    -datetime.timestamp(row.created_at) if row.created_at is not None else float("inf"),
                    str(row.ruolo_particella_id),
                ),
            )
            non_empty_colture = [
                row.coltura.strip()
                for row in year_rows
                if _has_text(row.coltura)
            ]
            distinct_colture = {item.upper(): item for item in non_empty_colture}
            # Una particella puo' comparire in piu' partite nello stesso anno con porzioni
            # irrigate distinte: la superficie corretta e' la somma, non il massimo.
            positive_sup_values = [
                value
                for row in year_rows
                if _has_positive_decimal(value := _decimal_or_none(row.sup_irrigata_ha))
            ]
            sup_irrigata_ha = sum(positive_sup_values, Decimal("0")) if positive_sup_values else None
            sup_catastale_ha = max(
                (_decimal_or_none(row.sup_catastale_ha) for row in year_rows if _has_positive_decimal(_decimal_or_none(row.sup_catastale_ha))),
                default=None,
            )
            importo_manut = sum((_decimal_or_none(row.importo_manut) or Decimal("0") for row in year_rows), Decimal("0"))
            importo_irrig = sum((_decimal_or_none(row.importo_irrig) or Decimal("0") for row in year_rows), Decimal("0"))
            importo_ist = sum((_decimal_or_none(row.importo_ist) or Decimal("0") for row in year_rows), Decimal("0"))
            rows_by_particella[particella_id] = _PreferredRuoloRow(
                particella_id=particella_id,
                coltura=next(iter(distinct_colture.values())) if len(distinct_colture) == 1 else preferred_row.coltura,
                anno_tributario=selected_year,
                sup_irrigata_ha=sup_irrigata_ha,
                sup_catastale_ha=sup_catastale_ha,
                importo_manut=importo_manut,
                importo_irrig=importo_irrig,
                importo_ist=importo_ist,
            )
    return rows_by_particella


def build_indici_overview(db: Session, anno: int | None) -> CatIndiceOverviewResponse:
    anno_riferimento = resolve_anno_riferimento(db, anno)
    distretti = list(
        db.execute(select(CatDistretto).where(CatDistretto.attivo.is_(True)).order_by(CatDistretto.num_distretto)).scalars().all()
    )
    particelle = list(
        db.execute(
            select(CatParticella)
            .where(CatParticella.is_current.is_(True), CatParticella.num_distretto.is_not(None))
            .order_by(CatParticella.num_distretto, CatParticella.cod_comune_capacitas, CatParticella.foglio, CatParticella.particella)
        ).scalars().all()
    )
    latest_ruolo_by_particella = _load_latest_ruolo_rows(db, [item.id for item in particelle])
    particelle_con_anagrafica = set(
        db.execute(
            select(CatUtenzaIrrigua.particella_id)
            .distinct()
            .where(CatUtenzaIrrigua.particella_id.is_not(None))
        ).scalars().all()
    )

    accumulators: dict[str, _IndiceAccumulator] = {}
    available_colture: set[str] = set()

    # Lo stesso distretto puo' comparire con codifiche diverse (es. "291" e "29a"):
    # si tiene una sola riga per codice normalizzato, preferendo quella canonica.
    def _distretto_dedup_sort_key(item: CatDistretto) -> tuple[str, int]:
        normalized = normalize_num_distretto(item.num_distretto) or item.num_distretto
        return (normalized, 0 if item.num_distretto == normalized else 1)

    seen_distretti_codes: set[str] = set()
    for distretto in sorted(distretti, key=_distretto_dedup_sort_key):
        normalized_code = normalize_num_distretto(distretto.num_distretto) or distretto.num_distretto
        metadata = get_indice_metadata(distretto.num_distretto)
        accumulator = accumulators.setdefault(
            metadata.key,
            _IndiceAccumulator(key=metadata.key, label=metadata.label, sort_order=metadata.sort_order),
        )
        if normalized_code in seen_distretti_codes:
            continue
        seen_distretti_codes.add(normalized_code)
        accumulator.distretti.append(
            CatIndiceDistrettoSummaryResponse(
                distretto_id=distretto.id,
                num_distretto=distretto.num_distretto,
                nome_distretto=distretto.nome_distretto,
                indice_key=metadata.key,
                indice_label=metadata.label,
                hectares_reference=metadata.hectares_reference,
            )
        )
        accumulator.distretti_analytics.setdefault(
            normalized_code,
            _empty_breakdown_entry(
                key=normalized_code,
                label=_distretto_breakdown_label(normalized_code, distretto.nome_distretto),
            ),
        )
        if metadata.hectares_reference is not None:
            accumulator.hectares_reference_total += metadata.hectares_reference

    for particella in particelle:
        metadata = get_indice_metadata(particella.num_distretto)
        accumulator = accumulators.setdefault(
            metadata.key,
            _IndiceAccumulator(key=metadata.key, label=metadata.label, sort_order=metadata.sort_order),
        )
        accumulator.particelle_count += 1
        comune_label = particella.nome_comune or str(particella.cod_comune_capacitas)
        comune_entry = accumulator.comuni.setdefault(
            comune_label.lower(),
            _empty_breakdown_entry(key=comune_label, label=comune_label),
        )
        comune_entry["particelle_count"] = int(comune_entry["particelle_count"]) + 1
        distretto_key = normalize_num_distretto(particella.num_distretto) or "nd"
        distretto_entry = accumulator.distretti_analytics.setdefault(
            distretto_key,
            _empty_breakdown_entry(
                key=distretto_key,
                label=_distretto_breakdown_label(distretto_key, particella.nome_distretto),
            ),
        )
        distretto_entry["particelle_count"] = int(distretto_entry["particelle_count"]) + 1
        if particella.id in particelle_con_anagrafica:
            accumulator.particelle_con_anagrafica_count += 1
            comune_entry["particelle_con_anagrafica_count"] = int(comune_entry["particelle_con_anagrafica_count"]) + 1
            distretto_entry["particelle_con_anagrafica_count"] = int(distretto_entry["particelle_con_anagrafica_count"]) + 1
        accumulator.superficie_catastale_mq += particella.superficie_mq or Decimal("0")

        latest_ruolo = latest_ruolo_by_particella.get(particella.id)
        if latest_ruolo is None:
            continue
        if anno_riferimento is not None and latest_ruolo.anno_tributario != anno_riferimento:
            continue

        accumulator.ruolo_particelle_count += 1
        comune_entry["ruolo_particelle_count"] = int(comune_entry["ruolo_particelle_count"]) + 1
        distretto_entry["ruolo_particelle_count"] = int(distretto_entry["ruolo_particelle_count"]) + 1
        sup_irrigata_ha_raw = _decimal_or_none(latest_ruolo.sup_irrigata_ha)
        sup_catastale_ha = _decimal_or_none(latest_ruolo.sup_catastale_ha)
        role_metrics_reliable = _is_role_surface_plausible(
            sup_irrigata_ha=sup_irrigata_ha_raw,
            sup_catastale_ha=sup_catastale_ha,
        )
        if role_metrics_reliable:
            accumulator.ruolo_metrics_valid_count += 1
        elif sup_irrigata_ha_raw is not None:
            accumulator.ruolo_metrics_invalid_count += 1

        sup_irrigata_ha = (
            sup_irrigata_ha_raw
            if role_metrics_reliable and sup_irrigata_ha_raw is not None
            else Decimal("0")
        )
        preview = build_irrigation_tariff_preview(
            coltura=latest_ruolo.coltura,
            sup_irrigata_ha=sup_irrigata_ha if sup_irrigata_ha_raw is not None and role_metrics_reliable else None,
            nome_distretto=particella.nome_distretto,
            num_distretto=particella.num_distretto,
            nome_comune=particella.nome_comune,
        )
        importo_ruolo = latest_ruolo.importo_ruolo
        accumulator.superficie_irrigata_ha += sup_irrigata_ha
        accumulator.importo_stimato += preview.importo_stimato or Decimal("0")
        accumulator.importo_ruolo += importo_ruolo
        accumulator.importo_ruolo_manutenzione += latest_ruolo.importo_manut
        accumulator.importo_ruolo_irrigazione += latest_ruolo.importo_irrig
        accumulator.importo_ruolo_istituzionale += latest_ruolo.importo_ist
        comune_entry["superficie_irrigata_ha"] = Decimal(comune_entry["superficie_irrigata_ha"]) + sup_irrigata_ha
        comune_entry["importo_stimato"] = Decimal(comune_entry["importo_stimato"]) + (preview.importo_stimato or Decimal("0"))
        comune_entry["importo_ruolo"] = Decimal(comune_entry["importo_ruolo"]) + importo_ruolo
        comune_entry["importo_ruolo_manutenzione"] = Decimal(comune_entry["importo_ruolo_manutenzione"]) + latest_ruolo.importo_manut
        comune_entry["importo_ruolo_irrigazione"] = Decimal(comune_entry["importo_ruolo_irrigazione"]) + latest_ruolo.importo_irrig
        comune_entry["importo_ruolo_istituzionale"] = Decimal(comune_entry["importo_ruolo_istituzionale"]) + latest_ruolo.importo_ist
        distretto_entry["superficie_irrigata_ha"] = Decimal(distretto_entry["superficie_irrigata_ha"]) + sup_irrigata_ha
        distretto_entry["importo_stimato"] = Decimal(distretto_entry["importo_stimato"]) + (preview.importo_stimato or Decimal("0"))
        distretto_entry["importo_ruolo"] = Decimal(distretto_entry["importo_ruolo"]) + importo_ruolo
        distretto_entry["importo_ruolo_manutenzione"] = Decimal(distretto_entry["importo_ruolo_manutenzione"]) + latest_ruolo.importo_manut
        distretto_entry["importo_ruolo_irrigazione"] = Decimal(distretto_entry["importo_ruolo_irrigazione"]) + latest_ruolo.importo_irrig
        distretto_entry["importo_ruolo_istituzionale"] = Decimal(distretto_entry["importo_ruolo_istituzionale"]) + latest_ruolo.importo_ist

        if latest_ruolo.coltura:
            available_colture.add(latest_ruolo.coltura)
            crop_key = (latest_ruolo.coltura, preview.crop_group_label)
            crop_entry = accumulator.colture.setdefault(
                crop_key,
                {
                    "coltura": latest_ruolo.coltura,
                    "gruppo_coltura": preview.crop_group_label,
                    "particelle_count": 0,
                    "superficie_irrigata_ha": Decimal("0"),
                    "importo_stimato": Decimal("0"),
                    "importo_ruolo": Decimal("0"),
                },
            )
            crop_entry["particelle_count"] = int(crop_entry["particelle_count"]) + 1
            crop_entry["superficie_irrigata_ha"] = Decimal(crop_entry["superficie_irrigata_ha"]) + sup_irrigata_ha
            crop_entry["importo_stimato"] = Decimal(crop_entry["importo_stimato"]) + (preview.importo_stimato or Decimal("0"))
            crop_entry["importo_ruolo"] = Decimal(crop_entry["importo_ruolo"]) + importo_ruolo

    items = [
        CatIndiceGroupSummaryResponse(
            indice_key=accumulator.key,
            indice_label=accumulator.label,
            sort_order=accumulator.sort_order,
            distretti_count=len(accumulator.distretti),
            particelle_count=accumulator.particelle_count,
            ruolo_particelle_count=accumulator.ruolo_particelle_count,
            particelle_con_anagrafica_count=accumulator.particelle_con_anagrafica_count,
            particelle_senza_ruolo_count=max(accumulator.particelle_count - accumulator.ruolo_particelle_count, 0),
            particelle_senza_anagrafica_count=max(accumulator.particelle_count - accumulator.particelle_con_anagrafica_count, 0),
            superficie_catastale_mq=accumulator.superficie_catastale_mq,
            superficie_irrigata_ha=accumulator.superficie_irrigata_ha,
            importo_stimato=accumulator.importo_stimato,
            importo_ruolo=accumulator.importo_ruolo,
            importo_ruolo_manutenzione=accumulator.importo_ruolo_manutenzione,
            importo_ruolo_irrigazione=accumulator.importo_ruolo_irrigazione,
            importo_ruolo_istituzionale=accumulator.importo_ruolo_istituzionale,
            ruolo_metrics_reliable=accumulator.ruolo_metrics_invalid_count <= accumulator.ruolo_metrics_valid_count,
            ruolo_metrics_valid_count=accumulator.ruolo_metrics_valid_count,
            ruolo_metrics_invalid_count=accumulator.ruolo_metrics_invalid_count,
            ruolo_metrics_warning=(
                "Le superfici irrigate e gli importi ruolo risultano non affidabili per questo indice: dati sorgente 2025 corrotti o allineati in modo errato."
                if accumulator.ruolo_metrics_invalid_count > accumulator.ruolo_metrics_valid_count
                else None
            ),
            hectares_reference_total=accumulator.hectares_reference_total if accumulator.hectares_reference_total > 0 else None,
            distretti=sorted(accumulator.distretti, key=lambda item: item.num_distretto),
            colture=sorted(
                [
                    CatIndiceColturaSummaryResponse(
                        coltura=str(value["coltura"]),
                        gruppo_coltura=value["gruppo_coltura"],
                        particelle_count=int(value["particelle_count"]),
                        superficie_irrigata_ha=Decimal(value["superficie_irrigata_ha"]),
                        importo_stimato=Decimal(value["importo_stimato"]),
                        importo_ruolo=Decimal(value["importo_ruolo"]),
                    )
                    for value in accumulator.colture.values()
                ],
                key=lambda item: (-item.particelle_count, item.coltura.lower()),
            ),
            comuni=_serialize_breakdowns(accumulator.comuni),
            distretti_analytics=_serialize_breakdowns(accumulator.distretti_analytics),
        )
        for accumulator in sorted(accumulators.values(), key=lambda item: (item.sort_order, item.label))
    ]

    return CatIndiceOverviewResponse(
        anno_riferimento=anno_riferimento,
        total_distretti=sum(len(item.distretti) for item in items),
        total_particelle=sum(item.particelle_count for item in items),
        available_colture=sorted(available_colture, key=lambda item: item.lower()),
        items=items,
        ruolo_reconciliation=build_ruolo_reconciliation(db, anno_riferimento),
    )


# Bump quando cambia la struttura o la semantica del payload snapshot, per invalidare le cache esistenti.
_OVERVIEW_PAYLOAD_VERSION = 6


def _to_signature_fragment(count: int, timestamp: datetime | None) -> str:
    return f"{count}:{timestamp.isoformat() if timestamp is not None else '-'}"


def build_indici_overview_source_signature(db: Session, anno_riferimento: int) -> str:
    particelle_count, particelle_updated_at = db.execute(
        select(func.count(CatParticella.id), func.max(CatParticella.updated_at)).where(
            CatParticella.is_current.is_(True),
            CatParticella.num_distretto.is_not(None),
        )
    ).one()
    distretti_count, distretti_updated_at = db.execute(
        select(func.count(CatDistretto.id), func.max(CatDistretto.updated_at)).where(CatDistretto.attivo.is_(True))
    ).one()
    ruolo_count, ruolo_created_at, ruolo_linked_count = db.execute(
        select(
            func.count(RuoloParticella.id),
            func.max(RuoloParticella.created_at),
            func.count(RuoloParticella.cat_particella_id),
        ).where(RuoloParticella.anno_tributario == anno_riferimento)
    ).one()

    return "|".join(
        [
            f"v={_OVERVIEW_PAYLOAD_VERSION}",
            f"anno={anno_riferimento}",
            f"particelle={_to_signature_fragment(int(particelle_count or 0), particelle_updated_at)}",
            f"distretti={_to_signature_fragment(int(distretti_count or 0), distretti_updated_at)}",
            f"ruolo={_to_signature_fragment(int(ruolo_count or 0), ruolo_created_at)}",
            f"ruolo_linked={int(ruolo_linked_count or 0)}",
        ]
    )


def get_indici_overview_cached(db: Session, anno: int | None, refresh: bool = False) -> CatIndiceOverviewResponse:
    anno_riferimento = resolve_anno_riferimento(db, anno)
    if anno_riferimento is None:
        return build_indici_overview(db, anno=None)

    source_signature = build_indici_overview_source_signature(db, anno_riferimento)
    snapshot = db.scalar(
        select(CatIndiceOverviewSnapshot).where(CatIndiceOverviewSnapshot.anno_riferimento == anno_riferimento)
    )
    if snapshot is not None and not refresh and snapshot.source_signature == source_signature:
        return CatIndiceOverviewResponse.model_validate(snapshot.payload_json)

    payload = build_indici_overview(db, anno=anno_riferimento)
    payload_json = payload.model_dump(mode="json")
    if snapshot is None:
        snapshot = CatIndiceOverviewSnapshot(
            anno_riferimento=anno_riferimento,
            source_signature=source_signature,
            payload_json=payload_json,
        )
        db.add(snapshot)
    else:
        snapshot.source_signature = source_signature
        snapshot.payload_json = payload_json

    db.commit()
    return payload
