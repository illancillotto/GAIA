"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { Badge } from "@/components/ui/badge";
import {
  applyPresenzeScheduleBootstrap,
  createPresenzeCollaboratorScheduleAssignment,
  getPresenzeBankHoursGuidanceConfig,
  createPresenzeScheduleRule,
  createPresenzeScheduleTemplate,
  deletePresenzeScheduleRule,
  deletePresenzeScheduleTemplate,
  listAllPresenzeCollaborators,
  getPresenzeScheduleBootstrapPreview,
  listPresenzeBankHoursGuidanceConfigHistory,
  listPresenzeScheduleTemplates,
  updatePresenzeBankHoursGuidanceConfig,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type {
  PresenzeScheduleBootstrapCollaboratorSuggestion,
  PresenzeScheduleBootstrapApplyResponse,
  PresenzeScheduleBootstrapPreviewResponse,
  PresenzeScheduleBootstrapRulePreview,
  PresenzeScheduleProfilePreview,
  PresenzeBankHoursGuidanceConfig,
  PresenzeBankHoursGuidanceConfigRevision,
  PresenzeCollaborator,
  PresenzeScheduleRule,
  PresenzeScheduleTemplate,
} from "@/types/api";

type ScheduleDisplayRule = Pick<
  PresenzeScheduleRule | PresenzeScheduleBootstrapRulePreview,
  | "label"
  | "weekday"
  | "recurrence_kind"
  | "week_of_month"
  | "interval_weeks"
  | "anchor_date"
  | "start_time"
  | "end_time"
  | "season_start_month"
  | "season_start_day"
  | "season_end_month"
  | "season_end_day"
  | "applies_on_holiday"
  | "ordinary_label"
  | "sort_order"
>;

type CollaboratorProfileFilter = "all" | "operai_gaia" | "impiegati_gaia" | "unassigned";

const OPERAI_PROFILE_TEMPLATE_CODES = new Set(["OPE0714_1E3SAB", "OPE0736_STD", "OP_5.3_12.3", "OSAB5.3_12.3"]);
const IMPIEGATI_PROFILE_TEMPLATE_CODES = new Set(["IMP1_STD", "IMP1_RIENTRO"]);

const DEFAULT_GAIA_SCHEDULE_PROFILES: PresenzeScheduleProfilePreview[] = [
  {
    profile_code: "operai_gaia",
    profile_label: "Profilo Operai",
    description:
      "Controllo rigido delle ore effettive con assegnazione flessibile del turno INAZ: agrario e catasto/magazzino condividono il profilo, ma hanno regole sabato diverse.",
    default_template_code: "OPE0714_1E3SAB",
    template_codes: ["OPE0714_1E3SAB", "OPE0736_STD", "OP_5.3_12.3", "OSAB5.3_12.3"],
    assignable_template_codes: ["OPE0714_1E3SAB", "OPE0736_STD"],
    inherited_template_codes: ["OP_5.3_12.3", "OSAB5.3_12.3"],
    rule_summaries: ["Feriale 7h", "Agrario sabato 6h30", "Catasto/magazzino sabato 6h"],
    active: true,
  },
  {
    profile_code: "impiegati_gaia",
    profile_label: "Profilo Impiegati",
    description: "Profilo gestionale per impiegati con orari INAZ flessibili, rientri e controllo banca ore separato dalle regole rigide degli operai.",
    default_template_code: "IMP1_STD",
    template_codes: ["IMP1_STD", "IMP1_RIENTRO"],
    assignable_template_codes: ["IMP1_STD", "IMP1_RIENTRO"],
    inherited_template_codes: [],
    rule_summaries: ["Flessibile IMP1", "Rientro lunedi pomeriggio", "Controllo banca ore / anomalie"],
    active: true,
  },
];

function weekdayLabel(value: number | null): string {
  const labels = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"];
  if (value == null) return "Tutti i giorni";
  return labels[value] ?? `Giorno ${value}`;
}

function recurrenceLabel(rule: PresenzeScheduleBootstrapRulePreview): string {
  if (rule.recurrence_kind === "first_weekday_of_month") {
    return `1° ${weekdayLabel(rule.weekday)}`;
  }
  if (rule.recurrence_kind === "nth_weekday_of_month") {
    return `${rule.week_of_month ?? "N°"} ${weekdayLabel(rule.weekday)}`;
  }
  if (rule.recurrence_kind === "alternating_weeks") {
    return `${weekdayLabel(rule.weekday)} alternato`;
  }
  return weekdayLabel(rule.weekday);
}

function compactRuleRecurrenceLabel(rules: ScheduleDisplayRule[]): string {
  const firstRule = rules[0];
  if (!firstRule) return "";
  if (rules.every((rule) => rule.recurrence_kind === "weekly" && rule.weekday != null)) {
    const weekdays = rules.map((rule) => rule.weekday as number).sort((a, b) => a - b);
    const firstWeekday = weekdays[0];
    const lastWeekday = weekdays[weekdays.length - 1];
    const isConsecutive = weekdays.every((weekday, index) => weekday === firstWeekday + index);
    if (isConsecutive && weekdays.length > 1) return `${weekdayLabel(firstWeekday)}-${weekdayLabel(lastWeekday)}`;
    return weekdays.map((weekday) => weekdayLabel(weekday)).join(", ");
  }
  if (
    rules.every(
      (rule) =>
        ["first_weekday_of_month", "nth_weekday_of_month"].includes(rule.recurrence_kind) &&
        rule.weekday === firstRule.weekday,
    )
  ) {
    const ordinals = rules
      .map((rule) => (rule.recurrence_kind === "first_weekday_of_month" ? 1 : rule.week_of_month))
      .filter((value): value is number => value != null)
      .sort((a, b) => a - b)
      .map((value) => `${value}°`)
      .join(" e ");
    return `${ordinals} ${weekdayLabel(firstRule.weekday)}`;
  }
  return recurrenceLabel(firstRule as PresenzeScheduleBootstrapRulePreview);
}

function formatClock(value: string): string {
  return value.slice(0, 5);
}

function formatCalendarDay(month: number, day: number): string {
  return `${String(day).padStart(2, "0")}/${String(month).padStart(2, "0")}`;
}

function seasonLabel(rule: ScheduleDisplayRule): string | null {
  const { season_start_month, season_start_day, season_end_month, season_end_day } = rule;
  if (season_start_month == null || season_start_day == null || season_end_month == null || season_end_day == null) {
    return null;
  }
  return `Periodo ${formatCalendarDay(season_start_month, season_start_day)}-${formatCalendarDay(season_end_month, season_end_day)}`;
}

function compactRuleGroups(rules: ScheduleDisplayRule[]): ScheduleDisplayRule[][] {
  const grouped = new Map<string, ScheduleDisplayRule[]>();
  for (const rule of rules) {
    const recurrenceBucket = rule.recurrence_kind === "weekly" ? "weekly" : `${rule.recurrence_kind}:${rule.weekday}`;
    const key = [
      recurrenceBucket,
      rule.start_time,
      rule.end_time,
      rule.season_start_month ?? "",
      rule.season_start_day ?? "",
      rule.season_end_month ?? "",
      rule.season_end_day ?? "",
      rule.applies_on_holiday,
      rule.ordinary_label ?? "",
    ].join("|");
    grouped.set(key, [...(grouped.get(key) ?? []), rule]);
  }
  return [...grouped.values()].map((items) => [...items].sort((a, b) => (a.weekday ?? 99) - (b.weekday ?? 99) || (a.week_of_month ?? 0) - (b.week_of_month ?? 0)));
}

function compactRuleLabel(rules: ScheduleDisplayRule[]): string {
  const firstRule = rules[0];
  if (!firstRule) return "";
  return `${compactRuleRecurrenceLabel(rules)} ${formatClock(firstRule.start_time)}-${formatClock(firstRule.end_time)}`;
}

function compactRuleDetail(rules: ScheduleDisplayRule[]): string {
  const firstRule = rules[0];
  if (!firstRule) return "";
  return [
    compactRuleRecurrenceLabel(rules),
    `${formatClock(firstRule.start_time)} - ${formatClock(firstRule.end_time)}`,
    seasonLabel(firstRule),
    firstRule.ordinary_label ? `Codice ${firstRule.ordinary_label}` : null,
  ]
    .filter(Boolean)
    .join(" · ");
}

function describePreset(code: string, label: string): string {
  const normalized = code.trim().toUpperCase();
  if (normalized === "OPE0714_1E3SAB") return "Operai 7:00-14:00, con fascia estiva 5:30-12:30 dal 01/06 al 30/09 e 1°/3° sabato dedicati.";
  if (normalized === "IMP1_STD") return "Impiegati con orario continuato 7:35-14:00 dal lunedi al venerdi.";
  if (normalized === "IMP1_RIENTRO") return "Impiegati 7:35-14:00 con rientro pomeridiano il lunedi 14:30-17:45.";
  if (normalized === "OPE0736_STD") return "Operai 6:20-13:56 dal lunedi al venerdi.";
  return label;
}

function collaboratorWorkflowText(suggestion: PresenzeScheduleBootstrapCollaboratorSuggestion): string {
  if (suggestion.already_assigned) {
    if ((suggestion.configuration_status ?? "unassigned") === "legacy_review") return "Da impostare";
    if ((suggestion.configuration_status ?? "unassigned") === "current") return "Allineato GAIA";
    return "Configurato";
  }
  if (suggestion.suggested_template_code && suggestion.suggestion_confidence === "high") return "Pronto";
  if (suggestion.suggested_template_code) return "Da confermare";
  return "Da verificare";
}

function collaboratorWorkflowClass(suggestion: PresenzeScheduleBootstrapCollaboratorSuggestion): string {
  if (suggestion.already_assigned) {
    if ((suggestion.configuration_status ?? "unassigned") === "legacy_review") return "bg-amber-50 text-amber-800 ring-1 ring-amber-200";
    if ((suggestion.configuration_status ?? "unassigned") === "current") return "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200";
    return "bg-gray-100 text-gray-700";
  }
  if (suggestion.suggested_template_code && suggestion.suggestion_confidence === "high") return "bg-sky-50 text-sky-800 ring-1 ring-sky-200";
  if (suggestion.suggested_template_code) return "bg-amber-50 text-amber-800 ring-1 ring-amber-200";
  return "bg-gray-100 text-gray-700";
}

function displayedAssignedTemplateCode(suggestion: PresenzeScheduleBootstrapCollaboratorSuggestion): string | null {
  return suggestion.assigned_template_code ?? (suggestion.already_assigned ? suggestion.suggested_template_code : null);
}

function profileFromTemplateCode(code: string | null | undefined): CollaboratorProfileFilter | null {
  const normalized = code?.trim().toUpperCase();
  if (!normalized) return null;
  if (OPERAI_PROFILE_TEMPLATE_CODES.has(normalized)) return "operai_gaia";
  if (IMPIEGATI_PROFILE_TEMPLATE_CODES.has(normalized)) return "impiegati_gaia";
  return null;
}

function resolveCollaboratorProfile(
  suggestion: PresenzeScheduleBootstrapCollaboratorSuggestion,
  collaborator: PresenzeCollaborator | undefined,
): CollaboratorProfileFilter {
  if (collaborator?.contract_kind === "operaio") return "operai_gaia";
  if (collaborator?.contract_kind === "impiegato") return "impiegati_gaia";
  return profileFromTemplateCode(displayedAssignedTemplateCode(suggestion)) ?? profileFromTemplateCode(suggestion.suggested_template_code) ?? "unassigned";
}

function collaboratorProfileLabel(profile: CollaboratorProfileFilter): string {
  if (profile === "operai_gaia") return "Operai GAIA";
  if (profile === "impiegati_gaia") return "Impiegati GAIA";
  if (profile === "unassigned") return "Non impostato";
  return "Tutti";
}

function collaboratorSurnameSortKey(name: string): string {
  return name.trim().split(/\s+/)[0]?.toLocaleLowerCase("it-IT") ?? "";
}

function confidenceLabel(confidence: PresenzeScheduleBootstrapCollaboratorSuggestion["suggestion_confidence"]): string {
  if (confidence === "high") return "Alta";
  if (confidence === "medium") return "Media";
  if (confidence === "low") return "Bassa";
  return "Assente";
}

function formatOperaiGroup(value: PresenzeCollaborator["operai_group"] | null | undefined): string {
  if (value === "agrario") return "Agrario";
  if (value === "catasto_magazzino") return "Catasto / magazzino";
  return "Non impostato";
}

function operaiGroupBadgeVariant(value: PresenzeCollaborator["operai_group"] | null | undefined): "success" | "info" | "neutral" {
  if (value === "agrario") return "success";
  if (value === "catasto_magazzino") return "info";
  return "neutral";
}

export default function PresenzeConfigurazionePage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [profileFilter, setProfileFilter] = useState<CollaboratorProfileFilter>("all");
  const [templates, setTemplates] = useState<PresenzeScheduleTemplate[]>([]);
  const [collaborators, setCollaborators] = useState<PresenzeCollaborator[]>([]);
  const [bootstrapPreview, setBootstrapPreview] = useState<PresenzeScheduleBootstrapPreviewResponse | null>(null);
  const [bankHoursGuidanceConfig, setBankHoursGuidanceConfig] = useState<PresenzeBankHoursGuidanceConfig | null>(null);
  const [bankHoursGuidanceHistory, setBankHoursGuidanceHistory] = useState<PresenzeBankHoursGuidanceConfigRevision[]>([]);
  const [templateCode, setTemplateCode] = useState("");
  const [templateLabel, setTemplateLabel] = useState("");
  const [templateCompanyCode, setTemplateCompanyCode] = useState("53");
  const [ruleTemplateId, setRuleTemplateId] = useState("");
  const [ruleLabel, setRuleLabel] = useState("");
  const [ruleWeekday, setRuleWeekday] = useState("");
  const [ruleRecurrence, setRuleRecurrence] = useState("weekly");
  const [ruleWeekOfMonth, setRuleWeekOfMonth] = useState("");
  const [ruleIntervalWeeks, setRuleIntervalWeeks] = useState("");
  const [ruleAnchorDate, setRuleAnchorDate] = useState("");
  const [ruleStartTime, setRuleStartTime] = useState("07:00");
  const [ruleEndTime, setRuleEndTime] = useState("14:00");
  const [ruleSeasonStartMonth, setRuleSeasonStartMonth] = useState("");
  const [ruleSeasonStartDay, setRuleSeasonStartDay] = useState("");
  const [ruleSeasonEndMonth, setRuleSeasonEndMonth] = useState("");
  const [ruleSeasonEndDay, setRuleSeasonEndDay] = useState("");
  const [ruleHoliday, setRuleHoliday] = useState(false);
  const [ruleOrdinaryLabel, setRuleOrdinaryLabel] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isApplyingBootstrap, setIsApplyingBootstrap] = useState(false);
  const [isSavingGuidanceConfig, setIsSavingGuidanceConfig] = useState(false);
  const [assigningCollaboratorId, setAssigningCollaboratorId] = useState<string | null>(null);
  const [bootstrapModalMode, setBootstrapModalMode] = useState<"confirm" | "result" | null>(null);
  const [bootstrapResult, setBootstrapResult] = useState<PresenzeScheduleBootstrapApplyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const token = getStoredAccessToken();
    if (!token) return;
    setIsLoading(true);
    try {
      const [templateItems, collaboratorItems, preview, guidanceConfig, guidanceHistory] = await Promise.all([
        listPresenzeScheduleTemplates(token),
        listAllPresenzeCollaborators(token),
        getPresenzeScheduleBootstrapPreview(token),
        getPresenzeBankHoursGuidanceConfig(token),
        listPresenzeBankHoursGuidanceConfigHistory(token),
      ]);
      setTemplates(templateItems);
      setCollaborators(collaboratorItems);
      setBootstrapPreview(preview);
      setBankHoursGuidanceConfig(guidanceConfig);
      setBankHoursGuidanceHistory(guidanceHistory);
      setRuleTemplateId((current) => current || (templateItems[0] ? String(templateItems[0].id) : ""));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh().catch((loadError) => {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento configurazione giornaliere");
      setIsLoading(false);
    });
  }, [refresh]);

  const templateByCode = useMemo(() => {
    const entries = templates.map((template) => [template.code.trim().toUpperCase(), template] as const);
    return new Map(entries);
  }, [templates]);

  const collaboratorsById = useMemo(() => new Map(collaborators.map((item) => [item.id, item])), [collaborators]);

  const pendingSuggestions = useMemo(
    () =>
      (bootstrapPreview?.collaborator_suggestions ?? []).filter(
        (item) => !item.already_assigned && item.suggested_template_code && item.suggestion_confidence === "high",
      ),
    [bootstrapPreview],
  );

  const suggestionsWithoutPreset = useMemo(
    () =>
      (bootstrapPreview?.collaborator_suggestions ?? []).filter(
        (item) => !item.already_assigned && (!item.suggested_template_code || item.suggestion_confidence === "none"),
      ),
    [bootstrapPreview],
  );

  const probableSuggestions = useMemo(
    () =>
      (bootstrapPreview?.collaborator_suggestions ?? []).filter(
        (item) => !item.already_assigned && item.suggested_template_code && ["medium", "low"].includes(item.suggestion_confidence),
      ),
    [bootstrapPreview],
  );

  const alreadyConfiguredSuggestions = useMemo(
    () => (bootstrapPreview?.collaborator_suggestions ?? []).filter((item) => item.already_assigned),
    [bootstrapPreview],
  );

  const alignedConfiguredSuggestions = useMemo(
    () => alreadyConfiguredSuggestions.filter((item) => item.configuration_status === "current"),
    [alreadyConfiguredSuggestions],
  );

  const legacyConfiguredSuggestions = useMemo(
    () => alreadyConfiguredSuggestions.filter((item) => item.configuration_status === "legacy_review"),
    [alreadyConfiguredSuggestions],
  );

  const detectedPresets = bootstrapPreview?.presets ?? [];
  const gaiaScheduleProfiles = bootstrapPreview?.profiles?.length ? bootstrapPreview.profiles : DEFAULT_GAIA_SCHEDULE_PROFILES;

  const normalizedSearchTerm = searchTerm.trim().toLowerCase();

  const collaboratorSuggestions = bootstrapPreview?.collaborator_suggestions ?? [];
  const collaboratorProfileCounts = useMemo(() => {
    const counts: Record<CollaboratorProfileFilter, number> = {
      all: collaboratorSuggestions.length,
      operai_gaia: 0,
      impiegati_gaia: 0,
      unassigned: 0,
    };
    for (const suggestion of collaboratorSuggestions) {
      counts[resolveCollaboratorProfile(suggestion, collaboratorsById.get(suggestion.collaborator_id))] += 1;
    }
    return counts;
  }, [collaboratorSuggestions, collaboratorsById]);

  const filteredCollaboratorSuggestions = useMemo(
    () =>
      collaboratorSuggestions
        .filter((suggestion) => {
          if (profileFilter !== "all" && resolveCollaboratorProfile(suggestion, collaboratorsById.get(suggestion.collaborator_id)) !== profileFilter) return false;
          if (!normalizedSearchTerm) return true;
          const haystack = [
            suggestion.employee_code,
            suggestion.collaborator_name,
            suggestion.dominant_schedule_code ?? "",
            suggestion.schedule_codes.join(" "),
            suggestion.suggested_template_code ?? "",
            suggestion.suggested_template_label ?? "",
            displayedAssignedTemplateCode(suggestion) ?? "",
          ]
            .join(" ")
            .toLowerCase();
          return haystack.includes(normalizedSearchTerm);
        })
        .sort((left, right) => {
          const surnameCompare = collaboratorSurnameSortKey(left.collaborator_name).localeCompare(collaboratorSurnameSortKey(right.collaborator_name), "it-IT");
          if (surnameCompare !== 0) return surnameCompare;
          return left.collaborator_name.localeCompare(right.collaborator_name, "it-IT") || left.employee_code.localeCompare(right.employee_code, "it-IT");
        }),
    [collaboratorSuggestions, collaboratorsById, normalizedSearchTerm, profileFilter],
  );

  async function handleBootstrapApply() {
    const token = getStoredAccessToken();
    if (!token) return;
    setError(null);
    setSuccess(null);
    setIsApplyingBootstrap(true);
    try {
      const result = await applyPresenzeScheduleBootstrap(token, {
        create_missing_templates: true,
        assign_unassigned_collaborators: true,
      });
      setBootstrapResult(result);
      setBootstrapModalMode("result");
      setSuccess(
        `Configurazione base completata: ${result.created_templates} template creati, ${result.created_assignments} assegnazioni applicate.`,
      );
      await refresh();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Errore durante il bootstrap della configurazione");
    } finally {
      setIsApplyingBootstrap(false);
    }
  }

  async function handleAssignSuggestion(suggestion: PresenzeScheduleBootstrapCollaboratorSuggestion) {
    const token = getStoredAccessToken();
    if (!token || !suggestion.suggested_template_code) return;
    const template = templateByCode.get(suggestion.suggested_template_code.trim().toUpperCase());
    if (!template) {
      setError(`Il template ${suggestion.suggested_template_code} non esiste ancora. Usa prima "Configura automaticamente".`);
      return;
    }
    setAssigningCollaboratorId(suggestion.collaborator_id);
    setError(null);
    setSuccess(null);
    try {
      await createPresenzeCollaboratorScheduleAssignment(token, suggestion.collaborator_id, {
        template_id: template.id,
        notes: `Assegnazione guidata da schedule code giornaliere: ${suggestion.schedule_codes.join(", ")}`,
      });
      setSuccess(`Template ${template.code} assegnato a ${suggestion.collaborator_name}.`);
      await refresh();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Errore assegnazione template");
    } finally {
      setAssigningCollaboratorId(null);
    }
  }

  async function handleSaveBankHoursGuidanceConfig() {
    const token = getStoredAccessToken();
    if (!token || !bankHoursGuidanceConfig) return;
    setIsSavingGuidanceConfig(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updatePresenzeBankHoursGuidanceConfig(token, {
        allow_derived_profile: bankHoursGuidanceConfig.allow_derived_profile,
        include_overtime_day: bankHoursGuidanceConfig.include_overtime_day,
        include_overtime_night: bankHoursGuidanceConfig.include_overtime_night,
        include_overtime_festive: bankHoursGuidanceConfig.include_overtime_festive,
        include_overtime_festive_night: bankHoursGuidanceConfig.include_overtime_festive_night,
        min_suggested_minutes: bankHoursGuidanceConfig.min_suggested_minutes,
      });
      setBankHoursGuidanceConfig(updated);
      setBankHoursGuidanceHistory(await listPresenzeBankHoursGuidanceConfigHistory(token));
      setSuccess("Policy banca ore aggiornata.");
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Errore salvataggio policy banca ore");
    } finally {
      setIsSavingGuidanceConfig(false);
    }
  }

  return (
    <ProtectedPage
      title="Configurazione giornaliere"
      description="Impostazione guidata di orari, festivita e regole con suggerimenti automatici dai dati giornaliere gia importati."
      breadcrumb="Giornaliere"
      requiredModule="presenze"
      requiredRoles={["admin", "super_admin"]}
    >
      <div className="space-y-6">
        {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
        {success ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div> : null}

        <details className="panel-card group">
          <summary className="cursor-pointer list-none">
            <div className="flex items-center justify-between gap-3">
              <div className="space-y-1">
                <h2 className="text-lg font-semibold text-gray-900">Policy banca ore</h2>
                <p className="max-w-3xl text-sm text-gray-600">
                  Regole operative della liquidazione guidata: tienile qui solo per interventi amministrativi avanzati.
                </p>
              </div>
              <span className="text-sm text-gray-500 group-open:hidden">Apri</span>
              <span className="hidden text-sm text-gray-500 group-open:inline">Chiudi</span>
            </div>
          </summary>
          {bankHoursGuidanceConfig ? (
            <div className="mt-5 space-y-4">
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                <label className="flex items-start gap-3 rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-sm text-gray-700">
                  <input
                    checked={bankHoursGuidanceConfig.allow_derived_profile}
                    className="mt-1"
                    onChange={(event) =>
                      setBankHoursGuidanceConfig((current) => (current ? { ...current, allow_derived_profile: event.target.checked } : current))
                    }
                    type="checkbox"
                  />
                  <span>
                    <span className="block font-medium text-gray-900">Consenti profilo derivato</span>
                    <span className="block text-xs text-gray-500">Se disattivo, i profili dedotti dal template finiscono in revisione HR.</span>
                  </span>
                </label>
                <label className="flex items-start gap-3 rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-sm text-gray-700">
                  <input
                    checked={bankHoursGuidanceConfig.include_overtime_day}
                    className="mt-1"
                    onChange={(event) =>
                      setBankHoursGuidanceConfig((current) => (current ? { ...current, include_overtime_day: event.target.checked } : current))
                    }
                    type="checkbox"
                  />
                  <span>
                    <span className="block font-medium text-gray-900">Straordinario diurno</span>
                    <span className="block text-xs text-gray-500">Include la quota feriale diurna tra i minuti candidabili.</span>
                  </span>
                </label>
                <label className="flex items-start gap-3 rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-sm text-gray-700">
                  <input
                    checked={bankHoursGuidanceConfig.include_overtime_night}
                    className="mt-1"
                    onChange={(event) =>
                      setBankHoursGuidanceConfig((current) => (current ? { ...current, include_overtime_night: event.target.checked } : current))
                    }
                    type="checkbox"
                  />
                  <span>
                    <span className="block font-medium text-gray-900">Straordinario notturno</span>
                    <span className="block text-xs text-gray-500">Include la quota svolta in fascia 22:00-06:00.</span>
                  </span>
                </label>
                <label className="flex items-start gap-3 rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-sm text-gray-700">
                  <input
                    checked={bankHoursGuidanceConfig.include_overtime_festive}
                    className="mt-1"
                    onChange={(event) =>
                      setBankHoursGuidanceConfig((current) => (current ? { ...current, include_overtime_festive: event.target.checked } : current))
                    }
                    type="checkbox"
                  />
                  <span>
                    <span className="block font-medium text-gray-900">Straordinario festivo</span>
                    <span className="block text-xs text-gray-500">Include la quota svolta su festivita o domeniche.</span>
                  </span>
                </label>
                <label className="flex items-start gap-3 rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-sm text-gray-700">
                  <input
                    checked={bankHoursGuidanceConfig.include_overtime_festive_night}
                    className="mt-1"
                    onChange={(event) =>
                      setBankHoursGuidanceConfig((current) => (current ? { ...current, include_overtime_festive_night: event.target.checked } : current))
                    }
                    type="checkbox"
                  />
                  <span>
                    <span className="block font-medium text-gray-900">Straordinario festivo notturno</span>
                    <span className="block text-xs text-gray-500">Controlla la quota piu sensibile del breakdown CCNL.</span>
                  </span>
                </label>
                <label className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-sm font-medium text-gray-700">
                  Soglia minima proposta
                  <input
                    className="form-control mt-2"
                    min={0}
                    onChange={(event) =>
                      setBankHoursGuidanceConfig((current) =>
                        current ? { ...current, min_suggested_minutes: Number(event.target.value || 0) } : current,
                      )
                    }
                    type="number"
                    value={bankHoursGuidanceConfig.min_suggested_minutes}
                  />
                  <span className="mt-2 block text-xs text-gray-500">Se la proposta resta sotto questa soglia, GAIA la sposta in revisione HR.</span>
                </label>
              </div>
              <div className="rounded-2xl border border-sky-100 bg-sky-50 px-4 py-3 text-sm text-sky-900">
                La policy viene applicata al dettaglio `/presenze/banca-ore` e al pulsante `Proponi liquidazione`. Le modifiche non alterano i dati storici
                gia salvati, ma solo le proposte future.
              </div>
              <div className="rounded-2xl border border-gray-100 bg-white px-4 py-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-gray-900">Storico modifiche</p>
                    <p className="mt-1 text-xs text-gray-500">Audit minimale della policy usata dalla liquidazione guidata.</p>
                  </div>
                  <div className="text-right text-xs text-gray-500">
                    <p>Ultimo aggiornamento</p>
                    <p className="mt-1 font-medium text-gray-700">
                      {bankHoursGuidanceConfig.updated_at
                        ? `${new Date(bankHoursGuidanceConfig.updated_at).toLocaleString("it-IT")} · ${bankHoursGuidanceConfig.updated_by_label ?? "Utente sconosciuto"}`
                        : "Nessuna modifica registrata"}
                    </p>
                  </div>
                </div>
                <div className="mt-4 space-y-3">
                  {bankHoursGuidanceHistory.length ? (
                    bankHoursGuidanceHistory.map((revision) => (
                      <article key={revision.id} className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div>
                            <p className="text-sm font-medium text-gray-900">
                              {revision.changed_by_label ?? "Utente sconosciuto"} · {new Date(revision.changed_at).toLocaleString("it-IT")}
                            </p>
                            <p className="mt-1 text-xs text-gray-500">
                              Profilo derivato {revision.allow_derived_profile ? "abilitato" : "disabilitato"} · soglia {revision.min_suggested_minutes} min
                            </p>
                          </div>
                          <div className="flex flex-wrap gap-2 text-xs text-gray-600">
                            <span className={revision.include_overtime_day ? "rounded-full bg-emerald-100 px-2 py-1 text-emerald-800" : "rounded-full bg-gray-200 px-2 py-1"}>Diurno</span>
                            <span className={revision.include_overtime_night ? "rounded-full bg-emerald-100 px-2 py-1 text-emerald-800" : "rounded-full bg-gray-200 px-2 py-1"}>Notturno</span>
                            <span className={revision.include_overtime_festive ? "rounded-full bg-emerald-100 px-2 py-1 text-emerald-800" : "rounded-full bg-gray-200 px-2 py-1"}>Festivo</span>
                            <span className={revision.include_overtime_festive_night ? "rounded-full bg-emerald-100 px-2 py-1 text-emerald-800" : "rounded-full bg-gray-200 px-2 py-1"}>Festivo notturno</span>
                          </div>
                        </div>
                      </article>
                    ))
                  ) : (
                    <p className="text-sm text-gray-500">Nessuna revisione storica disponibile.</p>
                  )}
                </div>
              </div>
              <div className="flex flex-wrap gap-3">
                <button className="btn-primary" disabled={isSavingGuidanceConfig} onClick={() => void handleSaveBankHoursGuidanceConfig()} type="button">
                  {isSavingGuidanceConfig ? "Salvataggio..." : "Salva policy banca ore"}
                </button>
              </div>
            </div>
          ) : (
            <p className="mt-5 text-sm text-gray-500">Caricamento policy banca ore...</p>
          )}
        </details>

        <section className="panel-card space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-1">
              <h2 className="text-lg font-semibold text-gray-900">Avvio rapido</h2>
              <p className="max-w-3xl text-sm text-gray-600">
                Apre il riepilogo prima di creare i template mancanti e assegnare solo i collaboratori senza configurazione con proposta alta.
              </p>
            </div>
            <button
              className="btn-primary"
              disabled={isApplyingBootstrap || isLoading}
              onClick={() => {
                setBootstrapResult(null);
                setBootstrapModalMode("confirm");
              }}
              type="button"
            >
              {isApplyingBootstrap ? "Configurazione in corso..." : "Rivedi configurazione automatica"}
            </button>
          </div>

          <div className="grid gap-3 md:grid-cols-4">
            <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-4">
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Collaboratori rilevati</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{bootstrapPreview?.detected_collaborators_total ?? "—"}</p>
            </div>
            <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-4">
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Template suggeriti</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{detectedPresets.length}</p>
            </div>
            <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-4">
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Suggerimenti trovati</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{bootstrapPreview?.collaborators_with_suggestion_total ?? "—"}</p>
            </div>
            <div className="rounded-2xl border border-sky-100 bg-sky-50 px-4 py-4">
              <p className="text-xs font-medium uppercase tracking-wide text-sky-700">Assegnabili subito</p>
              <p className="mt-2 text-2xl font-semibold text-sky-950">{pendingSuggestions.length}</p>
            </div>
            <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-4">
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Senza assegnazione</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{bootstrapPreview?.collaborators_without_assignment_total ?? "—"}</p>
            </div>
            <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-4">
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Già assegnati</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{alreadyConfiguredSuggestions.length}</p>
            </div>
            <div className="rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-4">
              <p className="text-xs font-medium uppercase tracking-wide text-emerald-700">Allineati GAIA</p>
              <p className="mt-2 text-2xl font-semibold text-emerald-950">{alignedConfiguredSuggestions.length}</p>
            </div>
            <div className="rounded-2xl border border-amber-100 bg-amber-50 px-4 py-4">
              <p className="text-xs font-medium uppercase tracking-wide text-amber-700">Legacy</p>
              <p className="mt-2 text-2xl font-semibold text-amber-950">{legacyConfiguredSuggestions.length}</p>
            </div>
          </div>
        </section>

        <section className="panel-card space-y-4">
          <div className="space-y-1">
            <h2 className="text-lg font-semibold text-gray-900">Template presenti nel sistema</h2>
            <p className="text-sm text-gray-600">
              GAIA distingue i profili operativi che governano controlli e regole dai template orari ereditati dai codici INAZ.
            </p>
          </div>

          <div className="space-y-4">
            <div className="space-y-3">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                  <h3 className="text-base font-semibold text-gray-900">Template GAIA</h3>
                  <p className="text-sm text-gray-600">Profili applicativi che fissano il comportamento di controllo, non singoli codici turno.</p>
                </div>
                <span className="rounded-full bg-slate-900 px-3 py-1 text-xs font-medium text-white">Gestiti da GAIA</span>
              </div>
              <div className="grid gap-4 xl:grid-cols-2">
                {gaiaScheduleProfiles.map((profile) => {
                  const defaultTemplateCode = profile.default_template_code ?? null;
                  const assignableTemplateCodes = profile.assignable_template_codes ?? [];
                  const inheritedTemplateCodes = profile.inherited_template_codes ?? [];
                  const isOperaiProfile = profile.profile_code === "operai_gaia";
                  const palette = isOperaiProfile
                    ? {
                        card: "rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-4",
                        title: "font-semibold text-emerald-950",
                        text: "mt-1 text-sm text-emerald-900",
                        badge: "rounded-full bg-white px-3 py-1 text-xs font-medium text-emerald-700 ring-1 ring-emerald-200",
                        chip: "rounded-xl bg-white px-3 py-2 text-sm text-emerald-900 ring-1 ring-emerald-100",
                      }
                    : {
                        card: "rounded-2xl border border-sky-100 bg-sky-50 px-4 py-4",
                        title: "font-semibold text-sky-950",
                        text: "mt-1 text-sm text-sky-900",
                        badge: "rounded-full bg-white px-3 py-1 text-xs font-medium text-sky-700 ring-1 ring-sky-200",
                        chip: "rounded-xl bg-white px-3 py-2 text-sm text-sky-900 ring-1 ring-sky-100",
                      };
                  return (
                    <article key={profile.profile_code} className={palette.card}>
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className={palette.title}>
                            {profile.profile_code} · {profile.profile_label}
                          </p>
                          <p className={palette.text}>{profile.description}</p>
                        </div>
                        <span className={palette.badge}>{profile.active ? "Attivo" : "In attesa template"}</span>
                      </div>
                      <div className="mt-4 grid gap-2 md:grid-cols-3">
                        {profile.rule_summaries.map((summary) => (
                          <div key={summary} className={palette.chip}>
                            {summary}
                          </div>
                        ))}
                      </div>
                      <div className="mt-3 space-y-2 rounded-xl bg-white/80 px-3 py-3 text-xs text-gray-700 ring-1 ring-white">
                        <p>
                          <span className="font-medium">Template predefinito:</span>{" "}
                          {defaultTemplateCode ?? "n/d"}
                        </p>
                        <p>
                          <span className="font-medium">Template assegnabili:</span>{" "}
                          {assignableTemplateCodes.length
                            ? assignableTemplateCodes.join(", ")
                            : profile.template_codes.join(", ")}
                        </p>
                        <p>
                          <span className="font-medium">Template ereditati da INAZ:</span>{" "}
                          {inheritedTemplateCodes.length
                            ? inheritedTemplateCodes.join(", ")
                            : "nessuno"}
                        </p>
                      </div>
                    </article>
                  );
                })}
              </div>
            </div>

            <details className="group rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
              <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="text-base font-semibold text-gray-900">Template ereditati da INAZ</h3>
                  <p className="text-sm text-gray-600">Orari concreti e codici turno letti dalle giornaliere, visibili solo quando servono dettagli tecnici.</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-white px-3 py-1 text-xs font-medium text-gray-700 ring-1 ring-gray-200">{templates.length} disponibili</span>
                  <span className="text-sm text-gray-500 group-open:hidden">Apri</span>
                  <span className="hidden text-sm text-gray-500 group-open:inline">Chiudi</span>
                </div>
              </summary>
              <div className="mt-4 space-y-3">
                {templates.map((template) => (
                  <details key={template.id} className="group/template rounded-xl border border-white bg-white px-3 py-3">
                    <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-medium text-gray-900">
                          {template.code} · {template.label}
                        </p>
                        <p className="mt-1 text-xs text-gray-500">
                          {template.company_code ?? "Globale"}
                          {template.notes ? ` · ${template.notes}` : ""}
                        </p>
                      </div>
                      <span className="text-sm text-gray-500 group-open/template:hidden">Dettagli</span>
                      <span className="hidden text-sm text-gray-500 group-open/template:inline">Nascondi</span>
                    </summary>
                    {template.rules.length > 0 ? (
                      <div className="mt-3 space-y-2">
                        {compactRuleGroups(template.rules).map((rules, index) => (
                          <div key={`${template.id}-${index}`} className="rounded-xl border border-gray-100 bg-gray-50 px-3 py-2 text-sm text-gray-700">
                            <span className="font-medium">{compactRuleLabel(rules)}</span>
                            <span className="text-gray-500"> · {compactRuleDetail(rules)}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="mt-3 rounded-xl border border-dashed border-amber-200 bg-amber-50 px-3 py-3 text-sm text-amber-900">
                        Template senza regole orarie fisse: il comportamento operativo viene completato da configurazioni applicative dedicate.
                      </div>
                    )}
                  </details>
                ))}
                {templates.length === 0 ? <p className="text-sm text-gray-500">Nessun template INAZ salvato disponibile.</p> : null}
              </div>
            </details>
          </div>
        </section>

        <details className="panel-card group">
          <summary className="cursor-pointer list-none">
            <div className="flex items-center justify-between gap-3">
              <div className="space-y-1">
                <h2 className="text-lg font-semibold text-gray-900">Template suggeriti dai dati giornaliere</h2>
                <p className="text-sm text-gray-600">Profili derivati dai codici orario gia presenti nel database, utili per audit e bootstrap.</p>
              </div>
              <span className="text-sm text-gray-500 group-open:hidden">Apri</span>
              <span className="hidden text-sm text-gray-500 group-open:inline">Chiudi</span>
            </div>
          </summary>
          <div className="mt-5 grid gap-4 xl:grid-cols-2">
            {detectedPresets.map((preset) => (
              <article key={preset.preset_key} className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-gray-900">
                      {preset.template_code} · {preset.template_label}
                    </p>
                    <p className="mt-1 text-sm text-gray-700">{describePreset(preset.template_code, preset.template_label)}</p>
                    <p className="mt-1 text-sm text-gray-600">{preset.template_notes}</p>
                  </div>
                  <span
                    className={`rounded-full px-3 py-1 text-xs font-medium ${
                      preset.already_exists ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"
                    }`}
                  >
                    {preset.already_exists ? "Gia presente" : "Da creare"}
                  </span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-xs text-gray-600">
                  <span className="rounded-full bg-white px-3 py-1 ring-1 ring-gray-200">
                    codici: {preset.source_schedule_codes.join(", ")}
                  </span>
                  <span className="rounded-full bg-white px-3 py-1 ring-1 ring-gray-200">
                    record rilevati: {preset.detected_records_count}
                  </span>
                  <span className="rounded-full bg-white px-3 py-1 ring-1 ring-gray-200">
                    collaboratori: {preset.detected_collaborators_count}
                  </span>
                </div>
                <div className="mt-4 space-y-2">
                  {compactRuleGroups(preset.rules).map((rules, index) => (
                    <div key={`${preset.preset_key}-${index}`} className="rounded-xl border border-white bg-white px-3 py-2 text-sm text-gray-700">
                      <span className="font-medium">{compactRuleLabel(rules)}</span>
                      <span className="text-gray-500"> · {compactRuleDetail(rules)}</span>
                    </div>
                  ))}
                </div>
              </article>
            ))}
            {detectedPresets.length === 0 ? <p className="text-sm text-gray-500">Nessun preset suggerito disponibile.</p> : null}
          </div>
        </details>

        <section className="panel-card space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <h2 className="text-lg font-semibold text-gray-900">Collaboratori</h2>
              <p className="text-sm text-gray-600">
                Vista unica ordinata per cognome: assegnazioni pronte, conferme, casi manuali e configurazioni legacy sono nello stesso elenco.
              </p>
            </div>
            <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
              {filteredCollaboratorSuggestions.length} visibili
            </span>
          </div>

          <div className="grid gap-3 lg:grid-cols-[minmax(260px,1fr)_auto] lg:items-end">
            <label className="block text-sm font-medium text-gray-700">
              Cerca collaboratore o codice orario
              <input
                className="form-control mt-1"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="Es. Sanna, 122, OPE0714, rientro"
              />
            </label>
            <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-sm text-gray-700">
              Vista ordinata per cognome.
              {profileFilter !== "all" ? ` Profilo: ${collaboratorProfileLabel(profileFilter)}.` : ""}
              {normalizedSearchTerm ? ` Ricerca: "${searchTerm}".` : ""}
            </div>
          </div>

          <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">Profilo</span>
              <button
                className={`rounded-full px-3 py-1.5 text-sm font-medium ${profileFilter === "all" ? "bg-gray-900 text-white" : "bg-white text-gray-700 ring-1 ring-gray-200"}`}
                onClick={() => setProfileFilter("all")}
                type="button"
              >
                {collaboratorProfileLabel("all")} <span className="text-xs opacity-70">{collaboratorProfileCounts.all}</span>
              </button>
              <button
                className={`rounded-full px-3 py-1.5 text-sm font-medium ${profileFilter === "operai_gaia" ? "bg-emerald-700 text-white" : "bg-white text-emerald-800 ring-1 ring-emerald-100"}`}
                onClick={() => setProfileFilter("operai_gaia")}
                type="button"
              >
                {collaboratorProfileLabel("operai_gaia")} <span className="text-xs opacity-70">{collaboratorProfileCounts.operai_gaia}</span>
              </button>
              <button
                className={`rounded-full px-3 py-1.5 text-sm font-medium ${profileFilter === "impiegati_gaia" ? "bg-sky-700 text-white" : "bg-white text-sky-800 ring-1 ring-sky-100"}`}
                onClick={() => setProfileFilter("impiegati_gaia")}
                type="button"
              >
                {collaboratorProfileLabel("impiegati_gaia")} <span className="text-xs opacity-70">{collaboratorProfileCounts.impiegati_gaia}</span>
              </button>
              {collaboratorProfileCounts.unassigned > 0 ? (
                <button
                  className={`rounded-full px-3 py-1.5 text-sm font-medium ${profileFilter === "unassigned" ? "bg-amber-600 text-white" : "bg-white text-amber-800 ring-1 ring-amber-100"}`}
                  onClick={() => setProfileFilter("unassigned")}
                  type="button"
                >
                  {collaboratorProfileLabel("unassigned")} <span className="text-xs opacity-70">{collaboratorProfileCounts.unassigned}</span>
                </button>
              ) : null}
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-4">
            <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
              <p className="text-xs uppercase tracking-wide text-gray-500">Da impostare</p>
              <p className="mt-1 text-2xl font-semibold text-gray-950">{pendingSuggestions.length + legacyConfiguredSuggestions.length}</p>
            </div>
            <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
              <p className="text-xs uppercase tracking-wide text-gray-500">Da confermare</p>
              <p className="mt-1 text-2xl font-semibold text-gray-950">{probableSuggestions.length}</p>
            </div>
            <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
              <p className="text-xs uppercase tracking-wide text-gray-500">Da verificare</p>
              <p className="mt-1 text-2xl font-semibold text-gray-950">{suggestionsWithoutPreset.length}</p>
            </div>
            <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
              <p className="text-xs uppercase tracking-wide text-gray-500">Allineati</p>
              <p className="mt-1 text-2xl font-semibold text-gray-950">{alignedConfiguredSuggestions.length}</p>
            </div>
          </div>

          <div className="grid gap-4 xl:grid-cols-2 2xl:grid-cols-3">
            {filteredCollaboratorSuggestions.slice(0, 40).map((suggestion) => {
              const configurationNotes = suggestion.configuration_notes ?? [];
              const assignedTemplateCode = displayedAssignedTemplateCode(suggestion);
              const collaborator = collaboratorsById.get(suggestion.collaborator_id);
              const resolvedProfile = resolveCollaboratorProfile(suggestion, collaborator);
              const canAssign = !suggestion.already_assigned && suggestion.suggested_template_code;
              const actionLabel = suggestion.suggestion_confidence === "high" ? "Assegna template" : "Conferma template";
              return (
                <article key={suggestion.collaborator_id} className="flex min-h-full flex-col justify-between gap-4 rounded-3xl border border-gray-100 bg-white px-5 py-5 shadow-sm">
                  <div className="min-w-0 space-y-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-base font-semibold text-gray-950">
                        {suggestion.employee_code} · {suggestion.collaborator_name}
                      </p>
                      <Badge variant={operaiGroupBadgeVariant(collaboratorsById.get(suggestion.collaborator_id)?.operai_group)}>
                        {formatOperaiGroup(collaboratorsById.get(suggestion.collaborator_id)?.operai_group)}
                      </Badge>
                      <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-700">
                        {collaboratorProfileLabel(resolvedProfile)}
                      </span>
                      <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${collaboratorWorkflowClass(suggestion)}`}>
                        {collaboratorWorkflowText(suggestion)}
                      </span>
                      {suggestion.suggested_template_code && suggestion.suggestion_confidence !== "high" ? (
                        <span className="rounded-full bg-gray-50 px-2.5 py-1 text-xs font-medium text-gray-600 ring-1 ring-gray-200">
                          Confidenza {confidenceLabel(suggestion.suggestion_confidence)}
                        </span>
                      ) : null}
                    </div>
                    <div className="rounded-2xl border border-gray-100 bg-gray-50 px-3 py-3 text-sm text-gray-700">
                      {suggestion.already_assigned ? (
                        <>
                          Template assegnato: <span className="font-medium">{assignedTemplateCode ?? "n/d"}</span>
                          {suggestion.assigned_template_code == null && assignedTemplateCode ? " · risolto da proposta corrente" : ""}
                          {suggestion.suggested_template_code && suggestion.assigned_template_code && suggestion.assigned_template_code !== suggestion.suggested_template_code
                            ? ` · suggerito ora: ${suggestion.suggested_template_code}`
                            : ""}
                        </>
                      ) : suggestion.suggested_template_code ? (
                        <>
                          Proposta: <span className="font-medium">{suggestion.suggested_template_label}</span> ({suggestion.suggested_template_code})
                        </>
                      ) : (
                        "Nessun template suggerito dai codici osservati."
                      )}
                    </div>
                    <p className="text-xs text-gray-500">
                      Codici osservati: {suggestion.schedule_codes.join(", ") || "nessuno"} · dominante: {suggestion.dominant_schedule_code ?? "n/d"}
                    </p>
                    {suggestion.suggestion_reason && !suggestion.already_assigned ? (
                      <p className="text-xs text-gray-600">{suggestion.suggestion_reason}</p>
                    ) : null}
                    {configurationNotes.length ? (
                      <ul className="space-y-1 text-xs text-gray-600">
                        {configurationNotes.map((note) => (
                          <li key={note}>• {note}</li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                  {canAssign ? (
                    <button
                      className="btn-secondary w-full justify-center"
                      disabled={assigningCollaboratorId === suggestion.collaborator_id}
                      onClick={() => void handleAssignSuggestion(suggestion)}
                      type="button"
                    >
                      {assigningCollaboratorId === suggestion.collaborator_id ? "Salvataggio..." : actionLabel}
                    </button>
                  ) : null}
                </article>
              );
            })}
            {filteredCollaboratorSuggestions.length === 0 ? (
              <div className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-4 text-sm text-gray-700">
                Nessun collaboratore trovato con i filtri correnti.
              </div>
            ) : null}
          </div>
        </section>

        <details className="panel-card group" open={detectedPresets.length === 0}>
          <summary className="cursor-pointer list-none">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Opzioni avanzate</h2>
                <p className="text-sm text-gray-600">Da usare solo se serve una configurazione manuale fine.</p>
              </div>
              <span className="text-sm text-gray-500 group-open:hidden">Apri</span>
              <span className="hidden text-sm text-gray-500 group-open:inline">Chiudi</span>
            </div>
          </summary>

          <div className="mt-6 space-y-6">
            <article className="space-y-4">
              <div className="rounded-3xl border border-sky-100 bg-sky-50/70 p-5">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                  <div>
                    <h3 className="text-base font-semibold text-slate-900">Festivita e festivita soppresse</h3>
                    <p className="mt-1 text-sm text-slate-600">
                      La configurazione del calendario festivo ora vive in una vista dedicata, separata da template orari e bootstrap collaboratori.
                    </p>
                  </div>
                  <Link
                    href="/presenze/festivita"
                    className="inline-flex items-center justify-center rounded-2xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800"
                  >
                    Apri pagina festivita
                  </Link>
                </div>
              </div>
            </article>

            <article className="space-y-4">
              <div className="grid gap-4 lg:grid-cols-3">
                <label className="block text-sm font-medium text-gray-700">
                  Codice template
                  <input className="form-control mt-1" value={templateCode} onChange={(event) => setTemplateCode(event.target.value)} />
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  Etichetta
                  <input className="form-control mt-1" value={templateLabel} onChange={(event) => setTemplateLabel(event.target.value)} />
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  Company code
                  <input className="form-control mt-1" value={templateCompanyCode} onChange={(event) => setTemplateCompanyCode(event.target.value)} />
                </label>
              </div>
              <button
                className="btn-primary"
                type="button"
                onClick={() =>
                  void (async () => {
                    const token = getStoredAccessToken();
                    if (!token) return;
                    setError(null);
                    setSuccess(null);
                    try {
                      await createPresenzeScheduleTemplate(token, {
                        code: templateCode,
                        label: templateLabel,
                        company_code: templateCompanyCode || null,
                        is_active: true,
                      });
                      setTemplateCode("");
                      setTemplateLabel("");
                      setTemplateCompanyCode("53");
                      setSuccess("Template orario creato.");
                      await refresh();
                    } catch (createError) {
                      setError(createError instanceof Error ? createError.message : "Errore creazione template");
                    }
                  })()
                }
              >
                Crea template
              </button>

              <div className="grid gap-4 lg:grid-cols-[1.2fr_repeat(2,140px)_repeat(4,120px)_auto]">
                <label className="block text-sm font-medium text-gray-700">
                  Template
                  <select className="form-control mt-1" value={ruleTemplateId} onChange={(event) => setRuleTemplateId(event.target.value)}>
                    <option value="">Seleziona template</option>
                    {templates.map((template) => (
                      <option key={template.id} value={template.id}>
                        {template.code} · {template.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  Dalle
                  <input className="form-control mt-1" type="time" value={ruleStartTime} onChange={(event) => setRuleStartTime(event.target.value)} />
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  Alle
                  <input className="form-control mt-1" type="time" value={ruleEndTime} onChange={(event) => setRuleEndTime(event.target.value)} />
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  Weekday
                  <input className="form-control mt-1" value={ruleWeekday} onChange={(event) => setRuleWeekday(event.target.value)} placeholder="0-6" />
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  Recurrence
                  <select className="form-control mt-1" value={ruleRecurrence} onChange={(event) => setRuleRecurrence(event.target.value)}>
                    <option value="weekly">weekly</option>
                    <option value="first_weekday_of_month">first_weekday_of_month</option>
                    <option value="nth_weekday_of_month">nth_weekday_of_month</option>
                    <option value="alternating_weeks">alternating_weeks</option>
                  </select>
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  Week of month
                  <input className="form-control mt-1" value={ruleWeekOfMonth} onChange={(event) => setRuleWeekOfMonth(event.target.value)} />
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  Interval weeks
                  <input className="form-control mt-1" value={ruleIntervalWeeks} onChange={(event) => setRuleIntervalWeeks(event.target.value)} />
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  Anchor
                  <input className="form-control mt-1" type="date" value={ruleAnchorDate} onChange={(event) => setRuleAnchorDate(event.target.value)} />
                </label>
              </div>
              <div className="grid gap-4 lg:grid-cols-4">
                <label className="block text-sm font-medium text-gray-700">
                  Label regola
                  <input className="form-control mt-1" value={ruleLabel} onChange={(event) => setRuleLabel(event.target.value)} />
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  Ordinary label
                  <input className="form-control mt-1" value={ruleOrdinaryLabel} onChange={(event) => setRuleOrdinaryLabel(event.target.value)} />
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  Season start (mese/giorno)
                  <div className="mt-1 flex gap-2">
                    <input className="form-control" value={ruleSeasonStartMonth} onChange={(event) => setRuleSeasonStartMonth(event.target.value)} placeholder="MM" />
                    <input className="form-control" value={ruleSeasonStartDay} onChange={(event) => setRuleSeasonStartDay(event.target.value)} placeholder="DD" />
                  </div>
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  Season end (mese/giorno)
                  <div className="mt-1 flex gap-2">
                    <input className="form-control" value={ruleSeasonEndMonth} onChange={(event) => setRuleSeasonEndMonth(event.target.value)} placeholder="MM" />
                    <input className="form-control" value={ruleSeasonEndDay} onChange={(event) => setRuleSeasonEndDay(event.target.value)} placeholder="DD" />
                  </div>
                </label>
              </div>
              <label className="inline-flex items-center gap-2 text-sm text-gray-700">
                <input checked={ruleHoliday} onChange={(event) => setRuleHoliday(event.target.checked)} type="checkbox" />
                Valida anche nei festivi
              </label>
              <button
                className="btn-primary"
                type="button"
                onClick={() =>
                  void (async () => {
                    const token = getStoredAccessToken();
                    if (!token || !ruleTemplateId) return;
                    setError(null);
                    setSuccess(null);
                    try {
                      await createPresenzeScheduleRule(token, Number(ruleTemplateId), {
                        label: ruleLabel || null,
                        weekday: ruleWeekday ? Number(ruleWeekday) : null,
                        recurrence_kind: ruleRecurrence,
                        week_of_month: ruleWeekOfMonth ? Number(ruleWeekOfMonth) : null,
                        interval_weeks: ruleIntervalWeeks ? Number(ruleIntervalWeeks) : null,
                        anchor_date: ruleAnchorDate || null,
                        start_time: ruleStartTime,
                        end_time: ruleEndTime,
                        season_start_month: ruleSeasonStartMonth ? Number(ruleSeasonStartMonth) : null,
                        season_start_day: ruleSeasonStartDay ? Number(ruleSeasonStartDay) : null,
                        season_end_month: ruleSeasonEndMonth ? Number(ruleSeasonEndMonth) : null,
                        season_end_day: ruleSeasonEndDay ? Number(ruleSeasonEndDay) : null,
                        applies_on_holiday: ruleHoliday,
                        ordinary_label: ruleOrdinaryLabel || null,
                      });
                      setSuccess("Regola oraria aggiunta.");
                      await refresh();
                    } catch (createError) {
                      setError(createError instanceof Error ? createError.message : "Errore creazione regola");
                    }
                  })()
                }
              >
                Aggiungi regola
              </button>

              <div className="space-y-4">
                {templates.map((template) => (
                  <div key={template.id} className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-medium text-gray-900">
                          {template.code} · {template.label}
                        </p>
                        <p className="text-xs text-gray-500">
                          {template.company_code ?? "Globale"}
                          {template.notes ? ` · ${template.notes}` : ""}
                        </p>
                      </div>
                      <button
                        className="btn-secondary"
                        type="button"
                        onClick={() =>
                          void (async () => {
                            const token = getStoredAccessToken();
                            if (!token) return;
                            setError(null);
                            try {
                              await deletePresenzeScheduleTemplate(token, template.id);
                              await refresh();
                            } catch (deleteError) {
                              setError(deleteError instanceof Error ? deleteError.message : "Errore eliminazione template");
                            }
                          })()
                        }
                      >
                        Elimina template
                      </button>
                    </div>
                    <div className="mt-3 space-y-2">
                      {template.rules.map((rule) => (
                        <div key={rule.id} className="flex items-center justify-between gap-3 rounded-xl border border-white bg-white px-3 py-2 text-sm text-gray-700">
                          <div>
                            {rule.label ?? rule.recurrence_kind} · {rule.start_time} / {rule.end_time}
                            {rule.weekday != null ? ` · weekday ${rule.weekday}` : ""}
                            {seasonLabel(rule) ? ` · ${seasonLabel(rule)}` : ""}
                          </div>
                          <button
                            className="btn-secondary"
                            type="button"
                            onClick={() =>
                              void (async () => {
                                const token = getStoredAccessToken();
                                if (!token) return;
                                setError(null);
                                try {
                                  await deletePresenzeScheduleRule(token, rule.id);
                                  await refresh();
                                } catch (deleteError) {
                                  setError(deleteError instanceof Error ? deleteError.message : "Errore eliminazione regola");
                                }
                              })()
                            }
                          >
                            Elimina
                          </button>
                        </div>
                      ))}
                      {template.rules.length === 0 ? <p className="text-sm text-gray-500">Nessuna regola per questo template.</p> : null}
                    </div>
                  </div>
                ))}
              </div>
            </article>
          </div>
        </details>
      </div>

      {bootstrapModalMode ? (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-sm">
          <div className="w-full max-w-2xl rounded-3xl bg-white p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Avvio rapido</p>
                <h2 className="mt-1 text-xl font-semibold text-gray-950">
                  {bootstrapModalMode === "confirm" ? "Conferma configurazione automatica" : "Risultato configurazione automatica"}
                </h2>
                <p className="mt-2 text-sm text-gray-600">
                  {bootstrapModalMode === "confirm"
                    ? "GAIA usera i codici giornaliere importati per creare template mancanti e assegnare solo collaboratori senza configurazione con confidenza alta. Se gli assegnabili sono 0, non verra creato nessun collegamento collaboratore-template."
                    : "Operazione completata. Controlla i dettagli sotto e poi verifica eventuali legacy o casi da confermare."}
                </p>
              </div>
              <button className="btn-secondary" type="button" onClick={() => setBootstrapModalMode(null)}>
                Chiudi
              </button>
            </div>

            {bootstrapModalMode === "confirm" ? (
              <div className="mt-5 space-y-4">
                <div className="grid gap-3 md:grid-cols-4">
                  <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                    <p className="text-xs uppercase tracking-wide text-gray-500">Template da valutare</p>
                    <p className="mt-2 text-2xl font-semibold text-gray-950">{detectedPresets.length}</p>
                  </div>
                  <div className="rounded-2xl border border-sky-100 bg-sky-50 px-4 py-3">
                    <p className="text-xs uppercase tracking-wide text-sky-700">Assegnabili subito</p>
                    <p className="mt-2 text-2xl font-semibold text-sky-950">{pendingSuggestions.length}</p>
                  </div>
                  <div className="rounded-2xl border border-amber-100 bg-amber-50 px-4 py-3">
                    <p className="text-xs uppercase tracking-wide text-amber-700">Da confermare</p>
                    <p className="mt-2 text-2xl font-semibold text-amber-950">{probableSuggestions.length + suggestionsWithoutPreset.length}</p>
                  </div>
                  <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                    <p className="text-xs uppercase tracking-wide text-gray-500">Già assegnati</p>
                    <p className="mt-2 text-2xl font-semibold text-gray-950">{alreadyConfiguredSuggestions.length}</p>
                  </div>
                </div>
                <div className="rounded-2xl border border-sky-100 bg-sky-50 px-4 py-3 text-sm text-sky-900">
                  Non vengono cancellate configurazioni esistenti. I collaboratori già assegnati vengono lasciati invariati.
                </div>
                {pendingSuggestions.length === 0 ? (
                  <div className="rounded-2xl border border-amber-100 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                    In questo momento non ci sono nuovi collaboratori assegnabili automaticamente: risultano già coperti oppure richiedono conferma manuale.
                  </div>
                ) : null}
                <div className="flex flex-wrap justify-end gap-3">
                  <button className="btn-secondary" type="button" onClick={() => setBootstrapModalMode(null)}>
                    Annulla
                  </button>
                  <button className="btn-primary" disabled={isApplyingBootstrap} type="button" onClick={() => void handleBootstrapApply()}>
                    {isApplyingBootstrap ? "Configurazione in corso..." : "Conferma e configura"}
                  </button>
                </div>
              </div>
            ) : null}

            {bootstrapModalMode === "result" && bootstrapResult ? (
              <div className="mt-5 space-y-4">
                <div className="grid gap-3 md:grid-cols-4">
                  <div className="rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-3">
                    <p className="text-xs uppercase tracking-wide text-emerald-700">Template creati</p>
                    <p className="mt-2 text-2xl font-semibold text-emerald-950">{bootstrapResult.created_templates}</p>
                  </div>
                  <div className="rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-3">
                    <p className="text-xs uppercase tracking-wide text-emerald-700">Assegnazioni</p>
                    <p className="mt-2 text-2xl font-semibold text-emerald-950">{bootstrapResult.created_assignments}</p>
                  </div>
                  <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                    <p className="text-xs uppercase tracking-wide text-gray-500">Template saltati</p>
                    <p className="mt-2 text-2xl font-semibold text-gray-950">{bootstrapResult.skipped_existing_templates}</p>
                  </div>
                  <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                    <p className="text-xs uppercase tracking-wide text-gray-500">Già presenti / non applicate</p>
                    <p className="mt-2 text-2xl font-semibold text-gray-950">{bootstrapResult.skipped_existing_assignments}</p>
                  </div>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-sm text-gray-700">
                    <p className="font-medium text-gray-900">Template creati</p>
                    <p className="mt-1">{bootstrapResult.template_codes.length ? bootstrapResult.template_codes.join(", ") : "Nessun nuovo template."}</p>
                  </div>
                  <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-sm text-gray-700">
                    <p className="font-medium text-gray-900">Collaboratori assegnati</p>
                    <p className="mt-1">{bootstrapResult.assigned_employee_codes.length ? bootstrapResult.assigned_employee_codes.join(", ") : "Nessuna nuova assegnazione automatica: i collaboratori risultano già coperti o non hanno proposta alta applicabile."}</p>
                  </div>
                </div>
                <div className="flex justify-end">
                  <button className="btn-primary" type="button" onClick={() => setBootstrapModalMode(null)}>
                    Ho capito
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </ProtectedPage>
  );
}
