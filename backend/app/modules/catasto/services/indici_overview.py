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
from app.modules.ruolo.models import RuoloParticella
from app.schemas.catasto_phase1 import (
    CatIndiceBreakdownSummaryResponse,
    CatIndiceColturaSummaryResponse,
    CatIndiceDistrettoSummaryResponse,
    CatIndiceGroupSummaryResponse,
    CatIndiceOverviewResponse,
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
    )


# Bump quando cambia la struttura o la semantica del payload snapshot, per invalidare le cache esistenti.
_OVERVIEW_PAYLOAD_VERSION = 5


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
    ruolo_count, ruolo_created_at = db.execute(
        select(func.count(RuoloParticella.id), func.max(RuoloParticella.created_at)).where(
            RuoloParticella.cat_particella_id.is_not(None),
            RuoloParticella.anno_tributario == anno_riferimento,
        )
    ).one()

    return "|".join(
        [
            f"v={_OVERVIEW_PAYLOAD_VERSION}",
            f"anno={anno_riferimento}",
            f"particelle={_to_signature_fragment(int(particelle_count or 0), particelle_updated_at)}",
            f"distretti={_to_signature_fragment(int(distretti_count or 0), distretti_updated_at)}",
            f"ruolo={_to_signature_fragment(int(ruolo_count or 0), ruolo_created_at)}",
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
