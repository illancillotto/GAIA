"use client";

import { useParams, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { Badge } from "@/components/ui/badge";
import {
  createPresenzeCollaboratorScheduleAssignment,
  deletePresenzeScheduleAssignment,
  getCurrentUser,
  getPresenzeCollaboratorCalendar,
  getPresenzeScheduleBootstrapPreview,
  getPresenzeCollaboratorSummary,
  listAllApplicationUsers,
  listAllPresenzeCollaborators,
  listPresenzeCollaboratorScheduleAssignments,
  listPresenzeScheduleTemplates,
  mapPresenzeCollaboratorApplicationUser,
  updatePresenzeCollaboratorContractProfile,
  updatePresenzeDailyRecord,
} from "@/lib/api";
import {
  notifyPresenzeCollaboratorDetailUpdated,
  scorePresenzeCollaboratorUserMatch,
  usersForPresenzeCollaboratorMappingSorted,
} from "@/lib/presenze-collaborator-mapping";
import { getStoredAccessToken } from "@/lib/auth";
import { getPresenzeCompanyLabel } from "@/lib/presenze-display";
import type {
  ApplicationUser,
  CurrentUser,
  PresenzeCollaborator,
  PresenzeCollaboratorScheduleAssignment,
  PresenzeDailyRecord,
  PresenzeEventSummary,
  PresenzeScheduleProfilePreview,
  PresenzeScheduleTemplate,
} from "@/types/api";

type TabKey = "calendar" | "summary";
const NON_ASSIGNABLE_INAZ_TEMPLATE_CODES = new Set([
  "OP_5.3_12.3",
  "OSAB5.3_12.3",
]);
type GaiaProfileCode = "GAIA_OPERAI" | "GAIA_IMPIEGATI" | "";
const DEFAULT_GAIA_PROFILES: PresenzeScheduleProfilePreview[] = [
  {
    profile_code: "GAIA_OPERAI",
    profile_label: "Profilo Operai",
    description:
      "Profilo GAIA per operai con controllo rigido delle ore effettive e gestione del gruppo operaio.",
    template_codes: [
      "OPE0714_1E3SAB",
      "OPE0736_STD",
      "OP_5.3_12.3",
      "OSAB5.3_12.3",
    ],
    rule_summaries: [
      "Feriale 7h",
      "Agrario sabato 6h30",
      "Catasto/magazzino sabato 6h",
    ],
    active: true,
  },
  {
    profile_code: "GAIA_IMPIEGATI",
    profile_label: "Profilo Impiegati",
    description: "Profilo GAIA per impiegati con orari flessibili e rientri.",
    template_codes: ["IMP1_STD", "IMP1_RIENTRO"],
    rule_summaries: ["Flessibile IMP1", "Rientro lunedi pomeriggio"],
    active: true,
  },
];

function currentMonthBounds(): { start: string; end: string } {
  const now = new Date();
  const start = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
  const end = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()).padStart(2, "0")}`;
  return { start, end };
}

function monthBoundsFromDate(isoDate: string): { start: string; end: string } {
  const [year, month] = isoDate.split("-").map(Number);
  const start = `${year}-${String(month).padStart(2, "0")}-01`;
  const end = `${year}-${String(month).padStart(2, "0")}-${String(new Date(year, month, 0).getDate()).padStart(2, "0")}`;
  return { start, end };
}

function shiftMonthBounds(
  isoDate: string,
  delta: number,
): { start: string; end: string } {
  const [year, month] = isoDate.split("-").map(Number);
  const shifted = new Date(year, month - 1 + delta, 1);
  return monthBoundsFromDate(
    `${shifted.getFullYear()}-${String(shifted.getMonth() + 1).padStart(2, "0")}-01`,
  );
}

function formatMonthRangeLabel(isoDate: string): string {
  return new Intl.DateTimeFormat("it-IT", {
    month: "long",
    year: "numeric",
  }).format(new Date(`${isoDate}T00:00:00`));
}

function formatHours(minutes: number | null): string {
  if (minutes == null) return "—";
  return `${(minutes / 60).toFixed(2)} h`;
}

function formatStandardDailyMinutes(
  minutes: number | null | undefined,
): string {
  if (minutes == null) return "—";
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return `${hours}:${String(remainder).padStart(2, "0")}`;
}

function formatContractKind(
  value: PresenzeCollaborator["contract_kind"] | null | undefined,
): string {
  if (!value) return "—";
  const labels: Record<
    NonNullable<PresenzeCollaborator["contract_kind"]>,
    string
  > = {
    operaio: "Operaio",
    impiegato: "Impiegato",
    quadro: "Quadro",
    altro: "Altro",
  };
  return labels[value] ?? value;
}

function formatOperaiGroup(
  value: PresenzeCollaborator["operai_group"] | null | undefined,
): string {
  if (value === "agrario") return "Agrario";
  if (value === "catasto_magazzino") return "Catasto / magazzino";
  return "Non impostato";
}

function operaiGroupBadgeVariant(
  value: PresenzeCollaborator["operai_group"] | null | undefined,
): "success" | "info" | "neutral" {
  if (value === "agrario") return "success";
  if (value === "catasto_magazzino") return "info";
  return "neutral";
}

function uniqueTemplateInazCodes(
  template: PresenzeCollaboratorScheduleAssignment["template"],
): string[] {
  if (!template) return [];
  return Array.from(
    new Set(
      (template.rules ?? [])
        .map((rule) => rule.ordinary_label?.trim())
        .filter((value): value is string => Boolean(value)),
    ),
  ).sort((left, right) => left.localeCompare(right));
}

function templateDisplayTitle(
  template:
    PresenzeCollaboratorScheduleAssignment["template"] | null | undefined,
): string {
  if (!template) return "Template non disponibile";
  return template.label?.trim() || template.code || `Template #${template.id}`;
}

function isAssignableGaiaTemplate(template: PresenzeScheduleTemplate): boolean {
  return !NON_ASSIGNABLE_INAZ_TEMPLATE_CODES.has(
    template.code.trim().toUpperCase(),
  );
}

function inferGaiaProfileCode(
  collaborator: PresenzeCollaborator | null | undefined,
): GaiaProfileCode {
  if (collaborator?.operai_group) return "GAIA_OPERAI";
  if (!collaborator?.contract_kind) return "";
  if (collaborator.contract_kind === "operaio") return "GAIA_OPERAI";
  if (
    collaborator.contract_kind === "impiegato" ||
    collaborator.contract_kind === "quadro" ||
    collaborator.contract_kind === "altro"
  )
    return "GAIA_IMPIEGATI";
  return "";
}

function formatAbsenceCause(cause: string | null | undefined): string {
  if (!cause) return "—";
  const labels: Record<string, string> = {
    ferie: "Ferie",
    permesso: "Permesso",
    malattia: "Malattia",
    riposo: "Riposo",
    festivita: "Festivita",
    banca_ore: "Banca ore",
    assenza_da_giustificare: "Assenza da giustificare",
  };
  return labels[cause] ?? cause.replaceAll("_", " ");
}

function formatRequestDescription(value: string | null | undefined): string {
  if (!value) return "—";
  if (value.includes(" - ")) {
    const [, right] = value.split(" - ", 2);
    if (right?.trim()) return right.trim();
  }
  return value;
}

function recoveryBadgeLabel(record: PresenzeDailyRecord): string | null {
  if (record.grants_recovery_day)
    return `Recupero +${record.recovery_day_credit}`;
  if (record.uses_recovery_day) return `Recupero -${record.recovery_day_debit}`;
  if (record.holiday_kind === "ordinary") return "Festivita ordinaria";
  if (record.holiday_kind === "working_override") return "Override lavorativo";
  return null;
}

function requestBadgeLabel(record: PresenzeDailyRecord): string | null {
  if (record.resolved_absence_cause) {
    return formatAbsenceCause(record.resolved_absence_cause);
  }
  if (record.request_description) {
    return formatRequestDescription(record.request_description);
  }
  return null;
}

function formatDetailEntries(
  values: Record<string, string>,
): Array<[string, string]> {
  return Object.entries(values);
}

function firstDetailPreview(
  items: Array<Record<string, string>>,
): string | null {
  for (const item of items) {
    for (const value of Object.values(item)) {
      if (typeof value === "string" && value.trim()) {
        return value.trim();
      }
    }
  }
  return null;
}

function sectionSummaryLabel(
  title: string,
  options?: { count?: number; preview?: string | null; status?: string | null },
): string {
  const countLabel =
    typeof options?.count === "number" && options.count > 0
      ? `${options.count} ${options.count === 1 ? "voce" : "voci"}`
      : null;
  const parts = [options?.status, options?.preview, countLabel].filter(Boolean);
  return parts.length > 0 ? `${title} (${parts.join(" · ")})` : title;
}

export default function PresenzeCollaboratoreDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const collaboratorId = params.id as string;
  const isEmbedded = searchParams.get("embedded") === "1";
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [users, setUsers] = useState<ApplicationUser[]>([]);
  const [allCollaborators, setAllCollaborators] = useState<
    PresenzeCollaborator[]
  >([]);
  const [collaborator, setCollaborator] = useState<PresenzeCollaborator | null>(
    null,
  );
  const [records, setRecords] = useState<PresenzeDailyRecord[]>([]);
  const [summary, setSummary] = useState<PresenzeEventSummary[]>([]);
  const [templates, setTemplates] = useState<PresenzeScheduleTemplate[]>([]);
  const [gaiaProfiles, setGaiaProfiles] = useState<
    PresenzeScheduleProfilePreview[]
  >([]);
  const [assignments, setAssignments] = useState<
    PresenzeCollaboratorScheduleAssignment[]
  >([]);
  const [tab, setTab] = useState<TabKey>("calendar");
  const [dateFrom, setDateFrom] = useState(currentMonthBounds().start);
  const [dateTo, setDateTo] = useState(currentMonthBounds().end);
  const [mappingValue, setMappingValue] = useState("");
  const [assignmentTemplateId, setAssignmentTemplateId] = useState("");
  const [suggestedTemplateCode, setSuggestedTemplateCode] = useState<
    string | null
  >(null);
  const [assignmentValidFrom, setAssignmentValidFrom] = useState("");
  const [assignmentValidTo, setAssignmentValidTo] = useState("");
  const [assignmentNotes, setAssignmentNotes] = useState("");
  const [dailyOverrides, setDailyOverrides] = useState<
    Record<
      string,
      {
        km_value: string;
        trasferta_minutes: string;
        trasferta_montano: boolean;
        reperibilita_giornaliera: boolean;
        override_straordinario_minutes: string;
        override_mpe_minutes: string;
        manual_note: string;
      }
    >
  >({});
  const [error, setError] = useState<string | null>(null);
  const [mappingNotice, setMappingNotice] = useState<{
    tone: "success" | "error";
    message: string;
  } | null>(null);
  const [savingMapping, setSavingMapping] = useState(false);
  const [gaiaProfileCode, setGaiaProfileCode] = useState<GaiaProfileCode>("");
  const [operaiGroupValue, setOperaiGroupValue] = useState<
    NonNullable<PresenzeCollaborator["operai_group"]> | ""
  >("");
  const [standardDailyMinutesValue, setStandardDailyMinutesValue] =
    useState("");
  const [savingContractProfile, setSavingContractProfile] = useState(false);
  const isDuplicateAssignment = assignments.some(
    (assignment) =>
      assignment.template_id === Number(assignmentTemplateId || 0) &&
      (assignment.valid_from ?? "") === (assignmentValidFrom || "") &&
      (assignment.valid_to ?? "") === (assignmentValidTo || ""),
  );
  const assignableTemplates = useMemo(
    () => templates.filter(isAssignableGaiaTemplate),
    [templates],
  );
  const effectiveGaiaProfiles = useMemo(
    () => (gaiaProfiles.length > 0 ? gaiaProfiles : DEFAULT_GAIA_PROFILES),
    [gaiaProfiles],
  );
  const selectedGaiaProfile = useMemo(
    () =>
      effectiveGaiaProfiles.find(
        (profile) => profile.profile_code === gaiaProfileCode,
      ) ?? null,
    [effectiveGaiaProfiles, gaiaProfileCode],
  );
  const assignableTemplatesForProfile = useMemo(() => {
    if (!selectedGaiaProfile) return assignableTemplates;
    const allowedCodes = new Set(
      selectedGaiaProfile.template_codes.map((code) =>
        code.trim().toUpperCase(),
      ),
    );
    return assignableTemplates.filter((template) =>
      allowedCodes.has(template.code.trim().toUpperCase()),
    );
  }, [assignableTemplates, selectedGaiaProfile]);

  const loadDetailData = useCallback(
    async (token: string) => {
      const sessionUser = await getCurrentUser(token);
      const [
        userItems,
        collaboratorItems,
        calendarResponse,
        summaryResponse,
        templatesResponse,
        assignmentsResponse,
        bootstrapPreview,
      ] = await Promise.all([
        sessionUser.role === "admin" || sessionUser.role === "super_admin"
          ? listAllApplicationUsers(token)
          : Promise.resolve([]),
        listAllPresenzeCollaborators(token),
        getPresenzeCollaboratorCalendar(
          token,
          collaboratorId,
          dateFrom,
          dateTo,
        ),
        getPresenzeCollaboratorSummary(token, collaboratorId, dateFrom, dateTo),
        sessionUser.role === "admin" || sessionUser.role === "super_admin"
          ? listPresenzeScheduleTemplates(token)
          : Promise.resolve([]),
        sessionUser.role === "admin" || sessionUser.role === "super_admin"
          ? listPresenzeCollaboratorScheduleAssignments(token, collaboratorId)
          : Promise.resolve([]),
        sessionUser.role === "admin" || sessionUser.role === "super_admin"
          ? getPresenzeScheduleBootstrapPreview(token)
          : Promise.resolve(null),
      ]);

      setCurrentUser(sessionUser);
      setUsers(userItems);
      setAllCollaborators(collaboratorItems);
      setCollaborator(
        collaboratorItems.find((item) => item.id === collaboratorId) ??
          calendarResponse.collaborator,
      );
      setRecords(calendarResponse.items);
      setSummary(summaryResponse.items);
      setTemplates(templatesResponse);
      setGaiaProfiles(bootstrapPreview?.profiles ?? []);
      setAssignments(assignmentsResponse);
      const resolvedCollaborator =
        collaboratorItems.find((item) => item.id === collaboratorId) ??
        calendarResponse.collaborator;
      const bootstrapSuggestion =
        bootstrapPreview?.collaborator_suggestions.find(
          (item) => item.collaborator_id === collaboratorId,
        ) ?? null;
      setMappingValue(String(resolvedCollaborator.application_user_id ?? ""));
      setGaiaProfileCode(inferGaiaProfileCode(resolvedCollaborator));
      setSuggestedTemplateCode(
        bootstrapSuggestion?.suggested_template_code ?? null,
      );
      setOperaiGroupValue(resolvedCollaborator.operai_group ?? "");
      setStandardDailyMinutesValue(
        resolvedCollaborator.standard_daily_minutes != null
          ? String(resolvedCollaborator.standard_daily_minutes)
          : "",
      );
      setDailyOverrides(
        Object.fromEntries(
          calendarResponse.items.map((record) => [
            record.id,
            {
              km_value: record.km_value != null ? String(record.km_value) : "",
              trasferta_minutes:
                record.trasferta_minutes != null
                  ? String(record.trasferta_minutes)
                  : "",
              trasferta_montano: record.trasferta_montano,
              reperibilita_giornaliera:
                record.reperibilita_unit !== "none" &&
                (record.reperibilita_quantity ?? 0) > 0,
              override_straordinario_minutes:
                record.override_straordinario_minutes != null
                  ? String(record.override_straordinario_minutes)
                  : "",
              override_mpe_minutes:
                record.override_mpe_minutes != null
                  ? String(record.override_mpe_minutes)
                  : "",
              manual_note: record.manual_note ?? "",
            },
          ]),
        ),
      );
    },
    [collaboratorId, dateFrom, dateTo],
  );

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token || !collaboratorId) return;
    loadDetailData(token).catch((loadError) =>
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Errore caricamento dettaglio collaboratore",
      ),
    );
  }, [collaboratorId, dateFrom, dateTo, loadDetailData]);

  const totalOrdinary = useMemo(
    () => records.reduce((sum, item) => sum + (item.ordinary_minutes ?? 0), 0),
    [records],
  );
  const totalAbsence = useMemo(
    () => records.reduce((sum, item) => sum + (item.absence_minutes ?? 0), 0),
    [records],
  );
  const totalExtra = useMemo(
    () =>
      records.reduce(
        (sum, item) =>
          sum + (item.straordinario_minutes ?? 0) + (item.mpe_minutes ?? 0),
        0,
      ),
    [records],
  );
  const totalRecoveryDays = useMemo(
    () =>
      records.reduce((sum, item) => sum + (item.recovery_day_credit ?? 0), 0),
    [records],
  );
  const totalRecoveryUsed = useMemo(
    () =>
      records.reduce((sum, item) => sum + (item.recovery_day_debit ?? 0), 0),
    [records],
  );
  const totalRecoveryBalance = totalRecoveryDays - totalRecoveryUsed;
  const canEdit =
    currentUser?.role === "admin" || currentUser?.role === "super_admin";
  const activeMonthLabel = useMemo(
    () => formatMonthRangeLabel(dateFrom),
    [dateFrom],
  );
  const mappingUsers = useMemo(
    () =>
      collaborator
        ? usersForPresenzeCollaboratorMappingSorted(
            collaborator,
            users,
            allCollaborators,
            collaboratorId,
          )
        : [],
    [collaborator, users, allCollaborators, collaboratorId],
  );
  const suggestedMapping = useMemo(() => {
    if (!collaborator || mappingUsers.length === 0) return null;
    let bestUser: ApplicationUser | null = null;
    let bestScore = 0;
    for (const user of mappingUsers) {
      const score = scorePresenzeCollaboratorUserMatch(collaborator, user);
      if (score > bestScore) {
        bestScore = score;
        bestUser = user;
      }
    }
    if (!bestUser || bestScore < 70) return null;
    return {
      user: bestUser,
      confidence: bestScore >= 120 ? "alta" : "media",
    };
  }, [collaborator, mappingUsers]);

  useEffect(() => {
    if (!collaborator || collaborator.application_user_id != null) {
      return;
    }
    if (!mappingValue && suggestedMapping) {
      setMappingValue(String(suggestedMapping.user.id));
    }
  }, [collaborator, suggestedMapping, mappingValue]);

  useEffect(() => {
    if (gaiaProfileCode === "GAIA_OPERAI") {
      setStandardDailyMinutesValue((current) => current || "420");
      return;
    }
    if (gaiaProfileCode === "GAIA_IMPIEGATI") {
      setOperaiGroupValue("");
      setStandardDailyMinutesValue((current) => current || "385");
    }
  }, [gaiaProfileCode]);

  useEffect(() => {
    if (!assignmentTemplateId) return;
    if (
      assignableTemplatesForProfile.some(
        (template) => String(template.id) === assignmentTemplateId,
      )
    )
      return;
    setAssignmentTemplateId("");
  }, [assignmentTemplateId, assignableTemplatesForProfile]);

  useEffect(() => {
    if (assignableTemplatesForProfile.length === 0) {
      if (assignmentTemplateId) {
        setAssignmentTemplateId("");
      }
      return;
    }
    if (
      assignmentTemplateId &&
      assignableTemplatesForProfile.some(
        (template) => String(template.id) === assignmentTemplateId,
      )
    ) {
      return;
    }

    const normalizedSuggestedCode =
      suggestedTemplateCode?.trim().toUpperCase() ?? "";
    const suggestedTemplate = normalizedSuggestedCode
      ? assignableTemplatesForProfile.find(
          (template) =>
            template.code.trim().toUpperCase() === normalizedSuggestedCode,
        )
      : null;
    setAssignmentTemplateId(
      String((suggestedTemplate ?? assignableTemplatesForProfile[0]).id),
    );
  }, [
    assignmentTemplateId,
    assignableTemplatesForProfile,
    suggestedTemplateCode,
  ]);

  async function handleSaveMapping() {
    const token = getStoredAccessToken();
    if (!collaborator) {
      setMappingNotice({
        tone: "error",
        message: "Collaboratore non caricato. Ricarica la pagina.",
      });
      return;
    }
    if (!token) {
      setMappingNotice({
        tone: "error",
        message: "Sessione scaduta. Effettua di nuovo l'accesso.",
      });
      return;
    }

    const trimmedValue = mappingValue.trim();
    const nextUserId = trimmedValue === "" ? null : Number(trimmedValue);
    if (trimmedValue !== "" && !Number.isFinite(nextUserId)) {
      setMappingNotice({
        tone: "error",
        message: "Seleziona un utente GAIA valido.",
      });
      return;
    }

    const currentValue =
      collaborator.application_user_id == null
        ? ""
        : String(collaborator.application_user_id);
    if (trimmedValue === currentValue) {
      setMappingNotice({ tone: "success", message: "Mapping già salvato." });
      return;
    }

    setSavingMapping(true);
    setMappingNotice(null);
    setError(null);
    try {
      const updated = await mapPresenzeCollaboratorApplicationUser(
        token,
        collaborator.id,
        nextUserId,
      );
      setCollaborator(updated);
      setAllCollaborators((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      setMappingValue(String(updated.application_user_id ?? ""));
      setMappingNotice({
        tone: "success",
        message: updated.application_user_id
          ? "Mapping GAIA salvato correttamente."
          : "Mapping GAIA rimosso correttamente.",
      });
      if (isEmbedded) {
        notifyPresenzeCollaboratorDetailUpdated();
      }
    } catch (mapError) {
      const message =
        mapError instanceof Error
          ? mapError.message
          : "Errore salvataggio mapping";
      setMappingNotice({ tone: "error", message });
      setError(message);
    } finally {
      setSavingMapping(false);
    }
  }

  async function handleSaveDailyOverride(recordId: string) {
    const token = getStoredAccessToken();
    if (!token) return;
    const form = dailyOverrides[recordId];
    if (!form) return;
    try {
      const updated = await updatePresenzeDailyRecord(token, recordId, {
        km_value: form.km_value ? Number(form.km_value) : null,
        trasferta_minutes: form.trasferta_minutes
          ? Number(form.trasferta_minutes)
          : null,
        trasferta_montano: form.trasferta_montano,
        reperibilita_unit: form.reperibilita_giornaliera ? "days" : "none",
        reperibilita_quantity: form.reperibilita_giornaliera ? 1 : null,
        override_straordinario_minutes: form.override_straordinario_minutes
          ? Number(form.override_straordinario_minutes)
          : null,
        override_mpe_minutes: form.override_mpe_minutes
          ? Number(form.override_mpe_minutes)
          : null,
        manual_note: form.manual_note.trim() || null,
      });
      setRecords((current) =>
        current.map((item) => (item.id === recordId ? updated : item)),
      );
      if (isEmbedded) {
        notifyPresenzeCollaboratorDetailUpdated();
      }
    } catch (updateError) {
      setError(
        updateError instanceof Error
          ? updateError.message
          : "Errore salvataggio rettifica giornaliera",
      );
    }
  }

  async function handleSaveContractProfile() {
    const token = getStoredAccessToken();
    if (!token || !collaborator) return;
    setError(null);
    setSavingContractProfile(true);
    try {
      let contractKind: PresenzeCollaborator["contract_kind"] = null;
      let operaiGroup: PresenzeCollaborator["operai_group"] = null;
      if (gaiaProfileCode === "GAIA_OPERAI") {
        contractKind = "operaio";
        operaiGroup = operaiGroupValue || null;
        if (!operaiGroup) {
          setError(
            "Per il profilo GAIA_OPERAI devi indicare il gruppo operaio.",
          );
          return;
        }
      } else if (gaiaProfileCode === "GAIA_IMPIEGATI") {
        contractKind = "impiegato";
      }
      await updatePresenzeCollaboratorContractProfile(token, collaborator.id, {
        contract_kind: contractKind,
        operai_group: operaiGroup,
        standard_daily_minutes: standardDailyMinutesValue.trim()
          ? Number(standardDailyMinutesValue)
          : null,
      });
      const selectedTemplateId =
        gaiaProfileCode && assignmentTemplateId
          ? Number(assignmentTemplateId)
          : null;
      const hasEquivalentAssignment =
        selectedTemplateId != null &&
        assignments.some(
          (assignment) =>
            assignment.template_id === selectedTemplateId &&
            (assignment.valid_from ?? "") === (assignmentValidFrom || "") &&
            (assignment.valid_to ?? "") === (assignmentValidTo || "") &&
            (assignment.notes ?? "") ===
              (assignmentNotes.trim() ||
                `Auto-caricato dal profilo ${gaiaProfileCode}`),
        );
      if (selectedTemplateId != null && !hasEquivalentAssignment) {
        await createPresenzeCollaboratorScheduleAssignment(
          token,
          collaborator.id,
          {
            template_id: selectedTemplateId,
            valid_from: assignmentValidFrom || null,
            valid_to: assignmentValidTo || null,
            notes:
              assignmentNotes.trim() ||
              `Auto-caricato dal profilo ${gaiaProfileCode}`,
          },
        );
      }
      await loadDetailData(token);
      if (isEmbedded) {
        notifyPresenzeCollaboratorDetailUpdated();
      }
    } catch (profileError) {
      setError(
        profileError instanceof Error
          ? profileError.message
          : "Errore salvataggio profilo contrattuale",
      );
    } finally {
      setSavingContractProfile(false);
    }
  }

  async function handleCreateAssignment() {
    const token = getStoredAccessToken();
    if (!token || !collaboratorId || !assignmentTemplateId) return;
    if (isDuplicateAssignment) {
      setError(
        "Questo template e gia assegnato al collaboratore con la stessa validita",
      );
      return;
    }
    try {
      const created = await createPresenzeCollaboratorScheduleAssignment(
        token,
        collaboratorId,
        {
          template_id: Number(assignmentTemplateId),
          valid_from: assignmentValidFrom || null,
          valid_to: assignmentValidTo || null,
          notes: assignmentNotes.trim() || null,
        },
      );
      setAssignments((current) => [created, ...current]);
      setAssignmentTemplateId("");
      setAssignmentValidFrom("");
      setAssignmentValidTo("");
      setAssignmentNotes("");
      if (isEmbedded) {
        notifyPresenzeCollaboratorDetailUpdated();
      }
    } catch (assignmentError) {
      setError(
        assignmentError instanceof Error
          ? assignmentError.message
          : "Errore creazione assegnazione",
      );
    }
  }

  async function handleDeleteAssignment(assignmentId: number) {
    const token = getStoredAccessToken();
    if (!token) return;
    try {
      await deletePresenzeScheduleAssignment(token, assignmentId);
      setAssignments((current) =>
        current.filter((item) => item.id !== assignmentId),
      );
      if (isEmbedded) {
        notifyPresenzeCollaboratorDetailUpdated();
      }
    } catch (assignmentError) {
      setError(
        assignmentError instanceof Error
          ? assignmentError.message
          : "Errore eliminazione assegnazione",
      );
    }
  }

  function jumpMonth(delta: number) {
    const nextBounds = shiftMonthBounds(dateFrom, delta);
    setDateFrom(nextBounds.start);
    setDateTo(nextBounds.end);
  }

  function resetToCurrentMonth() {
    const bounds = currentMonthBounds();
    setDateFrom(bounds.start);
    setDateTo(bounds.end);
  }

  return (
    <ProtectedPage
      title="Dettaglio collaboratore"
      description="Calendario giornaliero e riepilogo eventi."
      breadcrumb="Giornaliere"
      requiredModule="presenze"
    >
      <div className="space-y-6">
        {error ? (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        ) : null}
        {collaborator ? (
          <>
            <article className="panel-card">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0">
                  <p className="section-title">{collaborator.name}</p>
                  <p className="section-copy">
                    {[
                      `Matricola ${collaborator.employee_code}`,
                      getPresenzeCompanyLabel(
                        collaborator.company_label,
                        collaborator.company_code,
                        "",
                      )
                        ? `Azienda ${getPresenzeCompanyLabel(collaborator.company_label, collaborator.company_code, "")}`
                        : null,
                      `Nascita ${collaborator.birth_date ?? "n/d"}`,
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                </div>
                <Badge
                  variant={
                    collaborator.application_user_id ? "success" : "warning"
                  }
                >
                  {collaborator.application_user_id
                    ? "Mappato a GAIA"
                    : "Da mappare"}
                </Badge>
              </div>

              <div className="mt-4 rounded-3xl border border-slate-200 bg-gradient-to-r from-slate-50 via-white to-slate-50 px-5 py-4 shadow-sm">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                  <div className="min-w-0">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                      Periodo visualizzato
                    </p>
                    <div className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
                      <p className="text-2xl font-semibold capitalize text-slate-950">
                        {activeMonthLabel}
                      </p>
                      <span className="text-sm text-slate-500">
                        Scorri rapidamente il calendario mensile
                      </span>
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      className="inline-flex h-11 items-center rounded-2xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
                      type="button"
                      onClick={() => jumpMonth(-1)}
                    >
                      ← Precedente
                    </button>
                    <button
                      className="inline-flex h-11 items-center rounded-2xl border border-emerald-200 bg-emerald-50 px-4 text-sm font-medium text-emerald-800 transition hover:bg-emerald-100"
                      type="button"
                      onClick={resetToCurrentMonth}
                    >
                      Mese corrente
                    </button>
                    <button
                      className="inline-flex h-11 items-center rounded-2xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
                      type="button"
                      onClick={() => jumpMonth(1)}
                    >
                      Successivo →
                    </button>
                  </div>
                </div>
              </div>

              <div className="mt-6 grid gap-4 lg:grid-cols-4">
                <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-gray-400">
                    Giornaliere
                  </p>
                  <p className="mt-2 text-2xl font-semibold text-gray-900">
                    {records.length}
                  </p>
                </div>
                <div className="rounded-2xl border border-amber-100 bg-amber-50 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-amber-600">
                    Profilo contrattuale
                  </p>
                  <p className="mt-2 text-2xl font-semibold text-amber-950">
                    {formatContractKind(collaborator.contract_kind)}
                  </p>
                  <div className="mt-2">
                    <Badge
                      variant={operaiGroupBadgeVariant(
                        collaborator.operai_group,
                      )}
                    >
                      {formatOperaiGroup(collaborator.operai_group)}
                    </Badge>
                  </div>
                </div>
                <div className="rounded-2xl border border-cyan-100 bg-cyan-50 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-cyan-600">
                    Standard giornaliero
                  </p>
                  <p className="mt-2 text-2xl font-semibold text-cyan-950">
                    {formatStandardDailyMinutes(
                      collaborator.standard_daily_minutes,
                    )}
                  </p>
                </div>
                <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-gray-400">
                    Ore ordinarie
                  </p>
                  <p className="mt-2 text-2xl font-semibold text-gray-900">
                    {formatHours(totalOrdinary)}
                  </p>
                </div>
                <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-gray-400">
                    Ore assenza
                  </p>
                  <p className="mt-2 text-2xl font-semibold text-gray-900">
                    {formatHours(totalAbsence)}
                  </p>
                </div>
                <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-gray-400">
                    Ore extra
                  </p>
                  <p className="mt-2 text-2xl font-semibold text-gray-900">
                    {formatHours(totalExtra)}
                  </p>
                </div>
                <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-gray-400">
                    Voci riepilogo
                  </p>
                  <p className="mt-2 text-2xl font-semibold text-gray-900">
                    {summary.length}
                  </p>
                </div>
                <div className="rounded-2xl border border-violet-100 bg-violet-50 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-violet-500">
                    Recuperi maturati
                  </p>
                  <p className="mt-2 text-2xl font-semibold text-violet-900">
                    {totalRecoveryDays}
                  </p>
                </div>
                <div className="rounded-2xl border border-fuchsia-100 bg-fuchsia-50 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-fuchsia-500">
                    Saldo recuperi
                  </p>
                  <p className="mt-2 text-2xl font-semibold text-fuchsia-900">
                    {totalRecoveryBalance}
                  </p>
                  <p className="mt-1 text-xs text-fuchsia-700">
                    Fruiti {totalRecoveryUsed}
                  </p>
                </div>
              </div>
            </article>

            {canEdit ? (
              <article className="panel-card">
                <div className="mb-4">
                  <p className="section-title">Profilo GAIA e template orari</p>
                  <p className="section-copy">
                    Gestisci in un unico punto il profilo GAIA, il gruppo operai
                    e il template orario assegnato al collaboratore.
                  </p>
                  {isDuplicateAssignment ? (
                    <p className="mt-2 text-sm text-amber-700">
                      Questo template e gia presente con la stessa validita: non
                      puo essere inserito due volte.
                    </p>
                  ) : null}
                </div>
                <div className="mb-4 grid gap-4 rounded-2xl border border-amber-100 bg-amber-50 p-4 lg:grid-cols-[1fr_1fr_180px_auto]">
                  <label className="block text-sm font-medium text-gray-700">
                    Profilo GAIA
                    <select
                      className="form-control mt-1"
                      value={gaiaProfileCode}
                      onChange={(event) =>
                        setGaiaProfileCode(
                          event.target.value as GaiaProfileCode,
                        )
                      }
                    >
                      <option value="">Non impostato</option>
                      {effectiveGaiaProfiles.map((profile) => (
                        <option
                          key={profile.profile_code}
                          value={profile.profile_code}
                        >
                          {profile.profile_code} · {profile.profile_label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block text-sm font-medium text-gray-700">
                    Gruppo operai
                    <select
                      className="form-control mt-1"
                      value={operaiGroupValue}
                      onChange={(event) =>
                        setOperaiGroupValue(
                          event.target.value as typeof operaiGroupValue,
                        )
                      }
                      disabled={gaiaProfileCode !== "GAIA_OPERAI"}
                    >
                      <option value="">Non impostato</option>
                      <option value="agrario">Agrario</option>
                      <option value="catasto_magazzino">
                        Catasto / magazzino
                      </option>
                    </select>
                  </label>
                  <label className="block text-sm font-medium text-gray-700">
                    Standard giornaliero (minuti)
                    <input
                      className="form-control mt-1"
                      inputMode="numeric"
                      placeholder={
                        gaiaProfileCode === "GAIA_IMPIEGATI" ? "385" : "420"
                      }
                      value={standardDailyMinutesValue}
                      onChange={(event) =>
                        setStandardDailyMinutesValue(event.target.value)
                      }
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      Esempio: `420` = `7 ore` di orario ordinario teorico.
                    </p>
                  </label>
                  <div className="flex items-end">
                    <button
                      className="btn-primary w-full"
                      type="button"
                      onClick={() => void handleSaveContractProfile()}
                      disabled={savingContractProfile}
                    >
                      {savingContractProfile
                        ? "Salvataggio..."
                        : "Salva profilo GAIA"}
                    </button>
                  </div>
                  {selectedGaiaProfile ? (
                    <p className="text-xs text-amber-900 lg:col-span-4">
                      {selectedGaiaProfile.description}
                    </p>
                  ) : null}
                </div>
                <div className="grid gap-4 lg:grid-cols-[1.2fr_repeat(2,180px)_1fr_auto]">
                  <label className="block text-sm font-medium text-gray-700">
                    Template
                    <select
                      className="form-control mt-1"
                      value={assignmentTemplateId}
                      onChange={(event) =>
                        setAssignmentTemplateId(event.target.value)
                      }
                    >
                      <option value="">Seleziona template</option>
                      {assignableTemplatesForProfile.map((template) => (
                        <option key={template.id} value={template.id}>
                          {template.code} · {template.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block text-sm font-medium text-gray-700">
                    Dal
                    <input
                      className="form-control mt-1"
                      type="date"
                      value={assignmentValidFrom}
                      onChange={(event) =>
                        setAssignmentValidFrom(event.target.value)
                      }
                    />
                  </label>
                  <label className="block text-sm font-medium text-gray-700">
                    Al
                    <input
                      className="form-control mt-1"
                      type="date"
                      value={assignmentValidTo}
                      onChange={(event) =>
                        setAssignmentValidTo(event.target.value)
                      }
                    />
                  </label>
                  <label className="block text-sm font-medium text-gray-700">
                    Note
                    <input
                      className="form-control mt-1"
                      value={assignmentNotes}
                      onChange={(event) =>
                        setAssignmentNotes(event.target.value)
                      }
                    />
                  </label>
                  <div className="flex items-end">
                    <button
                      className="btn-primary w-full"
                      type="button"
                      onClick={() => void handleCreateAssignment()}
                      disabled={!assignmentTemplateId || isDuplicateAssignment}
                    >
                      Aggiungi
                    </button>
                  </div>
                </div>
                <div className="mt-4 space-y-3">
                  {assignments.map((assignment) => {
                    const inazCodes = uniqueTemplateInazCodes(
                      assignment.template,
                    );
                    return (
                      <div
                        key={assignment.id}
                        className="flex flex-col gap-3 rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 lg:flex-row lg:items-start lg:justify-between"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="font-medium text-gray-900">
                            {templateDisplayTitle(assignment.template)}
                          </p>
                          <p className="text-xs text-gray-500">
                            Template GAIA{" "}
                            {assignment.template?.code ??
                              `#${assignment.template_id}`}{" "}
                            · Validita {assignment.valid_from ?? "subito"} /{" "}
                            {assignment.valid_to ?? "aperta"}
                          </p>
                          {assignment.notes ? (
                            <p className="mt-1 text-xs text-gray-500">
                              Note assegnazione: {assignment.notes}
                            </p>
                          ) : null}
                          {inazCodes.length > 0 ? (
                            <details className="mt-3 rounded-xl border border-white bg-white px-3 py-2 text-sm text-gray-700">
                              <summary className="cursor-pointer font-medium text-gray-900">
                                Codici INAZ inclusi nel template GAIA
                              </summary>
                              <div className="mt-2 flex flex-wrap gap-2">
                                {inazCodes.map((code) => (
                                  <span
                                    key={code}
                                    className="rounded-full bg-gray-100 px-2.5 py-1 text-xs text-gray-700"
                                  >
                                    {code}
                                  </span>
                                ))}
                              </div>
                            </details>
                          ) : null}
                        </div>
                        <button
                          className="btn-secondary"
                          type="button"
                          onClick={() =>
                            void handleDeleteAssignment(assignment.id)
                          }
                        >
                          Elimina
                        </button>
                      </div>
                    );
                  })}
                  {assignments.length === 0 ? (
                    <p className="text-sm text-gray-500">
                      Nessuna assegnazione template presente.
                    </p>
                  ) : null}
                </div>
              </article>
            ) : null}

            <article className="panel-card">
              <div className="mb-4 flex gap-2">
                <button
                  className={
                    tab === "calendar" ? "btn-primary" : "btn-secondary"
                  }
                  type="button"
                  onClick={() => setTab("calendar")}
                >
                  Cartellino
                </button>
                <button
                  className={
                    tab === "summary" ? "btn-primary" : "btn-secondary"
                  }
                  type="button"
                  onClick={() => setTab("summary")}
                >
                  Riepilogo eventi
                </button>
              </div>

              {tab === "calendar" ? (
                <div className="space-y-3">
                  {records.map((record) => {
                    const daySummaryEntries = formatDetailEntries(
                      record.detail_day_summary,
                    );
                    const dayTotalEntries = formatDetailEntries(
                      record.detail_day_totals,
                    );
                    const requestPreview = firstDetailPreview(
                      record.detail_requests,
                    );
                    const anomalyPreview = firstDetailPreview(
                      record.detail_anomalies,
                    );

                    return (
                      <div
                        key={record.id}
                        className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3"
                      >
                        <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                          <div>
                            <p className="font-medium text-gray-900">
                              {record.work_date}
                            </p>
                            <p className="text-xs text-gray-500">
                              Orario{" "}
                              {record.detail_programmed_schedule ??
                                record.schedule_code ??
                                "—"}{" "}
                              · Stato{" "}
                              {record.detail_status ?? record.stato ?? "—"}
                            </p>
                          </div>
                          <div className="flex flex-wrap gap-2 text-xs">
                            <span className="rounded-full bg-white px-2.5 py-1 text-gray-700">
                              Ord. {formatHours(record.ordinary_minutes)}
                            </span>
                            <span className="rounded-full bg-white px-2.5 py-1 text-gray-700">
                              Ass. {formatHours(record.absence_minutes)}
                            </span>
                            <span className="rounded-full bg-white px-2.5 py-1 text-gray-700">
                              Straord.{" "}
                              {formatHours(record.straordinario_minutes)}
                            </span>
                            <span className="rounded-full bg-white px-2.5 py-1 text-gray-700">
                              MPE {formatHours(record.mpe_minutes)}
                            </span>
                            {requestBadgeLabel(record) ? (
                              <span className="rounded-full bg-sky-100 px-2.5 py-1 text-sky-800">
                                {requestBadgeLabel(record)}
                              </span>
                            ) : null}
                            {record.special_day ? (
                              <span className="rounded-full bg-amber-100 px-2.5 py-1 text-amber-800">
                                Giorno speciale
                              </span>
                            ) : null}
                            {recoveryBadgeLabel(record) ? (
                              <span className="rounded-full bg-violet-100 px-2.5 py-1 text-violet-800">
                                {recoveryBadgeLabel(record)}
                              </span>
                            ) : null}
                          </div>
                        </div>
                        <div className="mt-3 grid gap-3 md:grid-cols-4">
                          <div className="rounded-xl border border-white bg-white px-3 py-2 text-sm text-gray-700">
                            <span className="font-medium text-gray-900">
                              Fasce:
                            </span>{" "}
                            {record.detail_time_slots ?? "—"}
                          </div>
                          <div className="rounded-xl border border-white bg-white px-3 py-2 text-sm text-gray-700">
                            <span className="font-medium text-gray-900">
                              Tipo:
                            </span>{" "}
                            {record.detail_schedule_type ?? "—"}
                          </div>
                          <div className="rounded-xl border border-white bg-white px-3 py-2 text-sm text-gray-700">
                            <span className="font-medium text-gray-900">
                              Ore teoriche:
                            </span>{" "}
                            {record.detail_theoretical_hours ??
                              formatHours(record.teo_minutes)}
                          </div>
                          <div className="rounded-xl border border-white bg-white px-3 py-2 text-sm text-gray-700">
                            <span className="font-medium text-gray-900">
                              Ore assenza:
                            </span>{" "}
                            {record.detail_absence_hours ??
                              formatHours(record.absence_minutes)}
                          </div>
                        </div>
                        {record.request_description ||
                        record.resolved_absence_cause ||
                        record.request_status ? (
                          <div className="mt-3 grid gap-3 md:grid-cols-4">
                            <div className="rounded-xl border border-sky-100 bg-sky-50 px-3 py-2 text-sm text-sky-900">
                              <span className="font-medium text-sky-950">
                                Causale:
                              </span>{" "}
                              {formatAbsenceCause(
                                record.resolved_absence_cause,
                              )}
                            </div>
                            <div className="rounded-xl border border-sky-100 bg-sky-50 px-3 py-2 text-sm text-sky-900 md:col-span-2">
                              <span className="font-medium text-sky-950">
                                Richiesta:
                              </span>{" "}
                              {formatRequestDescription(
                                record.request_description,
                              )}
                            </div>
                            <div className="rounded-xl border border-sky-100 bg-sky-50 px-3 py-2 text-sm text-sky-900">
                              <span className="font-medium text-sky-950">
                                Stato:
                              </span>{" "}
                              {record.request_status ?? "—"}
                            </div>
                          </div>
                        ) : null}
                        <div className="mt-3 grid gap-2 md:grid-cols-3">
                          {record.punches.map((punch) => (
                            <div
                              key={punch.id}
                              className="rounded-xl border border-white bg-white px-3 py-2 text-sm text-gray-700"
                            >
                              Timbratura {punch.sequence}:{" "}
                              {punch.entry_time ?? "—"} /{" "}
                              {punch.exit_time ?? "—"}
                            </div>
                          ))}
                        </div>
                        {record.evidenze ? (
                          <p className="mt-3 text-sm text-gray-600">
                            Evidenze: {record.evidenze}
                          </p>
                        ) : null}
                        {daySummaryEntries.length > 0 ||
                        dayTotalEntries.length > 0 ? (
                          <div className="mt-3 grid gap-3 xl:grid-cols-2">
                            <details className="rounded-xl border border-white bg-white px-3 py-3 text-sm text-gray-700">
                              <summary className="cursor-pointer font-medium text-gray-900">
                                {sectionSummaryLabel("Riepilogo giornata", {
                                  count: daySummaryEntries.length,
                                })}
                              </summary>
                              <div className="mt-2 space-y-1">
                                {daySummaryEntries.length > 0 ? (
                                  daySummaryEntries.map(([label, value]) => (
                                    <div
                                      key={label}
                                      className="flex items-center justify-between gap-3"
                                    >
                                      <span>{label}</span>
                                      <span className="font-medium text-gray-900">
                                        {value}
                                      </span>
                                    </div>
                                  ))
                                ) : (
                                  <p className="text-gray-500">
                                    Nessun riepilogo disponibile.
                                  </p>
                                )}
                              </div>
                            </details>
                            <details className="rounded-xl border border-white bg-white px-3 py-3 text-sm text-gray-700">
                              <summary className="cursor-pointer font-medium text-gray-900">
                                {sectionSummaryLabel("Totali giornata", {
                                  count: dayTotalEntries.length,
                                })}
                              </summary>
                              <div className="mt-2 space-y-1">
                                {dayTotalEntries.length > 0 ? (
                                  dayTotalEntries.map(([label, value]) => (
                                    <div
                                      key={label}
                                      className="flex items-center justify-between gap-3"
                                    >
                                      <span>{label}</span>
                                      <span className="font-medium text-gray-900">
                                        {value}
                                      </span>
                                    </div>
                                  ))
                                ) : (
                                  <p className="text-gray-500">
                                    Nessun totale disponibile.
                                  </p>
                                )}
                              </div>
                            </details>
                          </div>
                        ) : null}
                        {record.detail_requests.length > 0 ||
                        record.detail_anomalies.length > 0 ||
                        record.detail_error ? (
                          <div className="mt-3 grid gap-3 xl:grid-cols-2">
                            <details className="rounded-xl border border-white bg-white px-3 py-3 text-sm text-gray-700">
                              <summary className="cursor-pointer font-medium text-gray-900">
                                {sectionSummaryLabel("Richieste", {
                                  count: record.detail_requests.length,
                                  preview:
                                    record.detail_requests.length === 1
                                      ? requestPreview
                                      : null,
                                })}
                              </summary>
                              <div className="mt-2 space-y-2">
                                {record.detail_requests.length > 0 ? (
                                  record.detail_requests.map(
                                    (request, index) => (
                                      <div
                                        key={`${record.id}-request-${index}`}
                                      >
                                        {Object.entries(request).map(
                                          ([label, value]) => (
                                            <p key={label}>
                                              <span className="font-medium text-gray-900">
                                                {label}:
                                              </span>{" "}
                                              {value}
                                            </p>
                                          ),
                                        )}
                                      </div>
                                    ),
                                  )
                                ) : (
                                  <p className="text-gray-500">
                                    Nessuna richiesta.
                                  </p>
                                )}
                              </div>
                            </details>
                            <details
                              className="rounded-xl border border-white bg-white px-3 py-3 text-sm text-gray-700"
                              open={Boolean(record.detail_error)}
                            >
                              <summary className="cursor-pointer font-medium text-gray-900">
                                {sectionSummaryLabel("Anomalie", {
                                  count: record.detail_anomalies.length,
                                  preview:
                                    record.detail_anomalies.length === 1
                                      ? anomalyPreview
                                      : null,
                                  status: record.detail_error ? "errore" : null,
                                })}
                              </summary>
                              <div className="mt-2 space-y-2">
                                {record.detail_anomalies.length > 0 ? (
                                  record.detail_anomalies.map(
                                    (anomaly, index) => (
                                      <div
                                        key={`${record.id}-anomaly-${index}`}
                                      >
                                        {Object.entries(anomaly).map(
                                          ([label, value]) => (
                                            <p key={label}>
                                              <span className="font-medium text-gray-900">
                                                {label}:
                                              </span>{" "}
                                              {value}
                                            </p>
                                          ),
                                        )}
                                      </div>
                                    ),
                                  )
                                ) : record.detail_error ? (
                                  <p className="text-red-600">
                                    {record.detail_error}
                                  </p>
                                ) : (
                                  <p className="text-gray-500">
                                    Nessuna anomalia.
                                  </p>
                                )}
                              </div>
                            </details>
                          </div>
                        ) : null}
                        {canEdit ? (
                          <div className="mt-3 rounded-xl border border-gray-100 bg-white px-3 py-3">
                            <p className="mb-3 font-medium text-gray-900">
                              Rettifiche operative
                            </p>
                            <div className="grid gap-3 lg:grid-cols-5">
                              <label className="block text-sm font-medium text-gray-700">
                                KM
                                <input
                                  className="form-control mt-1"
                                  value={
                                    dailyOverrides[record.id]?.km_value ?? ""
                                  }
                                  onChange={(event) =>
                                    setDailyOverrides((current) => ({
                                      ...current,
                                      [record.id]: {
                                        ...current[record.id],
                                        km_value: event.target.value,
                                      },
                                    }))
                                  }
                                />
                              </label>
                              <div className="block text-sm font-medium text-gray-700">
                                Trasferta
                                <input
                                  className="form-control mt-1"
                                  value={
                                    dailyOverrides[record.id]
                                      ?.trasferta_minutes ?? ""
                                  }
                                  onChange={(event) =>
                                    setDailyOverrides((current) => ({
                                      ...current,
                                      [record.id]: {
                                        ...current[record.id],
                                        trasferta_minutes: event.target.value,
                                      },
                                    }))
                                  }
                                  placeholder="Minuti"
                                />
                                <label className="mt-2 flex items-center gap-2 text-sm font-medium text-gray-700">
                                  <input
                                    type="checkbox"
                                    checked={
                                      dailyOverrides[record.id]
                                        ?.trasferta_montano ?? false
                                    }
                                    onChange={(event) =>
                                      setDailyOverrides((current) => ({
                                        ...current,
                                        [record.id]: {
                                          ...current[record.id],
                                          trasferta_montano:
                                            event.target.checked,
                                        },
                                      }))
                                    }
                                  />
                                  <span>Comune montano</span>
                                </label>
                              </div>
                              <label className="block text-sm font-medium text-gray-700">
                                Reperibilita giornaliera
                                <label className="mt-2 flex items-center gap-2 text-sm font-medium text-gray-700">
                                  <input
                                    type="checkbox"
                                    checked={
                                      dailyOverrides[record.id]
                                        ?.reperibilita_giornaliera ?? false
                                    }
                                    onChange={(event) =>
                                      setDailyOverrides((current) => ({
                                        ...current,
                                        [record.id]: {
                                          ...current[record.id],
                                          reperibilita_giornaliera:
                                            event.target.checked,
                                        },
                                      }))
                                    }
                                  />
                                  <span>
                                    Segna reperibilita per l&apos;intera
                                    giornata
                                  </span>
                                </label>
                              </label>
                              <label className="block text-sm font-medium text-gray-700">
                                Straordinario override
                                <input
                                  className="form-control mt-1"
                                  value={
                                    dailyOverrides[record.id]
                                      ?.override_straordinario_minutes ?? ""
                                  }
                                  onChange={(event) =>
                                    setDailyOverrides((current) => ({
                                      ...current,
                                      [record.id]: {
                                        ...current[record.id],
                                        override_straordinario_minutes:
                                          event.target.value,
                                      },
                                    }))
                                  }
                                />
                              </label>
                              <label className="block text-sm font-medium text-gray-700">
                                MPE override
                                <input
                                  className="form-control mt-1"
                                  value={
                                    dailyOverrides[record.id]
                                      ?.override_mpe_minutes ?? ""
                                  }
                                  onChange={(event) =>
                                    setDailyOverrides((current) => ({
                                      ...current,
                                      [record.id]: {
                                        ...current[record.id],
                                        override_mpe_minutes:
                                          event.target.value,
                                      },
                                    }))
                                  }
                                />
                              </label>
                              <label className="block text-sm font-medium text-gray-700">
                                Note
                                <input
                                  className="form-control mt-1"
                                  value={
                                    dailyOverrides[record.id]?.manual_note ?? ""
                                  }
                                  onChange={(event) =>
                                    setDailyOverrides((current) => ({
                                      ...current,
                                      [record.id]: {
                                        ...current[record.id],
                                        manual_note: event.target.value,
                                      },
                                    }))
                                  }
                                />
                              </label>
                            </div>
                            <div className="mt-3 flex flex-wrap items-center gap-3">
                              <span className="text-xs text-gray-500">
                                Effettivo extra:{" "}
                                {formatHours(record.effective_extra_minutes)}
                              </span>
                              {record.grants_recovery_day ? (
                                <span className="text-xs font-medium text-violet-700">
                                  Recupero maturato:{" "}
                                  {record.recovery_day_credit} giorno
                                </span>
                              ) : null}
                              {record.uses_recovery_day ? (
                                <span className="text-xs font-medium text-fuchsia-700">
                                  Recupero fruito: {record.recovery_day_debit}{" "}
                                  giorno
                                </span>
                              ) : null}
                              <button
                                className="btn-primary"
                                type="button"
                                onClick={() =>
                                  void handleSaveDailyOverride(record.id)
                                }
                              >
                                Salva rettifiche
                              </button>
                            </div>
                          </div>
                        ) : null}
                      </div>
                    );
                  })}
                  {records.length === 0 ? (
                    <p className="text-sm text-gray-500">
                      Nessuna giornaliera nel periodo selezionato.
                    </p>
                  ) : null}
                </div>
              ) : (
                <div className="space-y-3">
                  {summary.map((item) => (
                    <div
                      key={item.id}
                      className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3"
                    >
                      <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                        <div>
                          <p className="font-medium text-gray-900">
                            {item.description}
                          </p>
                          <p className="text-xs text-gray-500">
                            Codice {item.event_code ?? "—"} · Validita{" "}
                            {item.valid_from ?? "—"} / {item.valid_to ?? "—"}
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2 text-xs">
                          <span className="rounded-full bg-white px-2.5 py-1 text-gray-700">
                            Spettante {formatHours(item.spettante_minutes)}
                          </span>
                          <span className="rounded-full bg-white px-2.5 py-1 text-gray-700">
                            Fruito {formatHours(item.fruito_minutes)}
                          </span>
                          <span className="rounded-full bg-white px-2.5 py-1 text-gray-700">
                            Saldo {formatHours(item.saldo_minutes)}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                  {summary.length === 0 ? (
                    <p className="text-sm text-gray-500">
                      Nessun riepilogo eventi nel periodo selezionato.
                    </p>
                  ) : null}
                </div>
              )}
            </article>

            {canEdit ? (
              <article className="panel-card">
                <div className="mb-4">
                  <p className="section-title">Mapping GAIA -&gt; Presenze</p>
                  <p className="section-copy">
                    Seleziona l&apos;utente GAIA da collegare a questo
                    collaboratore delle giornaliere.
                  </p>
                </div>
                <div className="grid gap-4">
                  <div>
                    {suggestedMapping ? (
                      <p className="mb-2 text-sm text-emerald-700">
                        Suggerito:{" "}
                        {suggestedMapping.user.full_name?.trim() ||
                          suggestedMapping.user.username}{" "}
                        ({suggestedMapping.confidence})
                      </p>
                    ) : null}
                    <select
                      className="form-control"
                      value={mappingValue}
                      onChange={(event) => {
                        setMappingValue(event.target.value);
                        setMappingNotice(null);
                      }}
                    >
                      <option value="">Nessun mapping</option>
                      {mappingUsers.map((user) => (
                        <option key={user.id} value={user.id}>
                          {user.username} · {user.email}
                        </option>
                      ))}
                    </select>
                    {mappingNotice ? (
                      <p
                        className={`mt-2 text-sm ${mappingNotice.tone === "success" ? "text-emerald-700" : "text-red-700"}`}
                        role={
                          mappingNotice.tone === "success" ? "status" : "alert"
                        }
                      >
                        {mappingNotice.message}
                      </p>
                    ) : null}
                    <button
                      className="btn-primary mt-3 w-full disabled:cursor-not-allowed disabled:opacity-60 lg:ml-auto lg:flex lg:w-auto"
                      type="button"
                      disabled={savingMapping}
                      onClick={() => void handleSaveMapping()}
                    >
                      {savingMapping ? "Salvataggio..." : "Salva collegamento"}
                    </button>
                  </div>
                </div>
              </article>
            ) : null}
          </>
        ) : (
          <p className="text-sm text-gray-500">
            Caricamento dettaglio collaboratore...
          </p>
        )}
      </div>
    </ProtectedPage>
  );
}
