from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import String, desc, func, literal, select
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import CatMeterReading, CatParticella
from app.modules.catasto.services.indici import get_indice_metadata
from app.modules.catasto.services.irrigation_tariffs import build_irrigation_tariff_preview
from app.modules.catasto.services.meter_reading_consumption import effective_consumption_mc
from app.modules.ruolo.models import RuoloParticella, RuoloPartita
from app.schemas.catasto_phase1 import (
    CatColturaBreakdownItemResponse,
    CatColturaOverviewResponse,
    CatColturaSummaryResponse,
    CatColturaYearItemResponse,
)


def _normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.strip().split()).upper()


def _decimal(value: object | None) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _safe_ratio(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _label_or_default(value: str | None, fallback: str) -> str:
    normalized = " ".join((value or "").strip().split())
    return normalized or fallback


def _role_total_amount(item: RuoloParticella, particella: CatParticella | None) -> Decimal:
    importo_totale = _decimal(item.importo_manut) + _decimal(item.importo_irrig) + _decimal(item.importo_ist)
    if importo_totale > 0:
        return importo_totale
    preview = build_irrigation_tariff_preview(
        coltura=item.coltura,
        sup_irrigata_ha=_decimal(item.sup_irrigata_ha) if item.sup_irrigata_ha is not None else None,
        nome_distretto=particella.nome_distretto if particella is not None else item.distretto,
        num_distretto=particella.num_distretto if particella is not None else item.distretto,
        nome_comune=particella.nome_comune if particella is not None else None,
    )
    return preview.importo_stimato or Decimal("0")


def _legacy_role_partition_key():
    return (
        func.coalesce(RuoloPartita.comune_nome, "")
        + literal("|")
        + func.coalesce(RuoloParticella.distretto, "")
        + literal("|")
        + func.coalesce(RuoloParticella.foglio, "")
        + literal("|")
        + func.coalesce(RuoloParticella.particella, "")
        + literal("|")
        + func.coalesce(RuoloParticella.subalterno, "")
    )


def _build_latest_role_rows_query():
    identity_key = func.coalesce(
        func.cast(RuoloParticella.cat_particella_id, String),
        func.cast(RuoloParticella.catasto_parcel_id, String),
        _legacy_role_partition_key(),
    )
    ranked = (
        select(
            RuoloParticella.id.label("ruolo_particella_id"),
            func.row_number()
            .over(
                partition_by=(RuoloParticella.anno_tributario, identity_key),
                order_by=(desc(RuoloParticella.created_at), desc(RuoloParticella.id)),
            )
            .label("rn"),
        )
        .join(RuoloPartita, RuoloPartita.id == RuoloParticella.partita_id)
        .where(RuoloParticella.coltura.is_not(None))
        .subquery()
    )
    return (
        select(RuoloParticella, CatParticella)
        .join(ranked, ranked.c.ruolo_particella_id == RuoloParticella.id)
        .outerjoin(CatParticella, CatParticella.id == RuoloParticella.cat_particella_id)
        .where(ranked.c.rn == 1)
    )


@dataclass(slots=True)
class _BreakdownAccumulator:
    key: str
    label: str
    role_particella_ids: set[object] = field(default_factory=set)
    meter_point_keys: set[str] = field(default_factory=set)
    role_particelle_count: int = 0
    meter_readings_count: int = 0
    meter_points_count: int = 0
    superficie_irrigata_ha: Decimal = Decimal("0")
    importo_totale: Decimal = Decimal("0")
    consumo_reale_mc: Decimal = Decimal("0")

    def add_role(self, particella_id: object | None, superficie_irrigata_ha: Decimal, importo_totale: Decimal) -> None:
        if particella_id is not None and particella_id not in self.role_particella_ids:
            self.role_particella_ids.add(particella_id)
            self.role_particelle_count += 1
        self.superficie_irrigata_ha += superficie_irrigata_ha
        self.importo_totale += importo_totale

    def add_meter(self, point_key: str, consumo_reale_mc: Decimal) -> None:
        self.meter_readings_count += 1
        if point_key and point_key not in self.meter_point_keys:
            self.meter_point_keys.add(point_key)
            self.meter_points_count += 1
        self.consumo_reale_mc += consumo_reale_mc


@dataclass(slots=True)
class _ColturaAccumulator:
    key: str
    coltura: str
    gruppo_coltura: str | None
    role_particella_ids: set[object] = field(default_factory=set)
    meter_point_keys: set[str] = field(default_factory=set)
    role_particelle_count: int = 0
    meter_readings_count: int = 0
    meter_points_count: int = 0
    superficie_irrigata_ha: Decimal = Decimal("0")
    importo_totale: Decimal = Decimal("0")
    consumo_reale_mc: Decimal = Decimal("0")
    distretti: dict[str, _BreakdownAccumulator] = field(default_factory=dict)
    indici: dict[str, _BreakdownAccumulator] = field(default_factory=dict)
    comuni: dict[str, _BreakdownAccumulator] = field(default_factory=dict)
    years: dict[int, _BreakdownAccumulator] = field(default_factory=dict)

    def _bucket(self, store: dict[str, _BreakdownAccumulator], key: str, label: str) -> _BreakdownAccumulator:
        return store.setdefault(key, _BreakdownAccumulator(key=key, label=label))

    def _year_bucket(self, year: int) -> _BreakdownAccumulator:
        return self.years.setdefault(year, _BreakdownAccumulator(key=str(year), label=str(year)))

    def add_role(
        self,
        *,
        year: int,
        particella_id: object | None,
        superficie_irrigata_ha: Decimal,
        importo_totale: Decimal,
        distretto_key: str,
        distretto_label: str,
        indice_key: str,
        indice_label: str,
        comune_key: str,
        comune_label: str,
    ) -> None:
        if particella_id is not None and particella_id not in self.role_particella_ids:
            self.role_particella_ids.add(particella_id)
            self.role_particelle_count += 1
        self.superficie_irrigata_ha += superficie_irrigata_ha
        self.importo_totale += importo_totale
        self._bucket(self.distretti, distretto_key, distretto_label).add_role(particella_id, superficie_irrigata_ha, importo_totale)
        self._bucket(self.indici, indice_key, indice_label).add_role(particella_id, superficie_irrigata_ha, importo_totale)
        self._bucket(self.comuni, comune_key, comune_label).add_role(particella_id, superficie_irrigata_ha, importo_totale)
        self._year_bucket(year).add_role(particella_id, superficie_irrigata_ha, importo_totale)

    def add_meter(
        self,
        *,
        year: int,
        point_key: str,
        consumo_reale_mc: Decimal,
        distretto_key: str,
        distretto_label: str,
        indice_key: str,
        indice_label: str,
        comune_key: str,
        comune_label: str,
    ) -> None:
        self.meter_readings_count += 1
        if point_key and point_key not in self.meter_point_keys:
            self.meter_point_keys.add(point_key)
            self.meter_points_count += 1
        self.consumo_reale_mc += consumo_reale_mc
        self._bucket(self.distretti, distretto_key, distretto_label).add_meter(point_key, consumo_reale_mc)
        self._bucket(self.indici, indice_key, indice_label).add_meter(point_key, consumo_reale_mc)
        self._bucket(self.comuni, comune_key, comune_label).add_meter(point_key, consumo_reale_mc)
        self._year_bucket(year).add_meter(point_key, consumo_reale_mc)


def _serialize_breakdown(accumulator: _BreakdownAccumulator) -> CatColturaBreakdownItemResponse:
    return CatColturaBreakdownItemResponse(
        key=accumulator.key,
        label=accumulator.label,
        role_particelle_count=accumulator.role_particelle_count,
        meter_readings_count=accumulator.meter_readings_count,
        meter_points_count=accumulator.meter_points_count,
        superficie_irrigata_ha=accumulator.superficie_irrigata_ha,
        importo_totale=accumulator.importo_totale,
        consumo_reale_mc=accumulator.consumo_reale_mc,
        euro_per_ha=_safe_ratio(accumulator.importo_totale, accumulator.superficie_irrigata_ha),
        euro_per_mc=_safe_ratio(accumulator.importo_totale, accumulator.consumo_reale_mc),
        mc_per_ha=_safe_ratio(accumulator.consumo_reale_mc, accumulator.superficie_irrigata_ha),
    )


def _serialize_year(accumulator: _BreakdownAccumulator, anno: int) -> CatColturaYearItemResponse:
    return CatColturaYearItemResponse(
        anno=anno,
        key=accumulator.key,
        label=accumulator.label,
        role_particelle_count=accumulator.role_particelle_count,
        meter_readings_count=accumulator.meter_readings_count,
        meter_points_count=accumulator.meter_points_count,
        superficie_irrigata_ha=accumulator.superficie_irrigata_ha,
        importo_totale=accumulator.importo_totale,
        consumo_reale_mc=accumulator.consumo_reale_mc,
        euro_per_ha=_safe_ratio(accumulator.importo_totale, accumulator.superficie_irrigata_ha),
        euro_per_mc=_safe_ratio(accumulator.importo_totale, accumulator.consumo_reale_mc),
        mc_per_ha=_safe_ratio(accumulator.consumo_reale_mc, accumulator.superficie_irrigata_ha),
    )


def _quality_badge(accumulator: _ColturaAccumulator) -> str:
    has_role = accumulator.role_particelle_count > 0 or accumulator.importo_totale > 0 or accumulator.superficie_irrigata_ha > 0
    has_meter = accumulator.meter_readings_count > 0 or accumulator.consumo_reale_mc > 0
    if has_role and has_meter:
        return "misto"
    if has_meter:
        return "reale"
    return "stimato"


def _serialize_crop(accumulator: _ColturaAccumulator) -> CatColturaSummaryResponse:
    distretti = sorted(
        (_serialize_breakdown(item) for item in accumulator.distretti.values()),
        key=lambda item: (-item.importo_totale, -item.consumo_reale_mc, item.label.lower()),
    )
    indici = sorted(
        (_serialize_breakdown(item) for item in accumulator.indici.values()),
        key=lambda item: (-item.importo_totale, -item.consumo_reale_mc, item.label.lower()),
    )
    comuni = sorted(
        (_serialize_breakdown(item) for item in accumulator.comuni.values()),
        key=lambda item: (-item.importo_totale, -item.consumo_reale_mc, item.label.lower()),
    )
    years = [
        _serialize_year(year_accumulator, anno)
        for anno, year_accumulator in sorted(accumulator.years.items(), key=lambda item: item[0], reverse=True)
    ]
    return CatColturaSummaryResponse(
        coltura=accumulator.coltura,
        gruppo_coltura=accumulator.gruppo_coltura,
        quality_badge=_quality_badge(accumulator),
        role_particelle_count=accumulator.role_particelle_count,
        meter_readings_count=accumulator.meter_readings_count,
        meter_points_count=accumulator.meter_points_count,
        distretti_count=len(accumulator.distretti),
        indici_count=len(accumulator.indici),
        comuni_count=len(accumulator.comuni),
        superficie_irrigata_ha=accumulator.superficie_irrigata_ha,
        importo_totale=accumulator.importo_totale,
        consumo_reale_mc=accumulator.consumo_reale_mc,
        euro_per_ha=_safe_ratio(accumulator.importo_totale, accumulator.superficie_irrigata_ha),
        euro_per_mc=_safe_ratio(accumulator.importo_totale, accumulator.consumo_reale_mc),
        mc_per_ha=_safe_ratio(accumulator.consumo_reale_mc, accumulator.superficie_irrigata_ha),
        distretti=distretti,
        indici=indici,
        comuni=comuni,
        years=years,
    )


def build_colture_overview(db: Session, anno: int | None = None) -> CatColturaOverviewResponse:
    role_years = [int(item) for item in db.execute(select(RuoloParticella.anno_tributario).distinct()).scalars().all() if item is not None]
    meter_years = [int(item) for item in db.execute(select(CatMeterReading.anno).distinct()).scalars().all() if item is not None]
    available_years = sorted(set(role_years + meter_years), reverse=True)
    anno_riferimento = anno if anno is not None else (available_years[0] if available_years else None)

    role_rows = db.execute(_build_latest_role_rows_query()).all()
    meter_rows = db.execute(select(CatMeterReading).where(CatMeterReading.coltura.is_not(None))).scalars().all()

    selected_accumulators: dict[str, _ColturaAccumulator] = {}
    available_groups: set[str] = set()
    available_distretti: set[str] = set()
    available_comuni: set[str] = set()
    available_indici: set[str] = set()

    yearly_accumulators: dict[str, _ColturaAccumulator] = {}

    def crop_acc(store: dict[str, _ColturaAccumulator], coltura_label: str, gruppo_label: str | None) -> _ColturaAccumulator:
        key = _normalize_text(coltura_label)
        item = store.get(key)
        if item is None:
            item = _ColturaAccumulator(key=key, coltura=coltura_label, gruppo_coltura=gruppo_label)
            store[key] = item
        elif item.gruppo_coltura is None and gruppo_label is not None:
            item.gruppo_coltura = gruppo_label
        return item

    for ruolo_particella, particella in role_rows:
        crop_label = _label_or_default(ruolo_particella.coltura, "Coltura non indicata")
        year = int(ruolo_particella.anno_tributario)
        superficie_irrigata_ha = _decimal(ruolo_particella.sup_irrigata_ha)
        importo_totale = _role_total_amount(ruolo_particella, particella)
        nome_distretto = particella.nome_distretto if particella is not None else ruolo_particella.distretto
        num_distretto = particella.num_distretto if particella is not None else ruolo_particella.distretto
        nome_comune = particella.nome_comune if particella is not None else None
        preview = build_irrigation_tariff_preview(
            coltura=ruolo_particella.coltura,
            sup_irrigata_ha=superficie_irrigata_ha if ruolo_particella.sup_irrigata_ha is not None else None,
            nome_distretto=nome_distretto,
            num_distretto=num_distretto,
            nome_comune=nome_comune,
        )
        indice_metadata = get_indice_metadata(num_distretto)
        gruppo_label = preview.crop_group_label
        if gruppo_label:
            available_groups.add(gruppo_label)
        distretto_key = _normalize_text(num_distretto or nome_distretto or "SENZA_DISTRETTO")
        distretto_label = _label_or_default(f"{num_distretto or '—'} · {nome_distretto or 'Distretto non indicato'}", "Distretto non indicato")
        comune_key = _normalize_text(nome_comune or "COMUNE_NON_INDICATO")
        comune_label = _label_or_default(nome_comune, "Comune non indicato")
        indice_key = indice_metadata.key
        indice_label = indice_metadata.label

        yearly_crop = crop_acc(yearly_accumulators, crop_label, gruppo_label)
        yearly_crop.add_role(
            year=year,
            particella_id=ruolo_particella.cat_particella_id,
            superficie_irrigata_ha=superficie_irrigata_ha,
            importo_totale=importo_totale,
            distretto_key=distretto_key,
            distretto_label=distretto_label,
            indice_key=indice_key,
            indice_label=indice_label,
            comune_key=comune_key,
            comune_label=comune_label,
        )

        if anno_riferimento is None or year != anno_riferimento:
            continue
        available_distretti.add(distretto_label)
        available_comuni.add(comune_label)
        available_indici.add(indice_label)
        selected_crop = crop_acc(selected_accumulators, crop_label, gruppo_label)
        selected_crop.add_role(
            year=year,
            particella_id=ruolo_particella.cat_particella_id,
            superficie_irrigata_ha=superficie_irrigata_ha,
            importo_totale=importo_totale,
            distretto_key=distretto_key,
            distretto_label=distretto_label,
            indice_key=indice_key,
            indice_label=indice_label,
            comune_key=comune_key,
            comune_label=comune_label,
        )

    for meter_reading in meter_rows:
        crop_label = _label_or_default(meter_reading.coltura, "Coltura non indicata")
        year = int(meter_reading.anno)
        consumo_reale_mc = effective_consumption_mc(
            consumo_mc=meter_reading.consumo_mc,
            lettura_iniziale=meter_reading.lettura_iniziale,
            lettura_finale=meter_reading.lettura_finale,
        )
        if consumo_reale_mc is None:
            continue

        distretto_label = _label_or_default(meter_reading.punto_consegna, "Punto non indicato")
        distretto_key = _normalize_text(meter_reading.distretto.num_distretto if meter_reading.distretto is not None else distretto_label)
        if meter_reading.distretto is not None:
            distretto_label = _label_or_default(
                f"{meter_reading.distretto.num_distretto} · {meter_reading.distretto.nome_distretto or 'Distretto non indicato'}",
                distretto_label,
            )
            indice_metadata = get_indice_metadata(meter_reading.distretto.num_distretto)
        else:
            indice_metadata = get_indice_metadata(None)
        comune_label = "Comune non dedotto"
        comune_key = "COMUNE_NON_DEDOTTO"
        indice_key = indice_metadata.key
        indice_label = indice_metadata.label
        gruppo_label = build_irrigation_tariff_preview(
            coltura=meter_reading.coltura,
            sup_irrigata_ha=None,
            nome_distretto=meter_reading.distretto.nome_distretto if meter_reading.distretto is not None else None,
            num_distretto=meter_reading.distretto.num_distretto if meter_reading.distretto is not None else None,
            nome_comune=None,
        ).crop_group_label
        if gruppo_label:
            available_groups.add(gruppo_label)

        point_key = _normalize_text(f"{meter_reading.punto_consegna}|{meter_reading.matricola or ''}")
        yearly_crop = crop_acc(yearly_accumulators, crop_label, gruppo_label)
        yearly_crop.add_meter(
            year=year,
            point_key=point_key,
            consumo_reale_mc=_decimal(consumo_reale_mc),
            distretto_key=distretto_key,
            distretto_label=distretto_label,
            indice_key=indice_key,
            indice_label=indice_label,
            comune_key=comune_key,
            comune_label=comune_label,
        )

        if anno_riferimento is None or year != anno_riferimento:
            continue
        available_distretti.add(distretto_label)
        available_comuni.add(comune_label)
        available_indici.add(indice_label)
        selected_crop = crop_acc(selected_accumulators, crop_label, gruppo_label)
        selected_crop.add_meter(
            year=year,
            point_key=point_key,
            consumo_reale_mc=_decimal(consumo_reale_mc),
            distretto_key=distretto_key,
            distretto_label=distretto_label,
            indice_key=indice_key,
            indice_label=indice_label,
            comune_key=comune_key,
            comune_label=comune_label,
        )

    for key, selected_crop in selected_accumulators.items():
        yearly_crop = yearly_accumulators.get(key)
        if yearly_crop is not None:
            selected_crop.years = yearly_crop.years

    items = sorted(
        (_serialize_crop(item) for item in selected_accumulators.values()),
        key=lambda item: (-item.importo_totale, -item.consumo_reale_mc, item.coltura.lower()),
    )

    return CatColturaOverviewResponse(
        anno_riferimento=anno_riferimento,
        available_years=available_years,
        available_groups=sorted(available_groups),
        available_distretti=sorted(available_distretti),
        available_indici=sorted(available_indici),
        available_comuni=sorted(available_comuni),
        total_colture=len(items),
        total_role_particelle=sum(item.role_particelle_count for item in items),
        total_meter_readings=sum(item.meter_readings_count for item in items),
        total_superficie_irrigata_ha=sum(item.superficie_irrigata_ha for item in items),
        total_importo_totale=sum(item.importo_totale for item in items),
        total_consumo_reale_mc=sum(item.consumo_reale_mc for item in items),
        items=items,
    )
