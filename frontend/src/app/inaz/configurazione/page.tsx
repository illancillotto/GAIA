"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import {
  applyPresenzeScheduleBootstrap,
  createPresenzeCollaboratorScheduleAssignment,
  getPresenzeBankHoursGuidanceConfig,
  createPresenzeScheduleRule,
  createPresenzeScheduleTemplate,
  deletePresenzeScheduleRule,
  deletePresenzeScheduleTemplate,
  getPresenzeScheduleBootstrapPreview,
  listPresenzeBankHoursGuidanceConfigHistory,
  listPresenzeScheduleTemplates,
  updatePresenzeBankHoursGuidanceConfig,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type {
  PresenzeScheduleBootstrapCollaboratorSuggestion,
  PresenzeScheduleBootstrapPreviewResponse,
  PresenzeScheduleBootstrapRulePreview,
  PresenzeBankHoursGuidanceConfig,
  PresenzeBankHoursGuidanceConfigRevision,
  PresenzeScheduleTemplate,
} from "@/types/api";

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

function operatorBadgeClass(suggestion: PresenzeScheduleBootstrapCollaboratorSuggestion): string {
  if (suggestion.already_assigned) return "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200";
  if (suggestion.suggestion_confidence === "high") return "bg-sky-50 text-sky-700 ring-1 ring-sky-200";
  if (suggestion.suggestion_confidence === "medium") return "bg-amber-50 text-amber-700 ring-1 ring-amber-200";
  if (suggestion.suggestion_confidence === "low") return "bg-orange-50 text-orange-700 ring-1 ring-orange-200";
  return "bg-gray-100 text-gray-600 ring-1 ring-gray-200";
}

function formatClock(value: string): string {
  return value.slice(0, 5);
}

function describePreset(code: string, label: string): string {
  const normalized = code.trim().toUpperCase();
  if (normalized === "OPE0714_1E3SAB") return "Operai 7:00-14:00 dal lunedi al venerdi, con 1° e 3° sabato 7:00-13:30.";
  if (normalized === "IMP1_STD") return "Impiegati con orario continuato 7:35-14:00 dal lunedi al venerdi.";
  if (normalized === "IMP1_RIENTRO") return "Impiegati 7:35-14:00 con rientro pomeridiano il lunedi 14:30-17:45.";
  if (normalized === "OPE0736_STD") return "Operai 6:20-13:56 dal lunedi al venerdi.";
  return label;
}

function suggestionPriorityText(suggestion: PresenzeScheduleBootstrapCollaboratorSuggestion): string {
  if (suggestion.already_assigned) return "Configurazione gia presente";
  if (suggestion.suggestion_confidence === "high") return "Configurabile subito";
  if (suggestion.suggestion_confidence === "medium") return "Suggerimento probabile";
  if (suggestion.suggestion_confidence === "low") return "Suggerimento debole";
  return "Da verificare manualmente";
}

function confidenceLabel(confidence: PresenzeScheduleBootstrapCollaboratorSuggestion["suggestion_confidence"]): string {
  if (confidence === "high") return "Alta";
  if (confidence === "medium") return "Media";
  if (confidence === "low") return "Bassa";
  return "Assente";
}

export default function PresenzeConfigurazionePage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [focusFilter, setFocusFilter] = useState<"all" | "ready" | "review" | "configured">("all");
  const [templates, setTemplates] = useState<PresenzeScheduleTemplate[]>([]);
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
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const token = getStoredAccessToken();
    if (!token) return;
    setIsLoading(true);
    try {
      const [templateItems, preview, guidanceConfig, guidanceHistory] = await Promise.all([
        listPresenzeScheduleTemplates(token),
        getPresenzeScheduleBootstrapPreview(token),
        getPresenzeBankHoursGuidanceConfig(token),
        listPresenzeBankHoursGuidanceConfigHistory(token),
      ]);
      setTemplates(templateItems);
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

  const detectedPresets = bootstrapPreview?.presets ?? [];

  const normalizedSearchTerm = searchTerm.trim().toLowerCase();

  const filteredPendingSuggestions = useMemo(
    () =>
      pendingSuggestions.filter((suggestion) => {
        if (!normalizedSearchTerm) return true;
        const haystack = [
          suggestion.employee_code,
          suggestion.collaborator_name,
          suggestion.dominant_schedule_code ?? "",
          suggestion.schedule_codes.join(" "),
          suggestion.suggested_template_code ?? "",
          suggestion.suggested_template_label ?? "",
        ]
          .join(" ")
          .toLowerCase();
        return haystack.includes(normalizedSearchTerm);
      }),
    [normalizedSearchTerm, pendingSuggestions],
  );

  const filteredSuggestionsWithoutPreset = useMemo(
    () =>
      suggestionsWithoutPreset.filter((suggestion) => {
        if (!normalizedSearchTerm) return true;
        const haystack = [
          suggestion.employee_code,
          suggestion.collaborator_name,
          suggestion.dominant_schedule_code ?? "",
          suggestion.schedule_codes.join(" "),
        ]
          .join(" ")
          .toLowerCase();
        return haystack.includes(normalizedSearchTerm);
      }),
    [normalizedSearchTerm, suggestionsWithoutPreset],
  );

  const filteredAlreadyConfiguredSuggestions = useMemo(
    () =>
      alreadyConfiguredSuggestions.filter((suggestion) => {
        if (!normalizedSearchTerm) return true;
        const haystack = [
          suggestion.employee_code,
          suggestion.collaborator_name,
          suggestion.dominant_schedule_code ?? "",
          suggestion.schedule_codes.join(" "),
          suggestion.suggested_template_code ?? "",
          suggestion.suggested_template_label ?? "",
        ]
          .join(" ")
          .toLowerCase();
        return haystack.includes(normalizedSearchTerm);
      }),
    [alreadyConfiguredSuggestions, normalizedSearchTerm],
  );

  const filteredProbableSuggestions = useMemo(
    () =>
      probableSuggestions.filter((suggestion) => {
        if (!normalizedSearchTerm) return true;
        const haystack = [
          suggestion.employee_code,
          suggestion.collaborator_name,
          suggestion.dominant_schedule_code ?? "",
          suggestion.schedule_codes.join(" "),
          suggestion.suggested_template_code ?? "",
          suggestion.suggested_template_label ?? "",
        ]
          .join(" ")
          .toLowerCase();
        return haystack.includes(normalizedSearchTerm);
      }),
    [normalizedSearchTerm, probableSuggestions],
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
        notes: `Assegnazione guidata da schedule code INAZ: ${suggestion.schedule_codes.join(", ")}`,
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
      description="Impostazione guidata di orari, festivita e regole con suggerimenti automatici dai dati INAZ gia importati."
      breadcrumb="Giornaliere"
      requiredModule="inaz"
      requiredRoles={["admin", "super_admin"]}
    >
      <div className="space-y-6">
        {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
        {success ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div> : null}

        <section className="panel-card space-y-5">
          <div className="space-y-1">
            <h2 className="text-lg font-semibold text-gray-900">Policy banca ore</h2>
            <p className="max-w-3xl text-sm text-gray-600">
              Regole operative usate dalla liquidazione guidata in `/presenze/banca-ore`. Qui decidi quali bucket di straordinario possono generare
              proposte automatiche e quando una quota deve invece passare in revisione HR.
            </p>
          </div>
          {bankHoursGuidanceConfig ? (
            <div className="space-y-4">
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
            <p className="text-sm text-gray-500">Caricamento policy banca ore...</p>
          )}
        </section>

        <section className="panel-card space-y-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-1">
              <h2 className="text-lg font-semibold text-gray-900">Avvio rapido</h2>
              <p className="max-w-3xl text-sm text-gray-600">
                GAIA ha letto gli orari gia presenti nelle giornaliere INAZ e propone una configurazione iniziale. L&apos;obiettivo e ridurre al minimo
                i passaggi manuali: prima creiamo i template base, poi assegniamo automaticamente i collaboratori compatibili.
              </p>
            </div>
            <button className="btn-primary" disabled={isApplyingBootstrap || isLoading} onClick={() => void handleBootstrapApply()} type="button">
              {isApplyingBootstrap ? "Configurazione in corso..." : "Configura automaticamente"}
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
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Collaboratori configurabili</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{bootstrapPreview?.collaborators_with_suggestion_total ?? "—"}</p>
            </div>
            <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-4">
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Senza assegnazione</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{bootstrapPreview?.collaborators_without_assignment_total ?? "—"}</p>
            </div>
          </div>

          <div className="rounded-2xl border border-sky-100 bg-sky-50 px-4 py-4 text-sm text-sky-900">
            <p className="font-medium">Cosa succede con il bootstrap automatico</p>
            <p className="mt-1">
              Vengono creati solo i template mancanti e vengono assegnati solo i collaboratori senza template gia presente. I preset nascono dai codici
              orario rilevati in INAZ, per esempio `OPE0714`, `OPESAB`, `IMP1`, `RIENTRO IMP`, `OPE0736`.
            </p>
          </div>

          <div className="grid gap-3 lg:grid-cols-3">
            <div className="rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-4">
              <p className="text-sm font-semibold text-emerald-900">1. Configura automaticamente</p>
              <p className="mt-1 text-sm text-emerald-800">Crea i template base mancanti e assegna i casi chiari senza richiedere interventi tecnici.</p>
            </div>
            <div className="rounded-2xl border border-amber-100 bg-amber-50 px-4 py-4">
              <p className="text-sm font-semibold text-amber-900">2. Controlla i casi da verificare</p>
              <p className="mt-1 text-sm text-amber-800">I collaboratori senza proposta automatica vengono messi in evidenza per una verifica guidata.</p>
            </div>
            <div className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-4">
              <p className="text-sm font-semibold text-gray-900">3. Usa le opzioni avanzate solo se serve</p>
              <p className="mt-1 text-sm text-gray-700">Festivita, eccezioni e regole manuali restano disponibili, ma non sono il percorso principale.</p>
            </div>
          </div>
        </section>

        <section className="panel-card space-y-4">
          <div className="space-y-1">
            <h2 className="text-lg font-semibold text-gray-900">Template suggeriti dai dati INAZ</h2>
            <p className="text-sm text-gray-600">Questi profili sono stati derivati dai codici orario gia presenti nel database.</p>
          </div>
          <div className="grid gap-4 xl:grid-cols-2">
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
                  {preset.rules.map((rule, index) => (
                    <div key={`${preset.preset_key}-${index}`} className="rounded-xl border border-white bg-white px-3 py-2 text-sm text-gray-700">
                      <span className="font-medium">{rule.label ?? recurrenceLabel(rule)}</span>
                      <span className="text-gray-500"> · {recurrenceLabel(rule)} · {formatClock(rule.start_time)} - {formatClock(rule.end_time)}</span>
                    </div>
                  ))}
                </div>
              </article>
            ))}
            {detectedPresets.length === 0 ? <p className="text-sm text-gray-500">Nessun preset suggerito disponibile.</p> : null}
          </div>
        </section>

        <section className="panel-card space-y-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <label className="block max-w-xl flex-1 text-sm font-medium text-gray-700">
              Cerca collaboratore o codice orario
              <input
                className="form-control mt-1"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="Es. 122, Sanna, OPE0714, rientro"
              />
            </label>
            <div className="flex flex-wrap gap-2">
              <button
                className={`rounded-full px-4 py-2 text-sm font-medium ${focusFilter === "all" ? "bg-gray-900 text-white" : "bg-gray-100 text-gray-700"}`}
                onClick={() => setFocusFilter("all")}
                type="button"
              >
                Tutto
              </button>
              <button
                className={`rounded-full px-4 py-2 text-sm font-medium ${focusFilter === "ready" ? "bg-sky-700 text-white" : "bg-sky-50 text-sky-800"}`}
                onClick={() => setFocusFilter("ready")}
                type="button"
              >
                Solo pronti
              </button>
              <button
                className={`rounded-full px-4 py-2 text-sm font-medium ${focusFilter === "review" ? "bg-amber-600 text-white" : "bg-amber-50 text-amber-800"}`}
                onClick={() => setFocusFilter("review")}
                type="button"
              >
                Solo da verificare
              </button>
              <button
                className={`rounded-full px-4 py-2 text-sm font-medium ${focusFilter === "configured" ? "bg-emerald-700 text-white" : "bg-emerald-50 text-emerald-800"}`}
                onClick={() => setFocusFilter("configured")}
                type="button"
              >
                Solo gia configurati
              </button>
            </div>
          </div>

          <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-sm text-gray-700">
            {focusFilter === "all" ? "Vista completa attiva." : null}
            {focusFilter === "ready" ? "Stai vedendo solo i collaboratori configurabili subito." : null}
            {focusFilter === "review" ? "Stai vedendo i casi che richiedono verifica o conferma manuale." : null}
            {focusFilter === "configured" ? "Stai vedendo solo i collaboratori gia coperti da una configurazione." : null}
            {normalizedSearchTerm ? ` Filtro ricerca: "${searchTerm}".` : ""}
          </div>
        </section>

        {focusFilter !== "review" && focusFilter !== "configured" ? (
          <section className="panel-card space-y-4">
          <div className="space-y-1">
            <h2 className="text-lg font-semibold text-gray-900">Collaboratori da completare</h2>
            <p className="text-sm text-gray-600">
              Elenco ordinato per priorita: prima chi non ha ancora un template assegnato e per cui il sistema ha gia una proposta coerente.
            </p>
          </div>

          <div className="space-y-3">
            {filteredPendingSuggestions.slice(0, 24).map((suggestion) => (
              <div key={suggestion.collaborator_id} className="flex flex-col gap-3 rounded-2xl border border-gray-100 bg-gray-50 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium text-gray-900">
                      {suggestion.employee_code} · {suggestion.collaborator_name}
                    </p>
                    <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${operatorBadgeClass(suggestion)}`}>
                      {suggestionPriorityText(suggestion)}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600">
                    Proposta: <span className="font-medium text-gray-900">{suggestion.suggested_template_label}</span>
                    {suggestion.suggested_template_code ? ` (${suggestion.suggested_template_code})` : ""}
                  </p>
                  <p className="text-xs text-gray-500">
                    Codici osservati: {suggestion.schedule_codes.join(", ") || "nessuno"} · dominante: {suggestion.dominant_schedule_code ?? "n/d"}
                  </p>
                </div>
                <button
                  className="btn-secondary"
                  disabled={assigningCollaboratorId === suggestion.collaborator_id}
                  onClick={() => void handleAssignSuggestion(suggestion)}
                  type="button"
                >
                  {assigningCollaboratorId === suggestion.collaborator_id ? "Assegnazione..." : "Assegna template suggerito"}
                </button>
              </div>
            ))}
            {filteredPendingSuggestions.length === 0 ? (
              <p className="text-sm text-gray-500">
                Nessun collaboratore trovato in questa vista. La configurazione base puo essere gia completa oppure il filtro attivo non restituisce risultati.
              </p>
            ) : null}
          </div>
        </section>
        ) : null}

        {focusFilter !== "ready" && focusFilter !== "configured" ? (
          <section className="panel-card space-y-4">
            <div className="space-y-1">
              <h2 className="text-lg font-semibold text-gray-900">Suggerimenti da confermare</h2>
              <p className="text-sm text-gray-600">
                Qui GAIA propone il template piu probabile, ma non lo considera ancora abbastanza solido da trattarlo come assegnazione pronta.
              </p>
            </div>
            {filteredProbableSuggestions.length > 0 ? (
              <div className="space-y-3">
                {filteredProbableSuggestions.slice(0, 24).map((suggestion) => (
                  <div
                    key={suggestion.collaborator_id}
                    className="flex flex-col gap-3 rounded-2xl border border-amber-100 bg-amber-50 px-4 py-4 lg:flex-row lg:items-center lg:justify-between"
                  >
                    <div className="min-w-0 space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium text-amber-950">
                          {suggestion.employee_code} · {suggestion.collaborator_name}
                        </p>
                        <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${operatorBadgeClass(suggestion)}`}>
                          {suggestionPriorityText(suggestion)}
                        </span>
                        <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-amber-700 ring-1 ring-amber-200">
                          Confidenza {confidenceLabel(suggestion.suggestion_confidence)}
                        </span>
                      </div>
                      <p className="text-sm text-amber-900">
                        Proposta: <span className="font-medium">{suggestion.suggested_template_label}</span>
                        {suggestion.suggested_template_code ? ` (${suggestion.suggested_template_code})` : ""}
                      </p>
                      <p className="text-xs text-amber-800">
                        {suggestion.suggestion_reason ?? "Il sistema ha trovato un profilo compatibile, ma richiede conferma umana."}
                      </p>
                      <p className="text-xs text-amber-700">
                        Codici osservati: {suggestion.schedule_codes.join(", ") || "nessuno"} · dominante: {suggestion.dominant_schedule_code ?? "n/d"}
                      </p>
                    </div>
                    <button
                      className="btn-secondary"
                      disabled={assigningCollaboratorId === suggestion.collaborator_id}
                      onClick={() => void handleAssignSuggestion(suggestion)}
                      type="button"
                    >
                      {assigningCollaboratorId === suggestion.collaborator_id ? "Conferma..." : "Conferma questo template"}
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-4 text-sm text-gray-700">
                Nessun suggerimento probabile trovato con i filtri correnti.
              </div>
            )}
          </section>
        ) : null}

        {focusFilter !== "ready" && focusFilter !== "configured" ? (
        <section className="panel-card space-y-4">
          <div className="space-y-1">
            <h2 className="text-lg font-semibold text-gray-900">Casi da verificare</h2>
            <p className="text-sm text-gray-600">
              Qui trovi i collaboratori per cui i dati storici non bastano neppure a proporre un template probabile affidabile.
            </p>
          </div>
          {filteredSuggestionsWithoutPreset.length > 0 ? (
            <div className="space-y-3">
              {filteredSuggestionsWithoutPreset.slice(0, 24).map((suggestion) => (
                <div
                  key={suggestion.collaborator_id}
                  className="rounded-2xl border border-amber-100 bg-amber-50 px-4 py-4"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium text-amber-950">
                      {suggestion.employee_code} · {suggestion.collaborator_name}
                    </p>
                    <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-amber-700 ring-1 ring-amber-200">
                      Da verificare manualmente
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-amber-900">
                    Codici osservati: {suggestion.schedule_codes.join(", ") || "nessuno"} · dominante: {suggestion.dominant_schedule_code ?? "n/d"}
                  </p>
                  <p className="mt-1 text-sm text-amber-800">
                    Azione consigliata: controllare il profilo orario reale e poi usare le opzioni avanzate per creare o assegnare il template corretto.
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-4 text-sm text-emerald-800">
              Nessun caso critico trovato in questa vista: tutti i collaboratori senza assegnazione hanno gia una proposta automatica oppure il filtro attivo non restituisce risultati.
            </div>
          )}
        </section>
        ) : null}

        {focusFilter !== "ready" && focusFilter !== "review" ? (
          <section className="panel-card space-y-4">
            <div className="space-y-1">
              <h2 className="text-lg font-semibold text-gray-900">Collaboratori gia configurati</h2>
              <p className="text-sm text-gray-600">Elenco di controllo per verificare rapidamente chi ha gia un template assegnato.</p>
            </div>
            {filteredAlreadyConfiguredSuggestions.length > 0 ? (
              <div className="space-y-3">
                {filteredAlreadyConfiguredSuggestions.slice(0, 24).map((suggestion) => (
                  <div key={suggestion.collaborator_id} className="rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium text-emerald-950">
                        {suggestion.employee_code} · {suggestion.collaborator_name}
                      </p>
                      <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-emerald-700 ring-1 ring-emerald-200">
                        Configurazione gia presente
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-emerald-900">
                      Template suggerito: {suggestion.suggested_template_label ?? "Template presente"}{suggestion.suggested_template_code ? ` (${suggestion.suggested_template_code})` : ""}
                    </p>
                    <p className="mt-1 text-xs text-emerald-800">
                      Codici osservati: {suggestion.schedule_codes.join(", ") || "nessuno"} · dominante: {suggestion.dominant_schedule_code ?? "n/d"}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-4 text-sm text-gray-700">
                Nessun collaboratore configurato trovato con i filtri correnti.
              </div>
            )}
          </section>
        ) : null}

        <section className="panel-card space-y-4">
          <div className="space-y-1">
            <h2 className="text-lg font-semibold text-gray-900">Stato configurazione</h2>
            <p className="text-sm text-gray-600">Vista rapida per capire quanto del lavoro e gia stato coperto automaticamente.</p>
          </div>
          <div className="grid gap-3 md:grid-cols-4">
            <div className="rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-4">
              <p className="text-sm font-medium text-emerald-900">Gia configurati</p>
              <p className="mt-2 text-2xl font-semibold text-emerald-950">{alreadyConfiguredSuggestions.length}</p>
            </div>
            <div className="rounded-2xl border border-sky-100 bg-sky-50 px-4 py-4">
              <p className="text-sm font-medium text-sky-900">Configurabili subito</p>
              <p className="mt-2 text-2xl font-semibold text-sky-950">{pendingSuggestions.length}</p>
            </div>
            <div className="rounded-2xl border border-amber-100 bg-amber-50 px-4 py-4">
              <p className="text-sm font-medium text-amber-900">Da confermare</p>
              <p className="mt-2 text-2xl font-semibold text-amber-950">{probableSuggestions.length}</p>
            </div>
            <div className="rounded-2xl border border-amber-100 bg-amber-50 px-4 py-4">
              <p className="text-sm font-medium text-amber-900">Da verificare</p>
              <p className="mt-2 text-2xl font-semibold text-amber-950">{suggestionsWithoutPreset.length}</p>
            </div>
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
    </ProtectedPage>
  );
}
