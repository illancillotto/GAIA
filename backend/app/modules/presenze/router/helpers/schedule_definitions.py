from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

@dataclass(frozen=True)
class _BootstrapRuleDefinition:
    label: str | None
    weekday: int | None
    recurrence_kind: str
    start_time: time
    end_time: time
    week_of_month: int | None = None
    interval_weeks: int | None = None
    anchor_date: date | None = None
    season_start_month: int | None = None
    season_start_day: int | None = None
    season_end_month: int | None = None
    season_end_day: int | None = None
    applies_on_holiday: bool = False
    ordinary_label: str | None = None
    sort_order: int = 0


@dataclass(frozen=True)
class _BootstrapTemplatePreset:
    preset_key: str
    template_code: str
    template_label: str
    template_notes: str
    source_schedule_codes: tuple[str, ...]
    rules: tuple[_BootstrapRuleDefinition, ...]


@dataclass(frozen=True)
class _SystemScheduleTemplateDefinition:
    code: str
    label: str
    company_code: str | None
    notes: str
    rules: tuple[_BootstrapRuleDefinition, ...] = ()


@dataclass(frozen=True)
class _ScheduleProfileDefinition:
    profile_code: str
    profile_label: str
    description: str
    default_template_code: str | None
    template_codes: tuple[str, ...]
    assignable_template_codes: tuple[str, ...]
    inherited_template_codes: tuple[str, ...]
    rule_summaries: tuple[str, ...]


_OPERAI_SUMMER_START_MONTH = 6
_OPERAI_SUMMER_START_DAY = 1
_OPERAI_SUMMER_END_MONTH = 9
_OPERAI_SUMMER_END_DAY = 30


BOOTSTRAP_TEMPLATE_PRESETS: tuple[_BootstrapTemplatePreset, ...] = (
    _BootstrapTemplatePreset(
        preset_key="operai_0714_primo_terzo_sabato",
        template_code="OPE0714_1E3SAB",
        template_label="Operai 07:00-14:00 con 1° e 3° sabato",
        template_notes=(
            "Generato da INAZ: OPE0714 / OPE0613 / OP_5.3_12.3 + OPESAB / OSAB5.3_12.3. "
            "Default GAIA: fascia estiva 01/06-30/09 con timbrature anticipate ma ore operaio invariate. "
            "Verificare i sabati 1° e 3° del mese."
        ),
        source_schedule_codes=("OPE0714", "OPE0613", "OP_5.3_12.3", "OPESAB", "OSAB5.3_12.3"),
        rules=(
            _BootstrapRuleDefinition(
                label="Lun 07:00-14:00",
                weekday=0,
                recurrence_kind="weekly",
                start_time=time(7, 0),
                end_time=time(14, 0),
                season_start_month=10,
                season_start_day=1,
                season_end_month=_OPERAI_SUMMER_START_MONTH,
                season_end_day=_OPERAI_SUMMER_START_DAY - 1,
                ordinary_label="OPE0714",
                sort_order=0,
            ),
            _BootstrapRuleDefinition(
                label="Lun 05:30-12:30",
                weekday=0,
                recurrence_kind="weekly",
                start_time=time(5, 30),
                end_time=time(12, 30),
                season_start_month=_OPERAI_SUMMER_START_MONTH,
                season_start_day=_OPERAI_SUMMER_START_DAY,
                season_end_month=_OPERAI_SUMMER_END_MONTH,
                season_end_day=_OPERAI_SUMMER_END_DAY,
                ordinary_label="OP_5.3_12.3",
                sort_order=5,
            ),
            _BootstrapRuleDefinition(
                label="Mar 07:00-14:00",
                weekday=1,
                recurrence_kind="weekly",
                start_time=time(7, 0),
                end_time=time(14, 0),
                season_start_month=10,
                season_start_day=1,
                season_end_month=_OPERAI_SUMMER_START_MONTH,
                season_end_day=_OPERAI_SUMMER_START_DAY - 1,
                ordinary_label="OPE0714",
                sort_order=10,
            ),
            _BootstrapRuleDefinition(
                label="Mar 05:30-12:30",
                weekday=1,
                recurrence_kind="weekly",
                start_time=time(5, 30),
                end_time=time(12, 30),
                season_start_month=_OPERAI_SUMMER_START_MONTH,
                season_start_day=_OPERAI_SUMMER_START_DAY,
                season_end_month=_OPERAI_SUMMER_END_MONTH,
                season_end_day=_OPERAI_SUMMER_END_DAY,
                ordinary_label="OP_5.3_12.3",
                sort_order=15,
            ),
            _BootstrapRuleDefinition(
                label="Mer 07:00-14:00",
                weekday=2,
                recurrence_kind="weekly",
                start_time=time(7, 0),
                end_time=time(14, 0),
                season_start_month=10,
                season_start_day=1,
                season_end_month=_OPERAI_SUMMER_START_MONTH,
                season_end_day=_OPERAI_SUMMER_START_DAY - 1,
                ordinary_label="OPE0714",
                sort_order=20,
            ),
            _BootstrapRuleDefinition(
                label="Mer 05:30-12:30",
                weekday=2,
                recurrence_kind="weekly",
                start_time=time(5, 30),
                end_time=time(12, 30),
                season_start_month=_OPERAI_SUMMER_START_MONTH,
                season_start_day=_OPERAI_SUMMER_START_DAY,
                season_end_month=_OPERAI_SUMMER_END_MONTH,
                season_end_day=_OPERAI_SUMMER_END_DAY,
                ordinary_label="OP_5.3_12.3",
                sort_order=25,
            ),
            _BootstrapRuleDefinition(
                label="Gio 07:00-14:00",
                weekday=3,
                recurrence_kind="weekly",
                start_time=time(7, 0),
                end_time=time(14, 0),
                season_start_month=10,
                season_start_day=1,
                season_end_month=_OPERAI_SUMMER_START_MONTH,
                season_end_day=_OPERAI_SUMMER_START_DAY - 1,
                ordinary_label="OPE0714",
                sort_order=30,
            ),
            _BootstrapRuleDefinition(
                label="Gio 05:30-12:30",
                weekday=3,
                recurrence_kind="weekly",
                start_time=time(5, 30),
                end_time=time(12, 30),
                season_start_month=_OPERAI_SUMMER_START_MONTH,
                season_start_day=_OPERAI_SUMMER_START_DAY,
                season_end_month=_OPERAI_SUMMER_END_MONTH,
                season_end_day=_OPERAI_SUMMER_END_DAY,
                ordinary_label="OP_5.3_12.3",
                sort_order=35,
            ),
            _BootstrapRuleDefinition(
                label="Ven 07:00-14:00",
                weekday=4,
                recurrence_kind="weekly",
                start_time=time(7, 0),
                end_time=time(14, 0),
                season_start_month=10,
                season_start_day=1,
                season_end_month=_OPERAI_SUMMER_START_MONTH,
                season_end_day=_OPERAI_SUMMER_START_DAY - 1,
                ordinary_label="OPE0714",
                sort_order=40,
            ),
            _BootstrapRuleDefinition(
                label="Ven 05:30-12:30",
                weekday=4,
                recurrence_kind="weekly",
                start_time=time(5, 30),
                end_time=time(12, 30),
                season_start_month=_OPERAI_SUMMER_START_MONTH,
                season_start_day=_OPERAI_SUMMER_START_DAY,
                season_end_month=_OPERAI_SUMMER_END_MONTH,
                season_end_day=_OPERAI_SUMMER_END_DAY,
                ordinary_label="OP_5.3_12.3",
                sort_order=45,
            ),
            _BootstrapRuleDefinition(
                label="1° sabato 07:00-13:30",
                weekday=5,
                recurrence_kind="first_weekday_of_month",
                start_time=time(7, 0),
                end_time=time(13, 30),
                season_start_month=10,
                season_start_day=1,
                season_end_month=_OPERAI_SUMMER_START_MONTH,
                season_end_day=_OPERAI_SUMMER_START_DAY - 1,
                ordinary_label="OPESAB",
                sort_order=50,
            ),
            _BootstrapRuleDefinition(
                label="1° sabato 05:30-12:30",
                weekday=5,
                recurrence_kind="first_weekday_of_month",
                start_time=time(5, 30),
                end_time=time(12, 30),
                season_start_month=_OPERAI_SUMMER_START_MONTH,
                season_start_day=_OPERAI_SUMMER_START_DAY,
                season_end_month=_OPERAI_SUMMER_END_MONTH,
                season_end_day=_OPERAI_SUMMER_END_DAY,
                ordinary_label="OSAB5.3_12.3",
                sort_order=55,
            ),
            _BootstrapRuleDefinition(
                label="3° sabato 07:00-13:30",
                weekday=5,
                recurrence_kind="nth_weekday_of_month",
                week_of_month=3,
                start_time=time(7, 0),
                end_time=time(13, 30),
                season_start_month=10,
                season_start_day=1,
                season_end_month=_OPERAI_SUMMER_START_MONTH,
                season_end_day=_OPERAI_SUMMER_START_DAY - 1,
                ordinary_label="OPESAB",
                sort_order=60,
            ),
            _BootstrapRuleDefinition(
                label="3° sabato 05:30-12:30",
                weekday=5,
                recurrence_kind="nth_weekday_of_month",
                week_of_month=3,
                start_time=time(5, 30),
                end_time=time(12, 30),
                season_start_month=_OPERAI_SUMMER_START_MONTH,
                season_start_day=_OPERAI_SUMMER_START_DAY,
                season_end_month=_OPERAI_SUMMER_END_MONTH,
                season_end_day=_OPERAI_SUMMER_END_DAY,
                ordinary_label="OSAB5.3_12.3",
                sort_order=65,
            ),
        ),
    ),
    _BootstrapTemplatePreset(
        preset_key="impiegati_flessibile",
        template_code="IMP1_STD",
        template_label="Impiegati flessibile 07:35-14:00",
        template_notes="Generato da INAZ: IMP1.",
        source_schedule_codes=("IMP1",),
        rules=tuple(
            _BootstrapRuleDefinition(
                label=f"Giorno feriale {weekday}",
                weekday=weekday,
                recurrence_kind="weekly",
                start_time=time(7, 35),
                end_time=time(14, 0),
                ordinary_label="IMP1",
                sort_order=weekday,
            )
            for weekday in range(5)
        ),
    ),
    _BootstrapTemplatePreset(
        preset_key="impiegati_rientro",
        template_code="IMP1_RIENTRO",
        template_label="Impiegati con rientro 07:35-14:00 / 14:30-17:45",
        template_notes="Generato da INAZ: IMP1 + RIENTRO IMP.",
        source_schedule_codes=("IMP1", "RIENTRO IMP"),
        rules=(
            *tuple(
                _BootstrapRuleDefinition(
                    label=f"Giorno feriale {weekday}",
                    weekday=weekday,
                    recurrence_kind="weekly",
                    start_time=time(7, 35),
                    end_time=time(14, 0),
                    ordinary_label="IMP1",
                    sort_order=weekday,
                )
                for weekday in range(5)
            ),
            _BootstrapRuleDefinition(
                label="Rientro lunedi pomeriggio",
                weekday=0,
                recurrence_kind="weekly",
                start_time=time(14, 30),
                end_time=time(17, 45),
                ordinary_label="RIENTRO IMP",
                sort_order=10,
            ),
        ),
    ),
    _BootstrapTemplatePreset(
        preset_key="operai_0620_1356",
        template_code="OPE0736_STD",
        template_label="Operai 06:20-13:56",
        template_notes="Generato da INAZ: OPE0736.",
        source_schedule_codes=("OPE0736",),
        rules=tuple(
            _BootstrapRuleDefinition(
                label=f"Giorno feriale {weekday}",
                weekday=weekday,
                recurrence_kind="weekly",
                start_time=time(6, 20),
                end_time=time(13, 56),
                ordinary_label="OPE0736",
                sort_order=weekday,
            )
            for weekday in range(5)
        ),
    ),
)

SYSTEM_SCHEDULE_TEMPLATE_DEFINITIONS: tuple[_SystemScheduleTemplateDefinition, ...] = (
    _SystemScheduleTemplateDefinition(
        code="OPE0613",
        label="Operai 06:00-13:00",
        company_code="53",
        notes="Template orario feriale per codice INAZ OPE0613. Per gli operai il teorico resta 7h e viene verificato dal motore legato a operai_group.",
        rules=tuple(
            _BootstrapRuleDefinition(
                label=f"Giorno feriale {weekday}",
                weekday=weekday,
                recurrence_kind="weekly",
                start_time=time(6, 0),
                end_time=time(13, 0),
                ordinary_label="OPE0613",
                sort_order=weekday,
            )
            for weekday in range(5)
        ),
    ),
    _SystemScheduleTemplateDefinition(
        code="OP_5.3_12.3",
        label="Operai 05:30-12:30",
        company_code="53",
        notes="Template orario feriale per codice INAZ OP_5.3_12.3. Per gli operai i minuti attesi restano comunque verificati dal motore legato a operai_group.",
        rules=tuple(
            _BootstrapRuleDefinition(
                label=f"Giorno feriale {weekday}",
                weekday=weekday,
                recurrence_kind="weekly",
                start_time=time(5, 30),
                end_time=time(12, 30),
                ordinary_label="OP_5.3_12.3",
                sort_order=weekday,
            )
            for weekday in range(5)
        ),
    ),
    _SystemScheduleTemplateDefinition(
        code="OSAB5.3_12.3",
        label="Operai sabato 05:30-12:30",
        company_code="53",
        notes="Template orario sabato per codice INAZ OSAB5.3_12.3. Non impone da solo i minuti nominali: per gli operai il teorico del sabato resta definito da operai_group (agrario 6h30, catasto/magazzino 6h).",
    ),
)

SCHEDULE_PROFILE_DEFINITIONS: tuple[_ScheduleProfileDefinition, ...] = (
    _ScheduleProfileDefinition(
        profile_code="operai_gaia",
        profile_label="Profilo Operai",
        description=(
            "Controllo rigido delle ore effettive con assegnazione flessibile del turno INAZ: "
            "agrario e catasto/magazzino condividono il profilo, ma hanno regole sabato diverse."
        ),
        default_template_code="OPE0714_1E3SAB",
        template_codes=("OPE0714_1E3SAB", "OPE0736_STD", "OPE0613", "OP_5.3_12.3", "OSAB5.3_12.3"),
        assignable_template_codes=("OPE0714_1E3SAB", "OPE0736_STD"),
        inherited_template_codes=("OPE0613", "OP_5.3_12.3", "OSAB5.3_12.3"),
        rule_summaries=("Feriale 7h", "Agrario sabato 6h30", "Catasto/magazzino sabato 6h"),
    ),
    _ScheduleProfileDefinition(
        profile_code="impiegati_gaia",
        profile_label="Profilo Impiegati",
        description=(
            "Profilo gestionale per impiegati con orari INAZ flessibili, rientri e controllo banca ore "
            "separato dalle regole rigide degli operai."
        ),
        default_template_code="IMP1_STD",
        template_codes=("IMP1_STD", "IMP1_RIENTRO"),
        assignable_template_codes=("IMP1_STD", "IMP1_RIENTRO"),
        inherited_template_codes=(),
        rule_summaries=("Flessibile IMP1", "Rientro lunedi pomeriggio", "Controllo banca ore / anomalie"),
    ),
)

# fmt: on

__all__ = [
    "BOOTSTRAP_TEMPLATE_PRESETS",
    "SCHEDULE_PROFILE_DEFINITIONS",
    "SYSTEM_SCHEDULE_TEMPLATE_DEFINITIONS",
    "_OPERAI_SUMMER_END_DAY",
    "_OPERAI_SUMMER_END_MONTH",
    "_OPERAI_SUMMER_START_DAY",
    "_OPERAI_SUMMER_START_MONTH",
    "_BootstrapRuleDefinition",
    "_BootstrapTemplatePreset",
    "_ScheduleProfileDefinition",
    "_SystemScheduleTemplateDefinition",
]
