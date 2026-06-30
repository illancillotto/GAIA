from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import CatDistretto, CatIndiceOverviewSnapshot, CatParticella, CatUtenzaIrrigua
from app.modules.catasto.services.indici import get_indice_metadata
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
    hectares_reference_total: Decimal = Decimal("0")
    colture: dict[tuple[str, str | None], dict[str, object]] = field(default_factory=dict)
    comuni: dict[str, dict[str, object]] = field(default_factory=dict)
    distretti_analytics: dict[str, dict[str, object]] = field(default_factory=dict)


def _empty_breakdown_entry(*, key: str, label: str) -> dict[str, object]:
    return {
        "key": key,
        "label": label,
        "particelle_count": 0,
        "ruolo_particelle_count": 0,
        "particelle_con_anagrafica_count": 0,
        "superficie_irrigata_ha": Decimal("0"),
        "importo_stimato": Decimal("0"),
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
            )
            for value in items.values()
        ],
        key=lambda item: (-item.importo_stimato, -item.superficie_irrigata_ha, item.label.lower()),
    )


def resolve_anno_riferimento(db: Session, anno: int | None) -> int | None:
    if anno is not None:
        return anno
    latest = db.scalar(select(func.max(RuoloParticella.anno_tributario)))
    return int(latest) if latest is not None else None


def _load_latest_ruolo_rows(db: Session, particella_ids: list) -> dict:
    if not particella_ids:
        return {}
    rows_by_particella: dict = {}
    chunk_size = 2000
    for start in range(0, len(particella_ids), chunk_size):
        chunk = particella_ids[start:start + chunk_size]
        ranked = (
            select(
                RuoloParticella.cat_particella_id.label("particella_id"),
                RuoloParticella.coltura.label("coltura"),
                RuoloParticella.anno_tributario.label("anno_tributario"),
                RuoloParticella.sup_irrigata_ha.label("sup_irrigata_ha"),
                func.row_number()
                .over(
                    partition_by=RuoloParticella.cat_particella_id,
                    order_by=(desc(RuoloParticella.anno_tributario), desc(RuoloParticella.created_at)),
                )
                .label("rn"),
            )
            .where(
                RuoloParticella.cat_particella_id.in_(chunk),
                RuoloParticella.cat_particella_id.is_not(None),
            )
            .subquery()
        )
        rows = db.execute(select(ranked).where(ranked.c.rn == 1)).all()
        rows_by_particella.update({row.particella_id: row for row in rows})
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

    for distretto in distretti:
        metadata = get_indice_metadata(distretto.num_distretto)
        accumulator = accumulators.setdefault(
            metadata.key,
            _IndiceAccumulator(key=metadata.key, label=metadata.label, sort_order=metadata.sort_order),
        )
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
            distretto.num_distretto,
            _empty_breakdown_entry(
                key=distretto.num_distretto,
                label=f"{distretto.num_distretto} · {distretto.nome_distretto or 'Distretto'}",
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
        distretto_key = particella.num_distretto or "nd"
        distretto_entry = accumulator.distretti_analytics.setdefault(
            distretto_key,
            _empty_breakdown_entry(
                key=distretto_key,
                label=f"{distretto_key} · {particella.nome_distretto or 'Distretto'}",
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
        sup_irrigata_ha = Decimal(str(latest_ruolo.sup_irrigata_ha)) if latest_ruolo.sup_irrigata_ha is not None else Decimal("0")
        preview = build_irrigation_tariff_preview(
            coltura=latest_ruolo.coltura,
            sup_irrigata_ha=sup_irrigata_ha if latest_ruolo.sup_irrigata_ha is not None else None,
            nome_distretto=particella.nome_distretto,
            num_distretto=particella.num_distretto,
            nome_comune=particella.nome_comune,
        )
        accumulator.superficie_irrigata_ha += sup_irrigata_ha
        accumulator.importo_stimato += preview.importo_stimato or Decimal("0")
        comune_entry["superficie_irrigata_ha"] = Decimal(comune_entry["superficie_irrigata_ha"]) + sup_irrigata_ha
        comune_entry["importo_stimato"] = Decimal(comune_entry["importo_stimato"]) + (preview.importo_stimato or Decimal("0"))
        distretto_entry["superficie_irrigata_ha"] = Decimal(distretto_entry["superficie_irrigata_ha"]) + sup_irrigata_ha
        distretto_entry["importo_stimato"] = Decimal(distretto_entry["importo_stimato"]) + (preview.importo_stimato or Decimal("0"))

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
                },
            )
            crop_entry["particelle_count"] = int(crop_entry["particelle_count"]) + 1
            crop_entry["superficie_irrigata_ha"] = Decimal(crop_entry["superficie_irrigata_ha"]) + sup_irrigata_ha
            crop_entry["importo_stimato"] = Decimal(crop_entry["importo_stimato"]) + (preview.importo_stimato or Decimal("0"))

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
