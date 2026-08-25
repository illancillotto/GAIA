"use client";

import { FormEvent, Suspense, useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceMiniStat,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { RuoloModulePage } from "@/components/ruolo/module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon, LockIcon, SearchIcon } from "@/components/ui/icons";
import { getStoredAccessToken } from "@/lib/auth";
import { createCapacitasInCassSyncJob, getCurrentUser } from "@/lib/api";
import { RuoloTributiFallback } from "./fallback";
import {
  EMPTY_CALCULATION_POLICY_FORM,
  calculationPolicyAnnualityYears,
  calculationPolicyFormFromPolicy,
  calculationPolicyPayload,
  formatPolicyBollettino,
  optionalDate,
  parseOptionalYear,
  policyBonarioDueDate,
  policyNameForAnnuality,
  type CalculationPolicyFormState,
} from "./calculation-policy-form";
import { PolicyAnnualityCard, PolicyBollettinoFields } from "./policy-bollettino-fields";
import { listAllReminderCandidatesForYear, reminderBatchTaxCodes } from "./reminder-candidates";
import { parseNoticeAmount } from "@/lib/utenze-payment-notices-summary";
import {
  addTributiNote,
  createTributiCalculationPolicy,
  createTributiReminderBatch,
  createTributiPayment,
  createTributiYearManager,
  deleteTributiCalculationPolicy,
  deleteTributiYearManager,
  downloadTributiReminderDocument,
  fetchTributiEuribor6mRate,
  getTributiAvviso,
  getTributiSummary,
  listTributiCalculationPolicies,
  listTributiAvvisi,
  listTributiYearManagers,
  updateTributiCalculationPolicy,
  updateTributiAvvisoStatus,
  updateTributiYearManager,
} from "@/lib/ruolo-api";
import type {
  RuoloTributiAvvisoDetailResponse,
  RuoloTributiAvvisoListItemResponse,
  RuoloTributiCalculationPolicyResponse,
  RuoloTributiReminderBatchItemResponse,
  RuoloTributiReminderBatchResponse,
  RuoloTributiReminderCandidateResponse,
  RuoloTributiPaymentStatus,
  RuoloTributiSummaryResponse,
  RuoloTributiYearManagerResponse,
  RuoloTributiWorkflowStatus,
} from "@/types/ruolo";
import type { CurrentUser } from "@/types/api";

const PAGE_SIZE = 25;
const FILTER_AUTOSUBMIT_DELAY_MS = 350;
const DEFAULT_MANAGER_KEY = "gaia";
const REMINDER_MIN_YEAR = 2022;
const GAIA_REMINDER_TEMPLATE_PATH = "__gaia_proposal__";
const DEFAULT_REMINDER_TEMPLATE_LABEL = "Template GAIA con bollettino postale e partitario allegato";
const REMINDER_PREVIEW_DESKTOP_ZOOM = 125;
const REMINDER_PREVIEW_MOBILE_ZOOM = 60;
const REMINDER_PREVIEW_MOBILE_BREAKPOINT_PX = 640;
const REMINDER_PREVIEW_TEMPLATES = [
  { key: "gaia", label: "Template GAIA", templatePath: GAIA_REMINDER_TEMPLATE_PATH },
] as const;
const EMPTY_TRIBUTI_SUMMARY: RuoloTributiSummaryResponse = {
  to_send_count: 0,
  sent_count: 0,
  pec_count: 0,
  raccomandata_count: 0,
  total_count: 0,
  total_amount: 0,
  pec_amount: 0,
  raccomandata_amount: 0,
  raccomandata_source_available: false,
  summary_partial: false,
  summary_scan_limit: null,
  summary_scanned_count: 0,
};
const EMPTY_YEAR_MANAGER_FORM = {
  manager_key: "",
  manager_label: "",
  year_from: "",
  year_to: "",
  calculation_policy: "external",
  is_active: true,
  notes: "",
};
const INTEREST_START_MODE_LABELS: Record<RuoloTributiCalculationPolicyResponse["interest_start_mode"], string> = {
  fixed_date: "Data fissa policy",
  notification_date: "PEC/raccomandata",
};

const INTEREST_START_SOURCE_LABELS: Record<string, string> = {
  pec_accepted_at: "Invio PEC",
  pec_delivered_at: "Consegna PEC",
  registered_mail_received_at: "Ricezione raccomandata",
  policy_fixed_date: "Data fissa policy",
  policy_fallback_date: "Fallback policy",
  policy_min_date: "Data minima policy",
};

const PAYMENT_STATUS_LABELS: Record<RuoloTributiPaymentStatus, string> = {
  unpaid: "Non pagato",
  partial: "Parziale",
  paid: "Pagato",
  overpaid: "Eccedenza",
  to_review: "Da verificare",
};

const WORKFLOW_STATUS_OPTIONS: Array<{ value: RuoloTributiWorkflowStatus; label: string }> = [
  { value: "moroso", label: "Moroso" },
  { value: "contestato", label: "Contestato" },
  { value: "sospeso", label: "Sospeso" },
  { value: "annullato", label: "Annullato" },
  { value: "non_dovuto", label: "Non dovuto" },
  { value: "rateizzato", label: "Rateizzato" },
];

function canManageTributiRules(user: CurrentUser | null): boolean {
  return user?.role === "admin" || user?.role === "super_admin";
}

function formatEuro(value: number | null | undefined): string {
  if (value == null) return "-";
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(value);
}

function displayTributiNoticeCode(item: Pick<RuoloTributiAvvisoListItemResponse, "codice_cnc" | "capacitas_avviso_code">): string {
  return item.capacitas_avviso_code || item.codice_cnc;
}

function buildIncassRateizationInsight(detail: RuoloTributiAvvisoDetailResponse | null) {
  const incassNotice = detail?.incass_notice;
  const rateizedAmount = parseNoticeAmount(incassNotice?.importo_rateizzato);
  if (rateizedAmount == null || rateizedAmount <= 0) {
    return null;
  }
  const issuedAmount = parseNoticeAmount(incassNotice?.importo_carico);
  const paidAmount = parseNoticeAmount(incassNotice?.importo_riscosso);
  const residualAmount = parseNoticeAmount(incassNotice?.importo_residuo);
  const feeAmount = incassNotice?.rateization_fee_amount ?? (issuedAmount == null ? null : Math.max(rateizedAmount - issuedAmount, 0));
  return {
    issuedAmount,
    rateizedAmount,
    paidAmount: paidAmount == null ? null : Math.abs(paidAmount),
    residualAmount: residualAmount == null ? null : Math.abs(residualAmount),
    feeAmount,
    sourceNoticeId: incassNotice?.source_notice_id ?? detail?.capacitas_avviso_code ?? null,
    statusLabel: incassNotice?.stato_label ?? null,
  };
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  return new Intl.DateTimeFormat("it-IT", { dateStyle: "short" }).format(new Date(value));
}

function effectivePolicyInterestRatePercent(policy: RuoloTributiCalculationPolicyResponse): number {
  return policy.effective_interest_rate_percent ?? ((policy.euribor_6m_rate_percent ?? 0) + (policy.interest_rate_percent ?? 0));
}

function formatDeliveryDate(value: string | null | undefined): string {
  if (!value) return "-";
  if (value.includes("/")) return value;
  return new Intl.DateTimeFormat("it-IT", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

function formatYearRange(manager: Pick<RuoloTributiYearManagerResponse, "year_from" | "year_to">): string {
  if (manager.year_from == null && manager.year_to == null) return "Tutte le annualita";
  if (manager.year_from == null) return `Fino al ${manager.year_to}`;
  if (manager.year_to == null) return `Dal ${manager.year_from}`;
  if (manager.year_from === manager.year_to) return String(manager.year_from);
  return `${manager.year_from}-${manager.year_to}`;
}

function managerYearStart(manager: Pick<RuoloTributiYearManagerResponse, "year_from">): number {
  if (manager.year_from == null) return Number.NEGATIVE_INFINITY;
  return manager.year_from;
}

function getAnnualityManagerFilterClassName(managerKey: string, selected: boolean): string {
  const palettes: Record<string, { selected: string; idle: string }> = {
    agenzia_entrate: {
      selected: "border-red-700 bg-red-700 text-white shadow-sm",
      idle: "border-red-200 bg-red-50 text-red-800 hover:border-red-300 hover:bg-red-100",
    },
    step: {
      selected: "border-orange-600 bg-orange-600 text-white shadow-sm",
      idle: "border-orange-200 bg-orange-50 text-orange-800 hover:border-orange-300 hover:bg-orange-100",
    },
    gaia: {
      selected: "border-yellow-500 bg-yellow-400 text-yellow-950 shadow-sm",
      idle: "border-yellow-200 bg-yellow-50 text-yellow-900 hover:border-yellow-300 hover:bg-yellow-100",
    },
  };
  const palette = palettes[managerKey] ?? {
    selected: "border-[#1D4E35] bg-[#1D4E35] text-white shadow-sm",
    idle: "border-[#d8dfd3] bg-white text-gray-700 hover:border-[#8CB39D] hover:bg-[#f4faf6]",
  };
  return selected ? palette.selected : palette.idle;
}

function normaliseManagerKey(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9_]+/g, "_").replace(/_+/g, "_").replace(/^_+|_+$/g, "");
}

function calculationPolicyAnnualityRows(policy: RuoloTributiCalculationPolicyResponse): { key: string; label: string }[] {
  const years = calculationPolicyAnnualityYears(policy.year_from, policy.year_to);
  if (years.length === 0) {
    return [{ key: `${policy.id}-range`, label: `Annualita ${formatYearRange(policy).toLowerCase()}` }];
  }
  return years.map((year) => ({ key: `${policy.id}-${year}`, label: `Annualita ${year}` }));
}

/* c8 ignore start -- Defensive fallbacks for malformed API payloads; normal values are covered through the UI. */
function formatPercent(value: number | null | undefined): string {
  if (value == null) return "-";
  return `${new Intl.NumberFormat("it-IT", { maximumFractionDigits: 4 }).format(value)}%`;
}

function formatInterestStartSource(value: string | null | undefined): string {
  if (!value) return "-";
  return INTEREST_START_SOURCE_LABELS[value] ?? value;
}
/* c8 ignore stop */

function getPaymentStatusClassName(status: RuoloTributiPaymentStatus): string {
  switch (status) {
    case "paid":
      return "bg-emerald-50 text-emerald-700 border-emerald-200";
    case "partial":
      return "bg-amber-50 text-amber-800 border-amber-200";
    case "overpaid":
      return "bg-sky-50 text-sky-800 border-sky-200";
    case "to_review":
      return "bg-rose-50 text-rose-700 border-rose-200";
    case "unpaid":
    default:
      return "bg-gray-100 text-gray-700 border-gray-200";
  }
}

function shouldApplyTextFilter(value: string): boolean {
  const trimmed = value.trim();
  return trimmed.length === 0 || trimmed.length >= 3;
}

function shouldApplyAnnoFilter(value: string): boolean {
  const trimmed = value.trim();
  return trimmed.length === 0 || /^\d{4}$/.test(trimmed);
}

function normaliseTaxCode(value: string | null | undefined): string {
  return (value ?? "").toUpperCase().replace(/[^A-Z0-9]/g, "");
}

function canPrepareReminder(item: Pick<RuoloTributiAvvisoListItemResponse, "reminder_enabled">): boolean {
  return item.reminder_enabled;
}

function shouldShowMissingRuleReminderAction(
  item: Pick<RuoloTributiAvvisoListItemResponse, "calculation_policy" | "calculation_policy_id" | "payment_status" | "saldo_amount" | "reminder_enabled">,
): boolean {
  return (
    !item.reminder_enabled
    && item.calculation_policy === "internal_gaia"
    && !item.calculation_policy_id
    && item.payment_status !== "paid"
    && (item.saldo_amount === null || item.saldo_amount > 0)
  );
}

function buildReminderYearOptions(nowYear = new Date().getFullYear()): number[] {
  const maxYear = Math.max(REMINDER_MIN_YEAR, nowYear - 1);
  return Array.from({ length: maxYear - REMINDER_MIN_YEAR + 1 }, (_, index) => maxYear - index);
}

function buildDefaultReminderYears(nowYear = new Date().getFullYear()): number[] {
  const years = [nowYear - 2, nowYear - 1].filter((year) => year >= REMINDER_MIN_YEAR);
  const sortedYears = [...new Set(years)].sort((left, right) => left - right);
  /* c8 ignore next -- Only used when the current year is before the supported reminder window has two past years. */
  return sortedYears.length > 0 ? sortedYears : [Math.max(REMINDER_MIN_YEAR, nowYear - 1)];
}

function mergeReminderCandidates(
  responses: RuoloTributiReminderCandidateResponse[][],
): RuoloTributiReminderCandidateResponse[] {
  const merged = new Map<string, RuoloTributiReminderCandidateResponse>();
  for (const responseItems of responses) {
    for (const item of responseItems) {
      const current = merged.get(item.codice_fiscale);
      if (!current) {
        merged.set(item.codice_fiscale, {
          ...item,
          years: [...item.years].sort((left, right) => left - right),
          annuality_managers: [...item.annuality_managers].sort(),
          avvisi: [...item.avvisi].sort((left, right) => left.anno_tributario - right.anno_tributario),
        });
        continue;
      }
      const avvisiById = new Map(current.avvisi.map((avviso) => [avviso.id, avviso]));
      for (const avviso of item.avvisi) avvisiById.set(avviso.id, avviso);
      merged.set(item.codice_fiscale, {
        ...current,
        display_name: current.display_name ?? item.display_name,
        comune: current.comune ?? item.comune,
        years: [...new Set([...current.years, ...item.years])].sort((left, right) => left - right),
        avvisi_count: avvisiById.size,
        due_amount: (current.due_amount ?? 0) + (item.due_amount ?? 0),
        paid_amount: current.paid_amount + item.paid_amount,
        saldo_amount: (current.saldo_amount ?? 0) + (item.saldo_amount ?? 0),
        subject_id: current.subject_id ?? item.subject_id,
        nas_folder_path: current.nas_folder_path ?? item.nas_folder_path,
        has_nas_folder: current.has_nas_folder || item.has_nas_folder,
        annuality_managers: [...new Set([...current.annuality_managers, ...item.annuality_managers])].sort(),
        avvisi: [...avvisiById.values()].sort((left, right) => left.anno_tributario - right.anno_tributario),
      });
    }
  }
  return [...merged.values()].sort((left, right) => {
    const leftLabel = (left.display_name ?? "").toLowerCase();
    const rightLabel = (right.display_name ?? "").toLowerCase();
    if (leftLabel !== rightLabel) return leftLabel.localeCompare(rightLabel);
    return left.codice_fiscale.localeCompare(right.codice_fiscale);
  });
}

type SubjectQuickView = {
  id: string;
  label: string | null;
};

type ReminderPreviewTemplateKey = (typeof REMINDER_PREVIEW_TEMPLATES)[number]["key"];

type ReminderPreviewDocument = {
  key: ReminderPreviewTemplateKey;
  label: string;
  item: RuoloTributiReminderBatchItemResponse;
  objectUrl: string;
  mimeType: string | null;
};

type ReminderPreviewState = {
  open: boolean;
  label: string;
  error: string | null;
};

function buildFiltersSearchParams({
  query,
  anno,
  comune,
  paymentStatus,
  workflowStatus,
  managerKey,
  openOnly,
  unlinked,
}: {
  query: string;
  anno: string;
  comune: string;
  paymentStatus: string;
  workflowStatus: string;
  managerKey: string;
  openOnly: boolean;
  unlinked: boolean;
}) {
  const qs = new URLSearchParams();
  if (query.trim()) qs.set("q", query.trim());
  if (anno.trim()) qs.set("anno", anno.trim());
  if (comune.trim()) qs.set("comune", comune.trim());
  if (paymentStatus) qs.set("payment_status", paymentStatus);
  if (workflowStatus) qs.set("workflow_status", workflowStatus);
  qs.set("manager_key", managerKey);
  if (!openOnly) qs.set("open_only", "false");
  if (unlinked) qs.set("unlinked", "true");
  qs.set("page", "1");
  return qs;
}

export default function RuoloTributiPage() {
  return (
    <Suspense fallback={<RuoloTributiFallback />}>
      <RuoloTributiPageContent />
    </Suspense>
  );
}

function RuoloTributiPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [token, setToken] = useState<string | null>(null);
  const [items, setItems] = useState<RuoloTributiAvvisoListItemResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [summary, setSummary] = useState<RuoloTributiSummaryResponse>(EMPTY_TRIBUTI_SUMMARY);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [dataRefreshKey, setDataRefreshKey] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<RuoloTributiAvvisoDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [operationError, setOperationError] = useState<string | null>(null);
  const [operationMessage, setOperationMessage] = useState<string | null>(null);
  const [incassSyncing, setIncassSyncing] = useState(false);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [wizardStep, setWizardStep] = useState<1 | 2 | 3>(1);
  const [candidateItems, setCandidateItems] = useState<RuoloTributiReminderCandidateResponse[]>([]);
  const [candidateTotal, setCandidateTotal] = useState(0);
  const [candidatesLoading, setCandidatesLoading] = useState(false);
  const [wizardError, setWizardError] = useState<string | null>(null);
  const [selectedTaxCodes, setSelectedTaxCodes] = useState<string[]>([]);
  const [selectedReminderYears, setSelectedReminderYears] = useState<number[]>(() => buildDefaultReminderYears());
  const [manualTaxCode, setManualTaxCode] = useState("");
  const [batchResult, setBatchResult] = useState<RuoloTributiReminderBatchResponse | null>(null);
  const [batchGenerating, setBatchGenerating] = useState(false);
  const [previewDocuments, setPreviewDocuments] = useState<ReminderPreviewDocument[]>([]);
  const [previewState, setPreviewState] = useState<ReminderPreviewState>({ open: false, label: "", error: null });
  const [previewGeneratingId, setPreviewGeneratingId] = useState<string | null>(null);
  const [subjectQuickView, setSubjectQuickView] = useState<SubjectQuickView | null>(null);
  const [yearManagers, setYearManagers] = useState<RuoloTributiYearManagerResponse[]>([]);
  const [yearManagersLoading, setYearManagersLoading] = useState(false);
  const [yearManagerError, setYearManagerError] = useState<string | null>(null);
  const [yearManagerMessage, setYearManagerMessage] = useState<string | null>(null);
  const [editingYearManagerId, setEditingYearManagerId] = useState<string | null>(null);
  const [yearManagerForm, setYearManagerForm] = useState(EMPTY_YEAR_MANAGER_FORM);
  const [yearManagersModalOpen, setYearManagersModalOpen] = useState(false);
  const [calculationPolicies, setCalculationPolicies] = useState<RuoloTributiCalculationPolicyResponse[]>([]);
  const [calculationPoliciesLoading, setCalculationPoliciesLoading] = useState(false);
  const [calculationPolicyError, setCalculationPolicyError] = useState<string | null>(null);
  const [calculationPolicyMessage, setCalculationPolicyMessage] = useState<string | null>(null);
  const [editingCalculationPolicyId, setEditingCalculationPolicyId] = useState<string | null>(null);
  const [calculationPolicyForm, setCalculationPolicyForm] = useState(EMPTY_CALCULATION_POLICY_FORM);
  const [calculationPoliciesModalOpen, setCalculationPoliciesModalOpen] = useState(false);
  const reminderYearOptions = buildReminderYearOptions();
  const defaultReminderYears = buildDefaultReminderYears();

  const query = searchParams.get("q")?.trim() || "";
  const anno = searchParams.get("anno")?.trim() || "";
  const comune = searchParams.get("comune")?.trim() || "";
  const paymentStatus = searchParams.get("payment_status")?.trim() || "";
  const workflowStatus = searchParams.get("workflow_status")?.trim() || "";
  const managerKey = searchParams.get("manager_key")?.trim() || DEFAULT_MANAGER_KEY;
  const openOnly = searchParams.get("open_only") !== "false";
  const unlinked = searchParams.get("unlinked") === "true";
  const page = Math.max(1, Number(searchParams.get("page") ?? 1));

  const [filterQuery, setFilterQuery] = useState(query);
  const [filterAnno, setFilterAnno] = useState(anno);
  const [filterComune, setFilterComune] = useState(comune);
  const [filterPaymentStatus, setFilterPaymentStatus] = useState(paymentStatus);
  const [filterWorkflowStatus, setFilterWorkflowStatus] = useState(workflowStatus);
  const [filterManagerKey, setFilterManagerKey] = useState(managerKey);
  const [filterOpenOnly, setFilterOpenOnly] = useState(openOnly);
  const [filterUnlinked, setFilterUnlinked] = useState(unlinked);
  const canManageRules = canManageTributiRules(currentUser);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  useEffect(() => {
    if (!token) {
      setCurrentUser(null);
      return;
    }
    let cancelled = false;
    getCurrentUser(token)
      .then((user) => {
        if (!cancelled) setCurrentUser(user);
      })
      .catch(() => {
        if (!cancelled) setCurrentUser(null);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    setFilterQuery(query);
    setFilterAnno(anno);
    setFilterComune(comune);
    setFilterPaymentStatus(paymentStatus);
    setFilterWorkflowStatus(workflowStatus);
    setFilterManagerKey(managerKey);
    setFilterOpenOnly(openOnly);
    setFilterUnlinked(unlinked);
  }, [anno, comune, managerKey, openOnly, paymentStatus, query, unlinked, workflowStatus]);

  useEffect(() => {
    if (!shouldApplyTextFilter(filterQuery) || !shouldApplyTextFilter(filterComune) || !shouldApplyAnnoFilter(filterAnno)) {
      return;
    }
    const filtersChanged =
      filterQuery.trim() !== query ||
      filterAnno.trim() !== anno ||
      filterComune.trim() !== comune ||
      filterPaymentStatus !== paymentStatus ||
      filterWorkflowStatus !== workflowStatus ||
      filterManagerKey !== managerKey ||
      filterOpenOnly !== openOnly ||
      filterUnlinked !== unlinked;

    if (!filtersChanged) return;

    const handle = window.setTimeout(() => {
      const qs = buildFiltersSearchParams({
        query: filterQuery,
        anno: filterAnno,
        comune: filterComune,
        paymentStatus: filterPaymentStatus,
        workflowStatus: filterWorkflowStatus,
        managerKey: filterManagerKey,
        openOnly: filterOpenOnly,
        unlinked: filterUnlinked,
      });
      router.replace(`/ruolo/tributi?${qs}`);
    }, FILTER_AUTOSUBMIT_DELAY_MS);

    return () => window.clearTimeout(handle);
  }, [
    filterAnno,
    filterComune,
    filterOpenOnly,
    filterManagerKey,
    filterPaymentStatus,
    filterQuery,
    filterUnlinked,
    filterWorkflowStatus,
    anno,
    comune,
    managerKey,
    openOnly,
    paymentStatus,
    query,
    router,
    unlinked,
    workflowStatus,
  ]);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setSummary(EMPTY_TRIBUTI_SUMMARY);
    const params = {
      anno: anno ? Number(anno) : undefined,
      comune: comune || undefined,
      q: query || undefined,
      payment_status: paymentStatus || undefined,
      workflow_status: workflowStatus || undefined,
      manager_key: managerKey,
      open_only: openOnly,
      unlinked,
    };
    listTributiAvvisi(token, {
      ...params,
      page,
      page_size: PAGE_SIZE,
    })
      .then((listResponse) => {
        if (cancelled) return;
        setItems(listResponse.items);
        setTotal(listResponse.total);
        setLoading(false);
        return getTributiSummary(token, params)
          .then((summaryResponse) => {
            if (!cancelled) setSummary(summaryResponse);
          })
          .catch(() => {
            /* Summary KPIs are non-blocking: the paginated list remains usable. */
          });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setItems([]);
        setTotal(0);
        setError(err instanceof Error ? err.message : "Errore caricamento tributi");
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [anno, comune, dataRefreshKey, managerKey, openOnly, page, paymentStatus, query, token, unlinked, workflowStatus]);

  useEffect(() => {
    if (!token || !selectedId) {
      setDetail(null);
      return;
    }
    setDetailLoading(true);
    setOperationError(null);
    getTributiAvviso(token, selectedId)
      .then(setDetail)
      .catch((err: unknown) => setOperationError(err instanceof Error ? err.message : "Errore dettaglio tributi"))
      .finally(() => setDetailLoading(false));
  }, [dataRefreshKey, selectedId, token]);

  useEffect(() => {
    if (!token || !wizardOpen) return;
    if (selectedReminderYears.length === 0) {
      setCandidateItems([]);
      setCandidateTotal(0);
      setSelectedTaxCodes([]);
      return;
    }
    setCandidatesLoading(true);
    setWizardError(null);
    Promise.all(
      selectedReminderYears.map((year) =>
        listAllReminderCandidatesForYear(token, {
          anno_from: year,
          anno_to: year,
          comune: comune || undefined,
          q: query || undefined,
          manager_key: managerKey,
        }),
      ),
    )
      .then((responses) => {
        const mergedCandidates = mergeReminderCandidates(responses);
        setCandidateItems(mergedCandidates);
        setCandidateTotal(mergedCandidates.length);
        setSelectedTaxCodes((current) => {
          const preserved = current.filter((taxCode) => mergedCandidates.some((item) => item.codice_fiscale === taxCode));
          if (preserved.length > 0) return preserved;
          return mergedCandidates.map((item) => item.codice_fiscale);
        });
      })
      .catch((err: unknown) => setWizardError(err instanceof Error ? err.message : "Errore caricamento utenze sollecitabili"))
      .finally(() => setCandidatesLoading(false));
  }, [comune, managerKey, query, selectedReminderYears, token, wizardOpen]);

  function refreshYearManagers(currentToken = token) {
    /* c8 ignore next -- Defensive guard: callers invoke this only after token availability. */
    if (!currentToken) return Promise.resolve();
    setYearManagersLoading(true);
    setYearManagerError(null);
    return listTributiYearManagers(currentToken)
      .then((response) => setYearManagers(response.items))
      .catch((err: unknown) => setYearManagerError(err instanceof Error ? err.message : "Errore caricamento gestori annualita"))
      .finally(() => setYearManagersLoading(false));
  }

  function refreshCalculationPolicies(currentToken = token) {
    /* c8 ignore next -- Defensive guard: callers invoke this only after token availability. */
    if (!currentToken) return Promise.resolve();
    setCalculationPoliciesLoading(true);
    setCalculationPolicyError(null);
    return listTributiCalculationPolicies(currentToken)
      .then((response) => setCalculationPolicies(response.items))
      .catch((err: unknown) => setCalculationPolicyError(err instanceof Error ? err.message : "Errore caricamento regole ruolo"))
      .finally(() => setCalculationPoliciesLoading(false));
  }

  useEffect(() => {
    if (!token) return;
    void refreshYearManagers(token);
    void refreshCalculationPolicies(token);
  }, [token]);

  useEffect(() => {
    return () => {
      previewDocuments.forEach((document) => URL.revokeObjectURL(document.objectUrl));
    };
  }, [previewDocuments]);

  function resetFilters() {
    setFilterQuery("");
    setFilterAnno("");
    setFilterComune("");
    setFilterPaymentStatus("");
    setFilterWorkflowStatus("");
    setFilterManagerKey(DEFAULT_MANAGER_KEY);
    setFilterOpenOnly(true);
    setFilterUnlinked(false);
    router.push("/ruolo/tributi?page=1");
  }

  function editYearManager(manager: RuoloTributiYearManagerResponse) {
    setEditingYearManagerId(manager.id);
    setYearManagerForm({
      manager_key: manager.manager_key,
      manager_label: manager.manager_label,
      year_from: manager.year_from == null ? "" : String(manager.year_from),
      year_to: manager.year_to == null ? "" : String(manager.year_to),
      calculation_policy: manager.calculation_policy,
      is_active: manager.is_active,
      notes: manager.notes ?? "",
    });
    setYearManagerError(null);
    setYearManagerMessage(null);
  }

  function resetYearManagerForm() {
    setEditingYearManagerId(null);
    setYearManagerForm(EMPTY_YEAR_MANAGER_FORM);
    setYearManagerError(null);
    setYearManagerMessage(null);
  }

  async function submitYearManager(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    /* c8 ignore next -- The form is usable only after token-backed page initialisation. */
    if (!token) return;
    const payload = {
      manager_key: normaliseManagerKey(yearManagerForm.manager_key),
      manager_label: yearManagerForm.manager_label.trim(),
      year_from: parseOptionalYear(yearManagerForm.year_from),
      year_to: parseOptionalYear(yearManagerForm.year_to),
      calculation_policy: normaliseManagerKey(yearManagerForm.calculation_policy) || "external",
      is_active: yearManagerForm.is_active,
      notes: yearManagerForm.notes.trim() || null,
    };
    if (!payload.manager_key || !payload.manager_label) {
      setYearManagerError("Inserisci chiave e descrizione gestore.");
      return;
    }
    setYearManagerError(null);
    setYearManagerMessage(null);
    try {
      if (editingYearManagerId) {
        await updateTributiYearManager(token, editingYearManagerId, payload);
        resetYearManagerForm();
        setYearManagerMessage("Gestore annualita aggiornato.");
      } else {
        await createTributiYearManager(token, payload);
        resetYearManagerForm();
        setYearManagerMessage("Gestore annualita creato.");
      }
      await refreshYearManagers(token);
    } catch (err) {
      setYearManagerError(err instanceof Error ? err.message : "Errore salvataggio gestore annualita");
    }
  }

  async function removeYearManager(managerId: string) {
    /* c8 ignore next -- Delete buttons are rendered only after token-backed page initialisation. */
    if (!token) return;
    setYearManagerError(null);
    setYearManagerMessage(null);
    try {
      await deleteTributiYearManager(token, managerId);
      if (editingYearManagerId === managerId) resetYearManagerForm();
      setYearManagerMessage("Gestore annualita eliminato.");
      await refreshYearManagers(token);
    } catch (err) {
      setYearManagerError(err instanceof Error ? err.message : "Errore eliminazione gestore annualita");
    }
  }

  function editCalculationPolicy(policy: RuoloTributiCalculationPolicyResponse) {
    setEditingCalculationPolicyId(policy.id);
    setCalculationPolicyForm(calculationPolicyFormFromPolicy(policy));
    setCalculationPolicyError(null);
    setCalculationPolicyMessage(null);
  }

  function resetCalculationPolicyForm() {
    setEditingCalculationPolicyId(null);
    setCalculationPolicyForm(EMPTY_CALCULATION_POLICY_FORM);
    setCalculationPolicyError(null);
    setCalculationPolicyMessage(null);
  }

  async function submitCalculationPolicy(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    /* c8 ignore next -- The form is usable only after token-backed page initialisation. */
    if (!token) return;
    const payload = calculationPolicyPayload(calculationPolicyForm);
    const annualityYears = calculationPolicyAnnualityYears(payload.year_from, payload.year_to);
    const shouldSaveOnePolicyPerAnnuality = annualityYears.length > 1;
    setCalculationPolicyError(null);
    setCalculationPolicyMessage(null);
    try {
      if (shouldSaveOnePolicyPerAnnuality) {
        for (const [index, year] of annualityYears.entries()) {
          const annualityPayload = {
            ...payload,
            name: policyNameForAnnuality(payload.name, year),
            year_from: year,
            year_to: year,
            bonario_due_date: optionalDate(calculationPolicyForm.bonario_due_dates_by_year[String(year)]),
            interest_from: optionalDate(calculationPolicyForm.interest_from_by_year[String(year)]),
          };
          if (editingCalculationPolicyId && index === 0) {
            await updateTributiCalculationPolicy(token, editingCalculationPolicyId, annualityPayload);
          } else {
            await createTributiCalculationPolicy(token, annualityPayload);
          }
        }
        resetCalculationPolicyForm();
        setCalculationPolicyMessage(`Regole ruolo salvate per ${annualityYears.length} annualita.`);
      } else if (editingCalculationPolicyId) {
        await updateTributiCalculationPolicy(token, editingCalculationPolicyId, payload);
        resetCalculationPolicyForm();
        setCalculationPolicyMessage("Regola ruolo aggiornata.");
      } else {
        await createTributiCalculationPolicy(token, payload);
        resetCalculationPolicyForm();
        setCalculationPolicyMessage("Regola ruolo creata.");
      }
      await refreshCalculationPolicies(token);
      setDataRefreshKey((current) => current + 1);
    /* c8 ignore start -- Network/API failure branch: keeps the modal usable, covered by API client tests. */
    } catch (err) {
      setCalculationPolicyError(err instanceof Error ? err.message : "Errore salvataggio regole ruolo");
    }
    /* c8 ignore stop */
  }

  async function removeCalculationPolicy(policyId: string) {
    /* c8 ignore next -- Delete buttons are rendered only after token-backed page initialisation. */
    if (!token) return;
    setCalculationPolicyError(null);
    setCalculationPolicyMessage(null);
    try {
      await deleteTributiCalculationPolicy(token, policyId);
      resetCalculationPolicyForm();
      setCalculationPolicyMessage("Regola ruolo eliminata.");
      await refreshCalculationPolicies(token);
      setDataRefreshKey((current) => current + 1);
    /* c8 ignore start -- Network/API failure branch: keeps the modal usable, covered by API client tests. */
    } catch (err) {
      setCalculationPolicyError(err instanceof Error ? err.message : "Errore eliminazione regole ruolo");
    }
    /* c8 ignore stop */
  }

  async function fetchEuriborForCalculationPolicy() {
    /* c8 ignore next -- The button is rendered only in token-backed admin state. */
    if (!token) return;
    const year = parseOptionalYear(calculationPolicyForm.year_from);
    if (year == null) {
      setCalculationPolicyError("Inserisci prima l'anno della regola per recuperare l'Euribor BCE.");
      return;
    }
    setCalculationPolicyError(null);
    try {
      const rate = await fetchTributiEuribor6mRate(token, year);
      setCalculationPolicyForm((current) => ({
        ...current,
        euribor_6m_rate_percent: String(rate.rate_percent).replace(".", ","),
        euribor_source_url: rate.source_url,
        euribor_reference_period: rate.reference_period,
        euribor_fetched_at: rate.fetched_at,
      }));
      setCalculationPolicyMessage(`Euribor 6 mesi BCE ${rate.reference_period}: ${formatPercent(rate.rate_percent)} (${rate.observations_count} rilevazioni).`);
    } catch (err) {
      setCalculationPolicyError(err instanceof Error ? err.message : "Errore recupero Euribor BCE");
    }
  }

  function setPage(nextPage: number) {
    const qs = new URLSearchParams(searchParams.toString());
    qs.set("page", String(nextPage));
    router.push(`/ruolo/tributi?${qs}`);
  }

  function selectManagerFilter(nextManagerKey: string) {
    setFilterManagerKey(nextManagerKey);
  }

  function refreshSelected() {
    /* c8 ignore next -- Defensive guard: UI actions expose refresh only after token and selection exist. */
    if (!selectedId || !token) return;
    return getTributiAvviso(token, selectedId).then(setDetail);
  }

  async function submitPayment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    /* c8 ignore next -- Forms are rendered only when both token-backed detail and selection are available. */
    if (!token || !detail) return;
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const amount = Number(String(form.get("amount")).replace(",", "."));
    if (!Number.isFinite(amount) || amount <= 0) {
      setOperationError("Inserisci un importo pagamento valido.");
      return;
    }
    setOperationError(null);
    setOperationMessage(null);
    await createTributiPayment(token, detail.id, {
      amount,
      paid_at: String(form.get("paid_at") || "") || null,
      payment_reference: String(form.get("payment_reference") || "") || null,
      payment_method: String(form.get("payment_method") || "") || null,
    });
    formElement.reset();
    await refreshSelected();
    setOperationMessage("Pagamento registrato.");
  }

  async function submitStatus(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    /* c8 ignore next -- Forms are rendered only when both token-backed detail and selection are available. */
    if (!token || !detail) return;
    const form = new FormData(event.currentTarget);
    setOperationError(null);
    setOperationMessage(null);
    await updateTributiAvvisoStatus(token, detail.id, {
      workflow_status: (String(form.get("workflow_status") || "") || null) as RuoloTributiWorkflowStatus | null,
      capacitas_url: String(form.get("capacitas_url") || "") || null,
      capacitas_avviso_code: String(form.get("capacitas_avviso_code") || "") || null,
    });
    await refreshSelected();
    setOperationMessage("Stato operativo aggiornato.");
  }

  async function submitNote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    /* c8 ignore next -- Forms are rendered only when both token-backed detail and selection are available. */
    if (!token || !detail) return;
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const body = String(form.get("body") || "").trim();
    if (!body) {
      setOperationError("Scrivi una nota prima di salvarla.");
      return;
    }
    setOperationError(null);
    setOperationMessage(null);
    await addTributiNote(token, detail.id, { body, visibility: "internal" });
    formElement.reset();
    await refreshSelected();
    setOperationMessage("Nota salvata.");
  }

  async function queueInCassSubjectSync() {
    /* c8 ignore next -- The action is rendered only after token-backed detail loading. */
    if (!token || !detail) return;
    if (!detail.subject_id) {
      setOperationError("Avviso non collegato a un soggetto GAIA: impossibile accodare una sync inCASS puntuale.");
      setOperationMessage(null);
      return;
    }
    setIncassSyncing(true);
    setOperationError(null);
    setOperationMessage(null);
    try {
      const job = await createCapacitasInCassSyncJob(token, {
        subject_ids: [detail.subject_id],
        include_details: true,
        include_partitario: true,
        include_mailing_list: false,
        download_mailing_receipts: false,
        continue_on_error: true,
        throttle_ms: 250,
      });
      setOperationMessage(`Sync inCASS puntuale accodata sul soggetto collegato. Job #${job.id}.`);
    } catch (err: unknown) {
      setOperationError(err instanceof Error ? err.message : "Errore accodamento sync inCASS");
    } finally {
      setIncassSyncing(false);
    }
  }

  function closeDetailModal() {
    setSelectedId(null);
    setDetail(null);
    setOperationError(null);
    setOperationMessage(null);
    setIncassSyncing(false);
  }

  function openReminderWizard() {
    setWizardOpen(true);
    setWizardStep(1);
    setWizardError(null);
    setBatchResult(null);
    resetReminderWizardSelection();
  }

  function closeReminderWizard() {
    setWizardOpen(false);
    setWizardStep(1);
    setWizardError(null);
    setBatchResult(null);
    resetReminderWizardSelection();
  }

  function resetReminderWizardSelection() {
    setSelectedTaxCodes([]);
    setManualTaxCode("");
    setSelectedReminderYears(defaultReminderYears);
  }

  function toggleTaxCode(taxCode: string) {
    setSelectedTaxCodes((current) =>
      current.includes(taxCode) ? current.filter((value) => value !== taxCode) : [...current, taxCode],
    );
  }

  function addManualTaxCode() {
    const taxCode = manualTaxCode.toUpperCase().replace(/[^A-Z0-9]/g, "");
    if (!taxCode) return;
    setSelectedTaxCodes((current) => (current.includes(taxCode) ? current : [...current, taxCode]));
    setManualTaxCode("");
  }

  function toggleReminderYear(year: number) {
    setSelectedReminderYears((current) =>
      current.includes(year) ? current.filter((value) => value !== year) : [...current, year].sort((left, right) => left - right),
    );
  }

  async function generateReminderBatch() {
    /* c8 ignore next -- Defensive guard: wizard actions are not reachable before the token is loaded. */
    if (!token) return;
    /* c8 ignore next 3 -- Defensive guard: the wizard disables progression when no tax code is selected. */
    if (selectedTaxCodes.length === 0) {
      setWizardError("Seleziona almeno una utenza o aggiungi un codice fiscale manualmente.");
      return;
    }
    if (selectedReminderYears.length === 0) {
      setWizardError("Seleziona almeno una annualita da includere nel nuovo avviso.");
      return;
    }
    setBatchGenerating(true);
    setWizardError(null);
    try {
      const result = await createTributiReminderBatch(token, {
        title: `Solleciti tributi ${new Date().toLocaleDateString("it-IT")}`,
        codice_fiscale: reminderBatchTaxCodes(candidateItems, selectedTaxCodes),
        filters: {
          anno_from: Math.min(...selectedReminderYears),
          anno_to: Math.max(...selectedReminderYears),
          years: selectedReminderYears,
          comune: comune || null,
          q: query || null,
          manager_key: managerKey,
        },
        template_path: GAIA_REMINDER_TEMPLATE_PATH,
        notes: "Batch generato da wizard tributi GAIA.",
      });
      setBatchResult(result);
      setWizardStep(3);
    } catch (err) {
      setWizardError(err instanceof Error ? err.message : "Errore generazione batch solleciti");
    } finally {
      setBatchGenerating(false);
    }
  }

  function closeReminderPreview() {
    previewDocuments.forEach((document) => URL.revokeObjectURL(document.objectUrl));
    setPreviewDocuments([]);
    setPreviewState({ open: false, label: "", error: null });
  }

  function openSubjectQuickView(
    item: Pick<RuoloTributiAvvisoListItemResponse, "subject_id" | "display_name" | "nominativo_raw" | "codice_fiscale_raw">,
  ) {
    /* c8 ignore next -- Orphan avvisi render a disabled subject button; this guard keeps the callback defensive. */
    if (!item.subject_id) return;
    setSubjectQuickView({
      id: item.subject_id,
      label: item.display_name ?? item.nominativo_raw ?? item.codice_fiscale_raw,
    });
  }

  async function prepareReminderPreview(item: RuoloTributiAvvisoListItemResponse) {
    /* c8 ignore next -- The action is hidden for non-sollecitabile rows; this keeps direct calls safe. */
    if (!canPrepareReminder(item)) return;
    /* c8 ignore next -- Quick actions are rendered only after the token-backed list is loaded. */
    if (!token) return;
    const taxCode = normaliseTaxCode(item.codice_fiscale_raw);
    if (!taxCode) {
      setOperationError("Codice fiscale/P.IVA mancante: impossibile predisporre il sollecito.");
      return;
    }
    previewDocuments.forEach((document) => URL.revokeObjectURL(document.objectUrl));
    setPreviewDocuments([]);
    setPreviewState({
      open: true,
      label: item.display_name ?? item.nominativo_raw ?? taxCode,
      error: null,
    });
    setPreviewGeneratingId(item.id);
    setOperationError(null);
    setOperationMessage(null);
    const nextDocuments: ReminderPreviewDocument[] = [];
    const reminderYears = [item.anno_tributario];
    try {
      for (const template of REMINDER_PREVIEW_TEMPLATES) {
        const result = await createTributiReminderBatch(token, {
          title: `Sollecito tributi ${taxCode} - ${template.label}`,
          codice_fiscale: [taxCode],
          filters: {
            anno_from: item.anno_tributario,
            anno_to: item.anno_tributario,
            years: reminderYears,
            codice_fiscale: [taxCode],
            preview_only: true,
            policy_group: true,
          },
          template_path: template.templatePath,
          notes: `Preview sollecito ${template.label} generata da Elenco tributi per avviso ${item.codice_cnc}.`,
        });
        const generatedItem = result.items.find((batchItem) => batchItem.status === "generated" && batchItem.download_url) ?? result.items[0];
        if (!generatedItem?.download_url) {
          throw new Error(generatedItem?.error_detail || `PDF sollecito non disponibile per la preview ${template.label}.`);
        }
        const blob = await downloadTributiReminderDocument(token, generatedItem.download_url);
        nextDocuments.push({
          key: template.key,
          label: template.label,
          item: generatedItem,
          objectUrl: URL.createObjectURL(blob),
          mimeType: blob.type || null,
        });
      }
      previewDocuments.forEach((document) => URL.revokeObjectURL(document.objectUrl));
      setPreviewDocuments(nextDocuments);
      setPreviewState((current) => ({ ...current, open: true, error: null }));
      setOperationMessage("Avviso di sollecito predisposto.");
    } catch (err) {
      /* c8 ignore next -- Requires a future multi-template preview to fail after at least one document is created. */
      nextDocuments.forEach((document) => URL.revokeObjectURL(document.objectUrl));
      setPreviewState((current) => ({
        ...current,
        open: true,
        error: err instanceof Error ? err.message : "Errore predisposizione avviso di sollecito",
      }));
    } finally {
      setPreviewGeneratingId(null);
    }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <RuoloModulePage
      title="Tributi Ruolo"
      description="Tracciamento pagamenti, scoperti, note operative e link CapaciTas sugli avvisi a ruolo."
      breadcrumb="Tributi"
      requiredSection="ruolo.tributi.view"
      topbarActions={
        <div className="flex flex-wrap gap-2">
          <Link className="btn-secondary" href="/ruolo/tributi/import-pagamenti">
            Import pagamenti
          </Link>
          <Link className="btn-secondary" href="/ruolo/tributi/solleciti">
            Solleciti
          </Link>
          <button type="button" className="btn-primary" onClick={openReminderWizard} title="Genera batch solleciti">
            Wizard solleciti
          </button>
        </div>
      }
    >
      <>
        <div className="space-y-6">
          <ModuleWorkspaceHero
            badge={
              <>
                <LockIcon className="h-3.5 w-3.5" />
                Sezione tributi
              </>
            }
            title="Pagamenti, scoperti e solleciti partono dagli avvisi CNC."
            description="La lista include anche posizioni di anni precedenti e avvisi non collegati all'anagrafica GAIA. Usa i filtri per isolare morosi, parziali, contestati e casi da verificare."
            actions={
              <>
                <ModuleWorkspaceNoticeCard
                  title={openOnly ? "Vista scoperti attiva" : "Storico completo"}
                  description={openOnly ? "Mostra solo posizioni non completamente saldate." : "Include anche avvisi già pagati."}
                  tone={openOnly ? "warning" : "info"}
                />
                <ModuleWorkspaceNoticeCard
                  title="Wizard solleciti"
                  description="Genera un batch per codice fiscale con PDF e partitario nella cartella NAS dell'utenza."
                  tone="neutral"
                />
              </>
            }
          >
            <ModuleWorkspaceKpiRow>
              <ModuleWorkspaceKpiTile label="Da inviare" value={summary.to_send_count} hint="Avvisi aperti non ancora tracciati come inviati" variant={summary.to_send_count > 0 ? "amber" : "default"} />
              <ModuleWorkspaceKpiTile label="Avvisi inviati" value={summary.sent_count} hint="Inviati rilevati da inCASS o da fonti archivio" variant="emerald" />
              <ModuleWorkspaceKpiTile label="Via PEC" value={summary.pec_count} hint="Avvisi con spedizione PEC rilevata in inCASS" variant="emerald" />
              <ModuleWorkspaceKpiTile label="Via raccomandata" value={summary.raccomandata_count} hint={summary.raccomandata_source_available ? "Avvisi tracciati da archivio raccomandate" : "In attesa del file Excel raccomandate"} />
              <ModuleWorkspaceKpiTile
                label="Totale avvisi"
                value={formatEuro(summary.total_amount)}
                hint={
                  summary.summary_partial
                    ? `${summary.total_count} avvisi su ${summary.summary_scanned_count} righe analizzate: KPI parziale per limite ${summary.summary_scan_limit}`
                    : `${summary.total_count} avvisi nel perimetro corrente`
                }
                variant={summary.summary_partial ? "amber" : "default"}
              />
              <ModuleWorkspaceKpiTile label="Totale via PEC" value={formatEuro(summary.pec_amount)} hint={`${summary.pec_count} avvisi inviati via PEC`} variant="emerald" />
              <ModuleWorkspaceKpiTile label="Totale via raccomandata" value={formatEuro(summary.raccomandata_amount)} hint={summary.raccomandata_source_available ? `${summary.raccomandata_count} avvisi inviati via raccomandata` : "Importi non disponibili finche manca l'Excel"} />
            </ModuleWorkspaceKpiRow>
          </ModuleWorkspaceHero>

          {!selectedId && operationError ? (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">{operationError}</div>
          ) : null}
          {!selectedId && operationMessage ? (
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700">{operationMessage}</div>
          ) : null}

          <section className="panel-card">
            <div className="mb-4">
              <p className="section-title">Filtri tributi</p>
              <p className="section-copy">Cerca per nominativo, CF/P.IVA, codice CNC, codice utenza, comune o anno tributario.</p>
            </div>
            <div className="grid gap-3 lg:grid-cols-[minmax(0,1.4fr),120px,160px,160px]">
              <label className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3 shadow-sm">
                <SearchIcon className="h-5 w-5 text-gray-400" />
                <input
                  type="search"
                  placeholder="Rossi, CNC, utenza, comune..."
                  value={filterQuery}
                  onChange={(event) => setFilterQuery(event.target.value)}
                  className="w-full border-0 bg-transparent text-sm outline-none"
                />
              </label>
              <input
                type="text"
                inputMode="numeric"
                maxLength={4}
                pattern="[0-9]{4}"
                placeholder="Anno completo"
                value={filterAnno}
                onChange={(event) => setFilterAnno(event.target.value.replace(/\D/g, "").slice(0, 4))}
                className="rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm shadow-sm outline-none"
              />
              <input
                type="text"
                placeholder="Comune"
                value={filterComune}
                onChange={(event) => setFilterComune(event.target.value)}
                className="rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm shadow-sm outline-none"
              />
              <select
                value={filterPaymentStatus}
                onChange={(event) => setFilterPaymentStatus(event.target.value)}
                className="rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm shadow-sm outline-none"
              >
                <option value="">Tutti gli stati</option>
                {Object.entries(PAYMENT_STATUS_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <select
                value={filterWorkflowStatus}
                onChange={(event) => setFilterWorkflowStatus(event.target.value)}
                className="rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm shadow-sm outline-none"
              >
                <option value="">Tutti workflow</option>
                {WORKFLOW_STATUS_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <label className="flex items-center gap-2 rounded-xl border border-[#e3e9e0] bg-[#fbfcfb] px-4 py-2.5 text-sm text-gray-700">
                <input type="checkbox" checked={filterOpenOnly} onChange={(event) => setFilterOpenOnly(event.target.checked)} />
                Solo scoperti
              </label>
              <label className="flex items-center gap-2 rounded-xl border border-[#e3e9e0] bg-[#fbfcfb] px-4 py-2.5 text-sm text-gray-700">
                <input type="checkbox" checked={filterUnlinked} onChange={(event) => setFilterUnlinked(event.target.checked)} />
                Non collegati
              </label>
              <button type="button" className="btn-secondary" onClick={resetFilters}>
                Reset
              </button>
              <span className="text-xs text-gray-500">Ricerca automatica da 3 caratteri; anno solo a 4 cifre.</span>
            </div>
          </section>

          <div className="grid gap-4 xl:grid-cols-2 xl:items-stretch">
            <YearManagersPanel
              managers={yearManagers}
              loading={yearManagersLoading}
              error={yearManagerError}
              message={yearManagerMessage}
              editingId={editingYearManagerId}
              form={yearManagerForm}
              modalOpen={yearManagersModalOpen}
              canManage={canManageRules}
              onFormChange={setYearManagerForm}
              onSubmit={submitYearManager}
              onEdit={editYearManager}
              onDelete={removeYearManager}
              onCancel={resetYearManagerForm}
              onOpen={() => setYearManagersModalOpen(true)}
              onClose={() => setYearManagersModalOpen(false)}
            />

            <CalculationPoliciesPanel
              policies={calculationPolicies}
              loading={calculationPoliciesLoading}
              error={calculationPolicyError}
              message={calculationPolicyMessage}
              editingId={editingCalculationPolicyId}
              form={calculationPolicyForm}
              modalOpen={calculationPoliciesModalOpen}
              canManage={canManageRules}
              onFormChange={setCalculationPolicyForm}
              onSubmit={submitCalculationPolicy}
              onEdit={editCalculationPolicy}
              onDelete={removeCalculationPolicy}
              onCancel={resetCalculationPolicyForm}
              onFetchEuribor={fetchEuriborForCalculationPolicy}
              onOpen={() => setCalculationPoliciesModalOpen(true)}
              onClose={() => setCalculationPoliciesModalOpen(false)}
            />
          </div>

          <section id="tributi-elenco" className="scroll-mt-6 rounded-[28px] border border-[#d8dfd3] bg-white shadow-panel">
            <div className="border-b border-[#edf1eb] px-6 py-5">
              <p className="inline-flex items-center gap-2 rounded-full bg-[#e8f2ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
                <DocumentIcon className="h-3.5 w-3.5" />
                Elenco tributi
              </p>
              <p className="mt-3 text-lg font-semibold text-gray-900">Avvisi e saldo pagamento.</p>
              <AnnualityManagerQuickFilters
                managers={yearManagers}
                selectedManagerKey={filterManagerKey}
                onSelect={selectManagerFilter}
              />
            </div>
            <div className="p-6">
              {error ? (
                <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
              ) : loading ? (
                <p className="text-sm text-gray-400">Caricamento tributi...</p>
              ) : items.length === 0 ? (
                <EmptyState icon={DocumentIcon} title="Nessuna posizione trovata" description="Modifica i filtri o disattiva la vista solo scoperti." />
              ) : (
                <div className="space-y-3">
                  {items.map((item) => {
                    const reminderBusy = previewGeneratingId === item.id;
                    const reminderEnabled = canPrepareReminder(item);
                    const missingRuleReminderAction = shouldShowMissingRuleReminderAction(item);
                    const reminderTitle = "Predisponi e apri la preview del PDF";
                    return (
                      <article
                        key={item.id}
                        className={`grid w-full gap-3 rounded-[24px] border px-4 py-4 text-left transition hover:-translate-y-0.5 hover:shadow-sm 2xl:grid-cols-[minmax(0,1fr),minmax(390px,auto)] ${
                          selectedId === item.id ? "border-[#1D4E35] bg-[#f4faf6]" : "border-[#e6ebe5] bg-white"
                        }`}
                      >
                        <button type="button" onClick={() => setSelectedId(item.id)} className="grid min-w-0 gap-3 text-left lg:grid-cols-[minmax(0,1fr),minmax(380px,0.5fr)]">
                          <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                              <p className="truncate text-sm font-semibold text-gray-900">
                                {item.display_name ?? item.nominativo_raw ?? "Avviso senza nominativo"}
                              </p>
                              <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${getPaymentStatusClassName(item.payment_status)}`}>
                                {PAYMENT_STATUS_LABELS[item.payment_status]}
                              </span>
                              {item.workflow_status ? (
                                <span className="rounded-full bg-stone-100 px-2.5 py-1 text-xs font-semibold text-stone-700">
                                  {item.workflow_status}
                                </span>
                              ) : null}
                              {!item.is_linked ? <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700">Orfano</span> : null}
                              {item.annuality_manager_label ? (
                                <span className="rounded-full bg-[#eef7ef] px-2.5 py-1 text-xs font-semibold text-[#1D4E35]">
                                  {item.annuality_manager_label}
                                </span>
                              ) : null}
                            </div>
                            <p className="mt-1 truncate text-xs leading-5 text-gray-500">
                              Anno {item.anno_tributario} · CNC {displayTributiNoticeCode(item)} · CF/P.IVA {item.codice_fiscale_raw ?? "-"} · Utenza {item.codice_utenza ?? "-"}
                            </p>
                          </div>
                          <div className="grid grid-cols-2 gap-3 text-right text-xs sm:grid-cols-4 lg:min-w-[380px]">
                            <AmountCell label="Ruolo" value={item.importo_totale_euro} />
                            <AmountCell label="Magg./int." value={(item.surcharge_amount ?? 0) + (item.interest_amount ?? 0)} />
                            <AmountCell label="Pagato" value={item.paid_amount} />
                            <AmountCell label="Saldo agg." value={item.saldo_amount} strong />
                          </div>
                        </button>
                        <div className="grid grid-cols-[0.74fr_1.13fr_1.13fr] items-center gap-1.5 sm:flex sm:flex-wrap sm:justify-end sm:gap-2 2xl:min-w-[390px]">
                          <button type="button" className="btn-secondary min-w-0 whitespace-nowrap !px-1.5 !text-[11px] sm:!px-4 sm:!text-sm" onClick={() => setSelectedId(item.id)}>
                            Dettaglio
                          </button>
                          {item.subject_id ? (
                            <button type="button" className="btn-secondary min-w-0 whitespace-nowrap !px-1.5 !text-[11px] sm:!px-4 sm:!text-sm" onClick={() => openSubjectQuickView(item)}>
                              Dettaglio soggetto
                            </button>
                          ) : (
                            <button
                              type="button"
                              className="btn-secondary min-w-0 whitespace-nowrap !px-1.5 !text-[11px] sm:!px-4 sm:!text-sm"
                              disabled
                              title="Avviso non collegato a un soggetto GAIA"
                            >
                              Dettaglio soggetto
                            </button>
                          )}
                          {reminderEnabled ? (
                            <button
                              type="button"
                              className="btn-primary min-w-0 whitespace-nowrap !px-1.5 !text-[11px] sm:!px-4 sm:!text-sm"
                              onClick={() => prepareReminderPreview(item)}
                              disabled={reminderBusy}
                              title={reminderTitle}
                            >
                              {reminderBusy ? "Creo..." : "Avviso sollecito"}
                            </button>
                          ) : missingRuleReminderAction ? (
                            <button
                              type="button"
                              className="btn-secondary min-w-0 whitespace-nowrap !px-1.5 !text-[11px] sm:!px-4 sm:!text-sm"
                              disabled
                              title="Regola ruolo non configurata per questa annualita"
                            >
                              Avviso sollecito
                            </button>
                          ) : null}
                        </div>
                      </article>
                    );
                  })}
                </div>
              )}
              <div className="mt-6 flex items-center justify-between border-t border-gray-100 pt-4 text-sm text-gray-500">
                <button type="button" className="btn-secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                  Precedente
                </button>
                <span>Pagina {page}{totalPages ? ` di ${totalPages}` : ""}</span>
                <button type="button" className="btn-secondary" disabled={totalPages > 0 && page >= totalPages} onClick={() => setPage(page + 1)}>
                  Successiva
                </button>
              </div>
            </div>
          </section>

        </div>

        {selectedId ? (
          <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/45 px-3 py-4 backdrop-blur-sm">
            <div className="flex max-h-[96vh] w-full max-w-[1500px] flex-col overflow-hidden rounded-[24px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
              <div className="flex items-center justify-between gap-3 border-b border-gray-100 px-5 py-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Dettaglio tributo</p>
                    {detail ? (
                      <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${getPaymentStatusClassName(detail.payment_status)}`}>
                        {PAYMENT_STATUS_LABELS[detail.payment_status]}
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-0.5 truncate text-base font-semibold text-gray-900">
                    {detail?.display_name ?? detail?.nominativo_raw ?? "Avviso selezionato"}
                  </p>
                </div>
                <div className="flex shrink-0 flex-wrap justify-end gap-2">
                  {detail?.capacitas_url ? (
                    <Link className="btn-secondary" href={detail.capacitas_url} target="_blank" rel="noreferrer">
                      Apri CapaciTas
                    </Link>
                  ) : null}
                  <button type="button" className="btn-secondary" onClick={closeDetailModal}>
                    Chiudi
                  </button>
                </div>
              </div>
              <div className="overflow-y-auto bg-[#f7f9f5] p-3 md:p-4">
                <TributiDetailPanel
                  detail={detail}
                  loading={detailLoading}
                  operationError={operationError}
                  operationMessage={operationMessage}
                  onSubmitPayment={submitPayment}
                  onSubmitStatus={submitStatus}
                  onSubmitNote={submitNote}
                  onQueueInCassSubjectSync={queueInCassSubjectSync}
                  onPrepareReminder={prepareReminderPreview}
                  onOpenSubject={openSubjectQuickView}
                  reminderGenerating={detail ? previewGeneratingId === detail.id : false}
                  incassSyncing={incassSyncing}
                />
              </div>
            </div>
          </div>
        ) : null}

        {previewState.open ? (
          <ReminderPreviewModal
            documents={previewDocuments}
            error={previewState.error}
            loading={previewGeneratingId !== null}
            subjectLabel={previewState.label}
            onClose={closeReminderPreview}
          />
        ) : null}

        {subjectQuickView ? (
          <SubjectQuickViewModal subject={subjectQuickView} onClose={() => setSubjectQuickView(null)} />
        ) : null}

        {wizardOpen ? (
          <ReminderWizardModal
            candidates={candidateItems}
            candidatesLoading={candidatesLoading}
            candidateTotal={candidateTotal}
            selectedTaxCodes={selectedTaxCodes}
            selectedReminderYears={selectedReminderYears}
            reminderYearOptions={reminderYearOptions}
            manualTaxCode={manualTaxCode}
            step={wizardStep}
            error={wizardError}
            batchResult={batchResult}
            generating={batchGenerating}
            onClose={closeReminderWizard}
            onStepChange={setWizardStep}
            onToggleTaxCode={toggleTaxCode}
            onToggleReminderYear={toggleReminderYear}
            onManualTaxCodeChange={setManualTaxCode}
            onAddManualTaxCode={addManualTaxCode}
            onGenerate={generateReminderBatch}
          />
        ) : null}
      </>
    </RuoloModulePage>
  );
}

type YearManagerFormState = typeof EMPTY_YEAR_MANAGER_FORM;

function YearManagersPanel({
  managers,
  loading,
  error,
  message,
  editingId,
  form,
  modalOpen,
  canManage,
  onFormChange,
  onSubmit,
  onEdit,
  onDelete,
  onCancel,
  onOpen,
  onClose,
}: {
  managers: RuoloTributiYearManagerResponse[];
  loading: boolean;
  error: string | null;
  message: string | null;
  editingId: string | null;
  form: YearManagerFormState;
  modalOpen: boolean;
  canManage: boolean;
  onFormChange: (value: YearManagerFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onEdit: (manager: RuoloTributiYearManagerResponse) => void;
  onDelete: (managerId: string) => void;
  onCancel: () => void;
  onOpen: () => void;
  onClose: () => void;
}) {
  const activeManagers = [...managers]
    .filter((manager) => manager.is_active)
    .sort((first, second) => managerYearStart(first) - managerYearStart(second));
  const visibleManagers = canManage ? activeManagers.slice(0, 4) : activeManagers;

  return (
    <>
      <section className="h-full rounded-[24px] border border-[#d8dfd3] bg-white px-5 py-4 shadow-panel">
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr),auto]">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <p className="section-title">Gestori annualita tributo</p>
              <span className="rounded-full border border-[#cfe2b8] bg-[#f3faf5] px-3 py-1 text-xs font-semibold text-[#1D4E35]">
                {activeManagers.length} regole attive
              </span>
            </div>
            <p className="section-copy mt-1">Competenza delle annualita usata per attribuire somme dovute e filtri operativi.</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {loading ? (
                <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-500">Caricamento regole...</span>
              ) : activeManagers.length === 0 ? (
                <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800">Nessuna regola attiva</span>
              ) : (
                visibleManagers.map((manager) => (
                  <span key={manager.id} className="rounded-full bg-[#eef7ef] px-3 py-1 text-xs font-semibold text-[#1D4E35]">
                    {formatYearRange(manager)} · {manager.manager_label}
                  </span>
                ))
              )}
              {canManage && activeManagers.length > visibleManagers.length ? (
                <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-500">+{activeManagers.length - visibleManagers.length}</span>
              ) : null}
            </div>
          </div>
          <div className="flex flex-wrap items-start justify-end gap-2">
            <button
              type="button"
              className="btn-secondary disabled:cursor-not-allowed disabled:opacity-55"
              onClick={onOpen}
              disabled={!canManage}
              title={canManage ? undefined : "Gestione regole riservata agli admin"}
            >
              Gestisci regole
            </button>
          </div>
        </div>

        {error ? <div className="mt-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm font-medium text-red-700">{error}</div> : null}
        {message ? <div className="mt-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm font-medium text-emerald-700">{message}</div> : null}
      </section>

      {canManage && modalOpen ? (
        <div className="fixed inset-0 z-[90] flex items-center justify-center bg-[#0f172a]/55 px-4 py-6 backdrop-blur-sm">
          <div className="flex max-h-[94vh] w-full max-w-[1280px] flex-col overflow-hidden rounded-[30px] border border-[#d6dfd2] bg-white shadow-[0_34px_110px_rgba(15,23,42,0.32)]">
            <div className="flex flex-wrap items-start justify-between gap-4 border-b border-[#e5eadf] bg-[#203829] px-6 py-5 text-white">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#cfe2b8]">Gestori annualita tributo</p>
                <h2 className="mt-2 text-xl font-semibold">Configura competenza e policy calcolo</h2>
                <p className="mt-1 text-sm leading-6 text-white/70">I range attivi non possono sovrapporsi e sono usati per lista tributi, wizard solleciti e calcolo dovuto.</p>
              </div>
              <button type="button" className="btn-secondary border-white/20 bg-white/10 text-white hover:bg-white/20" onClick={onClose}>
                Chiudi
              </button>
            </div>

            <div className="overflow-y-auto bg-[#f8faf5] p-5">
              {error ? <div className="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">{error}</div> : null}
              {message ? <div className="mb-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700">{message}</div> : null}

              <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr),390px]">
                <div className="space-y-3">
                  {loading ? (
                    <p className="rounded-2xl bg-white px-4 py-5 text-sm text-gray-500">Caricamento gestori annualita...</p>
                  ) : managers.length === 0 ? (
                    <p className="rounded-2xl bg-white px-4 py-5 text-sm text-gray-500">Nessuna regola configurata.</p>
                  ) : (
                    managers.map((manager) => (
                      <article key={manager.id} className="grid gap-3 rounded-[22px] border border-[#e5ebe1] bg-white px-4 py-3 md:grid-cols-[minmax(0,1fr),auto]">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="font-semibold text-gray-900">{manager.manager_label}</p>
                            <span className="rounded-full bg-[#eef7ef] px-2.5 py-1 text-xs font-semibold text-[#1D4E35]">{formatYearRange(manager)}</span>
                            <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${manager.is_active ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-500"}`}>
                              {manager.is_active ? "Attivo" : "Disattivo"}
                            </span>
                          </div>
                          <p className="mt-1 text-xs text-gray-500">
                            Chiave {manager.manager_key} · policy {manager.calculation_policy}
                          </p>
                          {manager.notes ? <p className="mt-2 text-xs leading-5 text-gray-600">{manager.notes}</p> : null}
                        </div>
                        <div className="flex flex-wrap justify-end gap-2">
                          <button type="button" className="btn-secondary" onClick={() => onEdit(manager)}>
                            Modifica
                          </button>
                          <button type="button" className="btn-secondary" onClick={() => onDelete(manager.id)}>
                            Elimina
                          </button>
                        </div>
                      </article>
                    ))
                  )}
                </div>

                <form className="rounded-[24px] border border-[#e5ebe1] bg-white p-4" onSubmit={onSubmit}>
                  <p className="text-sm font-semibold text-gray-900">{editingId ? "Modifica gestore annualita" : "Nuovo gestore annualita"}</p>
                  <div className="mt-3 grid gap-2">
                    <input
                      value={form.manager_label}
                      onChange={(event) => onFormChange({ ...form, manager_label: event.target.value })}
                      placeholder="Descrizione, es. STEP"
                      className="rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[#8CB39D]"
                    />
                    <input
                      value={form.manager_key}
                      onChange={(event) => onFormChange({ ...form, manager_key: normaliseManagerKey(event.target.value) })}
                      placeholder="Chiave, es. step"
                      className="rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[#8CB39D]"
                    />
                    <div className="grid gap-2 sm:grid-cols-2">
                      <input
                        value={form.year_from}
                        onChange={(event) => onFormChange({ ...form, year_from: event.target.value.replace(/\D/g, "").slice(0, 4) })}
                        inputMode="numeric"
                        maxLength={4}
                        placeholder="Anno da, vuoto = -inf"
                        className="rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[#8CB39D]"
                      />
                      <input
                        value={form.year_to}
                        onChange={(event) => onFormChange({ ...form, year_to: event.target.value.replace(/\D/g, "").slice(0, 4) })}
                        inputMode="numeric"
                        maxLength={4}
                        placeholder="Anno a, vuoto = aperto"
                        className="rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[#8CB39D]"
                      />
                    </div>
                    <input
                      value={form.calculation_policy}
                      onChange={(event) => onFormChange({ ...form, calculation_policy: normaliseManagerKey(event.target.value) })}
                      placeholder="Policy calcolo"
                      className="rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[#8CB39D]"
                    />
                    <textarea
                      value={form.notes}
                      onChange={(event) => onFormChange({ ...form, notes: event.target.value })}
                      rows={3}
                      placeholder="Note operative"
                      className="rounded-2xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[#8CB39D]"
                    />
                    <label className="flex items-center gap-2 text-sm text-gray-700">
                      <input
                        type="checkbox"
                        checked={form.is_active}
                        onChange={(event) => onFormChange({ ...form, is_active: event.target.checked })}
                      />
                      Regola attiva
                    </label>
                  </div>
                  <div className="mt-4 flex flex-wrap justify-end gap-2">
                    {editingId ? (
                      <button type="button" className="btn-secondary" onClick={onCancel}>
                        Annulla
                      </button>
                    ) : null}
                    <button type="submit" className="btn-primary">
                      {editingId ? "Aggiorna" : "Aggiungi"}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

function CalculationPoliciesPanel({
  policies,
  loading,
  error,
  message,
  editingId,
  form,
  modalOpen,
  canManage,
  onFormChange,
  onSubmit,
  onEdit,
  onDelete,
  onCancel,
  onFetchEuribor,
  onOpen,
  onClose,
}: {
  policies: RuoloTributiCalculationPolicyResponse[];
  loading: boolean;
  error: string | null;
  message: string | null;
  editingId: string | null;
  form: CalculationPolicyFormState;
  modalOpen: boolean;
  canManage: boolean;
  onFormChange: (value: CalculationPolicyFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onEdit: (policy: RuoloTributiCalculationPolicyResponse) => void;
  onDelete: (policyId: string) => void;
  onCancel: () => void;
  onFetchEuribor: () => void;
  onOpen: () => void;
  onClose: () => void;
}) {
  const activePolicies = [...policies].filter((policy) => policy.is_active);
  const visiblePolicies = canManage ? activePolicies.slice(0, 3) : activePolicies;
  const annualityYears = calculationPolicyAnnualityYears(parseOptionalYear(form.year_from), parseOptionalYear(form.year_to));
  const shouldShowAnnualityDateFields = annualityYears.length > 1;

  return (
    <>
      <section className="h-full overflow-hidden rounded-[28px] border border-[#d7c9a8] bg-[#fffaf0] shadow-panel">
        <div className="grid gap-4 p-5 xl:grid-cols-[minmax(0,1fr),auto]">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <p className="section-title text-[#6d4215]">Regole ruolo</p>
              <span className="rounded-full border border-amber-200 bg-white px-3 py-1 text-xs font-semibold text-amber-800">
                {activePolicies.length} attive
              </span>
            </div>
            <p className="section-copy mt-1">
              Configura scadenza bonaria, maggiorazioni per annualita e decorrenza interessi da PEC/raccomandata.
            </p>
            <div className="mt-3 grid gap-2 md:grid-cols-3">
              {loading ? (
                <span className="rounded-2xl bg-white px-3 py-3 text-xs font-semibold text-gray-500">Caricamento policy...</span>
              ) : activePolicies.length === 0 ? (
                <span className="rounded-2xl bg-white px-3 py-3 text-xs font-semibold text-amber-800">Nessuna maggiorazione attiva</span>
              ) : (
                visiblePolicies.map((policy) => (
                  <article key={policy.id} className="rounded-2xl border border-amber-100 bg-white px-3 py-3">
                    <p className="truncate text-sm font-semibold text-gray-900">{policy.name}</p>
                    <p className="mt-1 text-xs text-gray-500">{formatYearRange(policy)}</p>
                    <div className="mt-2 space-y-1 text-[11px] leading-4 text-gray-600">
                      {calculationPolicyAnnualityRows(policy).map((annuality) => (
                        <p key={annuality.key}>
                          <span className="font-semibold text-gray-800">{annuality.label}</span> · scad. bonaria {formatDate(policyBonarioDueDate(policy))} · magg. dal {formatDate(policy.surcharge_from)} · int. dal {formatDate(policy.interest_from)}
                        </p>
                      ))}
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1.5 text-[11px] font-semibold">
                      <span className="rounded-full bg-amber-50 px-2 py-1 text-amber-800">Magg. {formatPercent(policy.surcharge_rate_percent)}</span>
                      <span className="rounded-full bg-sky-50 px-2 py-1 text-sky-800">Euribor {formatPercent(policy.euribor_6m_rate_percent)}</span>
                      <span className="rounded-full bg-indigo-50 px-2 py-1 text-indigo-800">Delibera {formatPercent(policy.interest_rate_percent)}</span>
                      <span className="rounded-full bg-cyan-50 px-2 py-1 text-cyan-800">Int. eff. {formatPercent(effectivePolicyInterestRatePercent(policy))}</span>
                      <span className="rounded-full bg-emerald-50 px-2 py-1 text-emerald-800">{INTEREST_START_MODE_LABELS[policy.interest_start_mode]}</span>
                      {policy.euribor_source_url ? (
                        <a href={policy.euribor_source_url} target="_blank" rel="noreferrer" className="rounded-full bg-white px-2 py-1 text-blue-700 underline decoration-blue-300">
                          Verifica BCE
                        </a>
                      ) : null}
                    </div>
                  </article>
                ))
              )}
            </div>
          </div>
          <div className="flex flex-wrap items-start justify-end gap-2">
            <button
              type="button"
              className="btn-primary bg-[#8a5a16] hover:bg-[#6f4710] disabled:cursor-not-allowed disabled:opacity-55"
              onClick={onOpen}
              disabled={!canManage}
              title={canManage ? undefined : "Gestione regole riservata agli admin"}
            >
              Gestisci regole calcolo
            </button>
          </div>
        </div>
        {error ? <div className="mx-5 mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm font-medium text-red-700">{error}</div> : null}
        {message ? <div className="mx-5 mb-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm font-medium text-emerald-700">{message}</div> : null}
      </section>

      {canManage && modalOpen ? (
        <div className="fixed inset-0 z-[90] flex items-center justify-center bg-[#1f1305]/60 px-4 py-6 backdrop-blur-sm">
          <div className="flex max-h-[94vh] w-full max-w-[1320px] flex-col overflow-hidden rounded-[30px] border border-[#e8d5af] bg-white shadow-[0_34px_110px_rgba(15,23,42,0.32)]">
            <div className="flex flex-wrap items-start justify-between gap-4 border-b border-[#eadfc9] bg-[#4b2f0e] px-6 py-5 text-white">
              <div>
	                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#f3d98f]">Regole ruolo</p>
	                <h2 className="mt-2 text-xl font-semibold">Scadenza bonaria, maggiorazioni e interessi</h2>
	                <p className="mt-1 text-sm leading-6 text-white/75">
	                  La maggiorazione scatta dopo la scadenza bonaria. Gli interessi partono dalla PEC o dalla ricezione raccomandata.
	                </p>
              </div>
              <button type="button" className="btn-secondary border-white/20 bg-white/10 text-white hover:bg-white/20" onClick={onClose}>
                Chiudi
              </button>
            </div>

            <div className="overflow-y-auto bg-[#fff9ec] p-5">
              <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr),420px]">
                <div className="space-y-3">
                  {/* c8 ignore start -- Loading/empty modal branches duplicate the compact panel state; CRUD path is covered. */}
                  {loading ? (
                    <p className="rounded-2xl bg-white px-4 py-5 text-sm text-gray-500">Caricamento policy...</p>
                  ) : policies.length === 0 ? (
	                    <p className="rounded-2xl bg-white px-4 py-5 text-sm text-gray-500">Nessuna regola ruolo configurata.</p>
                  ) : (
                    policies.map((policy) => (
                      <article key={policy.id} className="grid gap-3 rounded-[22px] border border-[#eadfc9] bg-white px-4 py-3 md:grid-cols-[minmax(0,1fr),auto]">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="font-semibold text-gray-900">{policy.name}</p>
                            <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-800">{formatYearRange(policy)}</span>
                            <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${policy.is_active ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-500"}`}>
                              {policy.is_active ? "Attiva" : "Disattiva"}
                            </span>
                          </div>
                          <p className="mt-1 text-xs text-gray-500">
                            Scadenza bonaria {formatDate(policyBonarioDueDate(policy))} · maggiorazione {formatPercent(policy.surcharge_rate_percent)} dal {formatDate(policy.surcharge_from)} · interessi effettivi {formatPercent(effectivePolicyInterestRatePercent(policy))} (Euribor {formatPercent(policy.euribor_6m_rate_percent)} + delibera {formatPercent(policy.interest_rate_percent)}) · {INTEREST_START_MODE_LABELS[policy.interest_start_mode]}
                          </p>
                          {policy.euribor_source_url ? (
                            <p className="mt-1 text-xs text-blue-700">
                              Fonte Euribor BCE {policy.euribor_reference_period ?? ""}:{" "}
                              <a href={policy.euribor_source_url} target="_blank" rel="noreferrer" className="underline decoration-blue-300">
                                verifica dato
                              </a>
                            </p>
                          ) : null}
                          <div className="mt-2 grid gap-1.5 text-xs text-gray-600 sm:grid-cols-2">
                            {calculationPolicyAnnualityRows(policy).map((annuality) => (
                              <PolicyAnnualityCard key={annuality.key} label={annuality.label} bonarioDueDate={formatDate(policyBonarioDueDate(policy))} surchargeFrom={formatDate(policy.surcharge_from)} interestFrom={formatDate(policy.interest_from)} bollettino={formatPolicyBollettino(policy)} />
                            ))}
                          </div>
                          {policy.notes ? <p className="mt-2 text-xs leading-5 text-gray-600">{policy.notes}</p> : null}
                        </div>
                        <div className="flex flex-wrap justify-end gap-2">
                          <button type="button" className="btn-secondary" onClick={() => onEdit(policy)}>
                            Modifica
                          </button>
                          <button type="button" className="btn-secondary" onClick={() => onDelete(policy.id)}>
                            Elimina
                          </button>
                        </div>
                      </article>
                    ))
                  )}
                  {/* c8 ignore stop */}
                </div>

                <form className="rounded-[24px] border border-[#eadfc9] bg-white p-4" onSubmit={onSubmit}>
	                  <p className="text-sm font-semibold text-gray-900">{editingId ? "Modifica regola" : "Nuova regola"}</p>
                  <div className="mt-3 grid gap-2">
                    <input required value={form.name} onChange={(event) => onFormChange({ ...form, name: event.target.value })} placeholder="Nome, es. Ruoli morosi 2024" className="rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-amber-400" />
                    <div className="grid gap-2 sm:grid-cols-2">
                      <input value={form.year_from} onChange={(event) => onFormChange({ ...form, year_from: event.target.value.replace(/\D/g, "").slice(0, 4) })} inputMode="numeric" maxLength={4} placeholder="Anno da" className="rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-amber-400" />
                      <input value={form.year_to} onChange={(event) => onFormChange({ ...form, year_to: event.target.value.replace(/\D/g, "").slice(0, 4) })} inputMode="numeric" maxLength={4} placeholder="Anno a" className="rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-amber-400" />
                    </div>
                    <div className="grid gap-2 sm:grid-cols-2">
                      <label className="grid gap-1 text-xs font-semibold text-gray-600">
	                        % maggiorazione ruolo
                        <input value={form.surcharge_rate_percent} onChange={(event) => onFormChange({ ...form, surcharge_rate_percent: event.target.value })} inputMode="decimal" placeholder="es. 3" className="rounded-xl border border-gray-200 px-3 py-2 text-sm font-normal outline-none focus:border-amber-400" />
                      </label>
                      {shouldShowAnnualityDateFields ? (
                        <p className="rounded-2xl border border-amber-100 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800">
                          Il range verra salvato come una regola separata per ogni annualita, con scadenza bonaria e fallback interessi dedicati.
                        </p>
                      ) : (
                        <label className="grid gap-1 text-xs font-semibold text-gray-600">
	                          Scadenza pagamento bonario
	                          <input type="date" value={form.bonario_due_date} onChange={(event) => onFormChange({ ...form, bonario_due_date: event.target.value })} className="rounded-xl border border-gray-200 px-3 py-2 text-sm font-normal outline-none focus:border-amber-400" />
                        </label>
                      )}
                    </div>
                    {shouldShowAnnualityDateFields ? (
                      <div className="rounded-2xl border border-amber-100 bg-amber-50/70 p-3">
                        <p className="text-xs font-semibold text-amber-900">Date per annualita</p>
                        <div className="mt-2 grid gap-2 sm:grid-cols-2">
                          {annualityYears.map((year) => (
                            <div key={year} className="grid gap-2 rounded-2xl border border-amber-100 bg-white/70 p-3">
                              <p className="text-xs font-semibold text-amber-900">Annualita {year}</p>
                              <label className="grid gap-1 text-xs font-semibold text-gray-600">
                                Scadenza pagamento bonario
                                <input
                                  aria-label={`Scadenza pagamento bonario ${year}`}
                                  type="date"
                                  value={form.bonario_due_dates_by_year[String(year)] ?? ""}
                                  onChange={(event) =>
                                    onFormChange({
                                      ...form,
                                      bonario_due_dates_by_year: {
                                        ...form.bonario_due_dates_by_year,
                                        [year]: event.target.value,
                                      },
                                    })
                                  }
                                  className="rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm font-normal outline-none focus:border-amber-400"
                                />
                              </label>
                              <label className="grid gap-1 text-xs font-semibold text-gray-600">
                                Fallback/minimo interessi
                                <input
                                  aria-label={`Fallback/minimo interessi ${year}`}
                                  type="date"
                                  value={form.interest_from_by_year[String(year)] ?? ""}
                                  onChange={(event) =>
                                    onFormChange({
                                      ...form,
                                      interest_from_by_year: {
                                        ...form.interest_from_by_year,
                                        [year]: event.target.value,
                                      },
                                    })
                                  }
                                  className="rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm font-normal outline-none focus:border-amber-400"
                                />
                              </label>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}
                    <div className="grid gap-2 sm:grid-cols-2">
                      <label className="grid gap-1 text-xs font-semibold text-gray-600">
                        % Euribor medio 6 mesi
                        <input value={form.euribor_6m_rate_percent} onChange={(event) => onFormChange({ ...form, euribor_6m_rate_percent: event.target.value })} inputMode="decimal" placeholder="es. 3,25" className="rounded-xl border border-gray-200 px-3 py-2 text-sm font-normal outline-none focus:border-amber-400" />
                      </label>
                      <label className="grid gap-1 text-xs font-semibold text-gray-600">
                        % tasso da delibera
                        <input value={form.interest_rate_percent} onChange={(event) => onFormChange({ ...form, interest_rate_percent: event.target.value })} inputMode="decimal" placeholder="es. 2,5" className="rounded-xl border border-gray-200 px-3 py-2 text-sm font-normal outline-none focus:border-amber-400" />
                      </label>
                    </div>
                    <div className="rounded-2xl border border-sky-100 bg-sky-50 px-3 py-2 text-xs leading-5 text-sky-900">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span>
                          Recupera automaticamente la media annuale Euribor 6 mesi dal Data Portal BCE in base all&apos;anno iniziale della regola.
                        </span>
                        <button type="button" className="btn-secondary border-sky-200 bg-white text-sky-800 hover:bg-sky-100" onClick={onFetchEuribor}>
                          Recupera da BCE
                        </button>
                      </div>
                      {form.euribor_source_url ? (
                        <p className="mt-2">
                          Fonte {form.euribor_reference_period || "-"}:{" "}
                          <a href={form.euribor_source_url} target="_blank" rel="noreferrer" className="font-semibold underline decoration-sky-300">
                            verifica il dato BCE
                          </a>
                        </p>
                      ) : null}
                    </div>
                    <div className="grid gap-2 sm:grid-cols-2">
                      {shouldShowAnnualityDateFields ? null : (
                        <label className="grid gap-1 text-xs font-semibold text-gray-600">
                          Fallback/minimo interessi
                          <input type="date" value={form.interest_from} onChange={(event) => onFormChange({ ...form, interest_from: event.target.value })} className="rounded-xl border border-gray-200 px-3 py-2 text-sm font-normal outline-none focus:border-amber-400" />
                        </label>
                      )}
                    </div>
                    <label className="grid gap-1 text-xs font-semibold text-gray-600">
                      Decorrenza interessi
                      <select value={form.interest_start_mode} onChange={(event) => onFormChange({ ...form, interest_start_mode: event.target.value as CalculationPolicyFormState["interest_start_mode"] })} className="rounded-xl border border-gray-200 px-3 py-2 text-sm font-normal outline-none focus:border-amber-400">
                        <option value="notification_date">Da invio PEC/ricezione raccomandata</option>
                        <option value="fixed_date">Da data fissa policy</option>
                      </select>
                    </label>
                    <PolicyBollettinoFields form={form} onChange={onFormChange} />
                    <textarea value={form.notes} onChange={(event) => onFormChange({ ...form, notes: event.target.value })} rows={3} placeholder="Note operative" className="rounded-2xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-amber-400" />
                    <label className="flex items-center gap-2 text-sm text-gray-700">
                      <input type="checkbox" checked={form.is_active} onChange={(event) => onFormChange({ ...form, is_active: event.target.checked })} />
                      Policy attiva
                    </label>
                  </div>
                  <div className="mt-4 flex flex-wrap justify-end gap-2">
                    {editingId ? <button type="button" className="btn-secondary" onClick={onCancel}>Annulla</button> : null}
                    <button type="submit" className="btn-primary bg-[#8a5a16] hover:bg-[#6f4710]">{editingId ? "Aggiorna" : "Aggiungi"}</button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

function AnnualityManagerQuickFilters({
  managers,
  selectedManagerKey,
  onSelect,
}: {
  managers: RuoloTributiYearManagerResponse[];
  selectedManagerKey: string;
  onSelect: (managerKey: string) => void;
}) {
  const activeManagers = [...managers]
    .filter((manager) => manager.is_active)
    .sort((first, second) => managerYearStart(first) - managerYearStart(second));
  if (activeManagers.length === 0) {
    return (
      <div className="mt-4 rounded-2xl border border-amber-100 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-800">
        Regole annualita non disponibili: il filtro predefinito resta Consorzio/GAIA.
      </div>
    );
  }

  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {activeManagers.map((manager) => {
        const selected = selectedManagerKey === manager.manager_key;
        return (
          <button
            key={manager.id}
            type="button"
            onClick={() => onSelect(manager.manager_key)}
            className={`rounded-full border px-4 py-2 text-sm font-semibold transition ${getAnnualityManagerFilterClassName(manager.manager_key, selected)}`}
            aria-pressed={selected}
          >
            {formatYearRange(manager)} · {manager.manager_label}
          </button>
        );
      })}
    </div>
  );
}

function AmountCell({ label, value, strong = false }: { label: string; value: number | null | undefined; strong?: boolean }) {
  return (
    <div>
      <p className="uppercase tracking-[0.16em] text-gray-400">{label}</p>
      <p className={`mt-1 ${strong ? "font-semibold text-gray-900" : "font-medium text-gray-700"}`}>{formatEuro(value)}</p>
    </div>
  );
}

function ReminderWizardModal({
  candidates,
  candidatesLoading,
  candidateTotal,
  selectedTaxCodes,
  selectedReminderYears,
  reminderYearOptions,
  manualTaxCode,
  step,
  error,
  batchResult,
  generating,
  onClose,
  onStepChange,
  onToggleTaxCode,
  onToggleReminderYear,
  onManualTaxCodeChange,
  onAddManualTaxCode,
  onGenerate,
}: {
  candidates: RuoloTributiReminderCandidateResponse[];
  candidatesLoading: boolean;
  candidateTotal: number;
  selectedTaxCodes: string[];
  selectedReminderYears: number[];
  reminderYearOptions: number[];
  manualTaxCode: string;
  step: 1 | 2 | 3;
  error: string | null;
  batchResult: RuoloTributiReminderBatchResponse | null;
  generating: boolean;
  onClose: () => void;
  onStepChange: (step: 1 | 2 | 3) => void;
  onToggleTaxCode: (taxCode: string) => void;
  onToggleReminderYear: (year: number) => void;
  onManualTaxCodeChange: (value: string) => void;
  onAddManualTaxCode: () => void;
  onGenerate: () => void;
}) {
  const selectedCandidates = candidates.filter((candidate) => selectedTaxCodes.includes(candidate.codice_fiscale));
  const selectedDue = selectedCandidates.reduce((sum, candidate) => sum + (candidate.due_amount ?? 0), 0);
  const selectedSaldo = selectedCandidates.reduce((sum, candidate) => sum + (candidate.saldo_amount ?? 0), 0);
  const missingNasCount = selectedCandidates.filter((candidate) => !candidate.has_nas_folder).length;

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center bg-[#0f172a]/55 px-4 py-6 backdrop-blur-sm">
      <div className="flex max-h-[94vh] w-full max-w-[1480px] flex-col overflow-hidden rounded-[34px] border border-[#d6dfd2] bg-[#f8faf5] shadow-[0_34px_110px_rgba(15,23,42,0.32)]">
        <div className="relative overflow-hidden border-b border-[#dfe7db] bg-[#203829] px-7 py-6 text-white">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_12%_18%,rgba(233,242,218,0.22),transparent_32%),radial-gradient(circle_at_88%_8%,rgba(160,190,132,0.3),transparent_28%)]" />
          <div className="relative flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#cfe2b8]">Wizard solleciti tributi</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight">Crea batch PDF per utenze morose</h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-white/72">
                Raggruppa gli avvisi aperti per codice fiscale, include piu anni e salva ogni PDF nella cartella NAS dell&apos;utenza sotto <code>solleciti</code>.
              </p>
            </div>
            <button type="button" className="btn-secondary border-white/20 bg-white/10 text-white hover:bg-white/20" onClick={onClose}>
              Chiudi
            </button>
          </div>
        </div>

        <div className="grid gap-4 border-b border-[#e5eadf] bg-white px-7 py-4 md:grid-cols-3">
          <WizardStepPill active={step === 1} done={step > 1} label="1. Seleziona utenze" />
          <WizardStepPill active={step === 2} done={step > 2} label="2. Verifica batch" />
          <WizardStepPill active={step === 3} done={false} label="3. Esito generazione" />
        </div>

        <div className="overflow-y-auto p-6">
          {error ? <div className="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">{error}</div> : null}

          {step === 1 ? (
            <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr),360px]">
              <section className="rounded-[28px] border border-[#d7e0d2] bg-white p-5 shadow-panel">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Utenze candidabili</p>
                    <p className="mt-1 text-sm text-gray-600">{candidateTotal} utenze aperte trovate per le annualita selezionate.</p>
                  </div>
                  <button type="button" className="btn-secondary" onClick={() => onStepChange(2)} disabled={selectedTaxCodes.length === 0}>
                    Avanti
                  </button>
                </div>
                <div className="mt-5 rounded-2xl border border-[#e5ebe1] bg-[#fbfcfa] p-4">
                  <p className="text-sm font-semibold text-gray-900">Annualita da includere nel nuovo avviso</p>
                  <p className="mt-1 text-xs leading-5 text-gray-500">
                    Il nuovo numero avviso usa sempre l&apos;anno di emissione corrente e concatena le annualita selezionate nel codice.
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {reminderYearOptions.map((year) => {
                      const selected = selectedReminderYears.includes(year);
                      return (
                        <button
                          key={year}
                          type="button"
                          aria-pressed={selected}
                          onClick={() => onToggleReminderYear(year)}
                          className={`rounded-full border px-3 py-1.5 text-sm font-semibold transition ${
                            selected
                              ? "border-[#1D4E35] bg-[#1D4E35] text-white"
                              : "border-[#d7e0d2] bg-white text-gray-700 hover:border-[#8CB39D] hover:bg-[#f4faf6]"
                          }`}
                        >
                          {year}
                        </button>
                      );
                    })}
                  </div>
                </div>
                <div className="mt-5 space-y-3">
                  {candidatesLoading ? (
                    <p className="rounded-2xl bg-gray-50 px-4 py-5 text-sm text-gray-500">Caricamento utenze sollecitabili...</p>
                  ) : candidates.length === 0 ? (
                    <EmptyState icon={DocumentIcon} title="Nessuna utenza sollecitabile" description="Modifica i filtri o verifica i pagamenti importati." />
                  ) : (
                    candidates.map((candidate) => (
                      <label
                        key={candidate.codice_fiscale}
                        className={`grid cursor-pointer gap-4 rounded-[24px] border px-4 py-4 transition hover:-translate-y-0.5 hover:shadow-sm md:grid-cols-[auto,minmax(0,1fr),320px] ${
                          selectedTaxCodes.includes(candidate.codice_fiscale) ? "border-[#1D4E35] bg-[#f3faf5]" : "border-[#e5ebe1] bg-white"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={selectedTaxCodes.includes(candidate.codice_fiscale)}
                          onChange={() => onToggleTaxCode(candidate.codice_fiscale)}
                          className="mt-1"
                        />
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-gray-900">{candidate.display_name ?? candidate.codice_fiscale}</p>
                          <p className="mt-1 text-xs leading-5 text-gray-500">
                            CF/P.IVA {candidate.codice_fiscale} · {candidate.comune ?? "Comune non disponibile"} · anni {candidate.years.join(", ")}
                          </p>
                          {candidate.annuality_managers.length ? (
                            <p className="mt-1 text-xs font-semibold text-[#1D4E35]">
                              Gestione: {candidate.annuality_managers.join(", ")}
                            </p>
                          ) : null}
                          {!candidate.has_nas_folder ? (
                            <p className="mt-2 rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800">Cartella NAS mancante: verra tracciato come errore</p>
                          ) : null}
                        </div>
                        <div className="grid grid-cols-3 gap-2 text-right text-xs">
                          <CompactMetric label="Avvisi" value={String(candidate.avvisi_count)} />
                          <AmountCell label="Dovuto" value={candidate.due_amount} />
                          <AmountCell label="Saldo" value={candidate.saldo_amount} strong />
                        </div>
                      </label>
                    ))
                  )}
                </div>
              </section>

              <WizardSummaryCard
                selectedCount={selectedTaxCodes.length}
                selectedDue={selectedDue}
                selectedSaldo={selectedSaldo}
                missingNasCount={missingNasCount}
                manualTaxCode={manualTaxCode}
                onManualTaxCodeChange={onManualTaxCodeChange}
                onAddManualTaxCode={onAddManualTaxCode}
              />
            </div>
          ) : null}

          {step === 2 ? (
            <section className="rounded-[28px] border border-[#d7e0d2] bg-white p-6 shadow-panel">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Verifica batch</p>
              <h3 className="mt-2 text-xl font-semibold text-gray-900">Conferma generazione di {selectedTaxCodes.length} solleciti</h3>
              <div className="mt-5 grid gap-3 md:grid-cols-4">
                <DetailField label="Utenze selezionate" value={String(selectedTaxCodes.length)} />
                <DetailField label="Annualita" value={selectedReminderYears.join(", ") || "-"} />
                <DetailField label="Dovuto selezione" value={formatEuro(selectedDue)} />
                <DetailField label="Saldo selezione" value={formatEuro(selectedSaldo)} />
                <DetailField label="Cartelle NAS mancanti" value={String(missingNasCount)} />
              </div>
              <div className="mt-5 rounded-2xl border border-[#e5ebe1] bg-[#fbfcfa] p-4">
                <p className="text-sm font-semibold text-gray-900">Template configurato</p>
                <p className="mt-2 break-all text-xs leading-5 text-gray-500">{DEFAULT_REMINDER_TEMPLATE_LABEL}</p>
              </div>
              <div className="mt-6 flex flex-wrap justify-between gap-3">
                <button type="button" className="btn-secondary" onClick={() => onStepChange(1)}>
                  Torna alla selezione
                </button>
                <button type="button" className="btn-primary" onClick={onGenerate} disabled={generating}>
                  {generating ? "Generazione in corso..." : "Genera PDF nel NAS"}
                </button>
              </div>
            </section>
          ) : null}

          {step === 3 && batchResult ? (
            <section className="rounded-[28px] border border-[#d7e0d2] bg-white p-6 shadow-panel">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Batch generato</p>
              <h3 className="mt-2 text-xl font-semibold text-gray-900">
                {batchResult.items_generated} PDF generati, {batchResult.items_failed} errori
              </h3>
              <div className="mt-5 space-y-3">
                {batchResult.items.map((item) => (
                  <div key={item.id} className="grid gap-3 rounded-2xl border border-[#e5ebe1] bg-[#fbfcfa] px-4 py-3 md:grid-cols-[minmax(0,1fr),auto]">
                  <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-gray-900">{item.display_name ?? item.codice_fiscale}</p>
                      {typeof item.payload_json?.notice_number === "string" ? (
                        <p className="mt-1 text-xs font-semibold text-[#1D4E35]">Avviso {item.payload_json.notice_number}</p>
                      ) : null}
                      <p className="mt-1 break-all text-xs text-gray-500">{item.generated_document_path ?? item.error_detail ?? "In attesa"}</p>
                    </div>
                    <span className={`self-start rounded-full px-3 py-1 text-xs font-semibold ${item.status === "generated" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800"}`}>
                      {item.status}
                    </span>
                  </div>
                ))}
              </div>
              <div className="mt-6 flex justify-end">
                <button type="button" className="btn-secondary" onClick={onClose}>
                  Chiudi wizard
                </button>
              </div>
            </section>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function WizardStepPill({ active, done, label }: { active: boolean; done: boolean; label: string }) {
  return (
    <div className={`rounded-2xl border px-4 py-3 text-sm font-semibold ${active ? "border-[#1D4E35] bg-[#eef7ef] text-[#1D4E35]" : done ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-gray-200 bg-gray-50 text-gray-500"}`}>
      {label}
    </div>
  );
}

function CompactMetric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="uppercase tracking-[0.16em] text-gray-400">{label}</p>
      <p className="mt-1 font-semibold text-gray-900">{value}</p>
    </div>
  );
}

function WizardSummaryCard({
  selectedCount,
  selectedDue,
  selectedSaldo,
  missingNasCount,
  manualTaxCode,
  onManualTaxCodeChange,
  onAddManualTaxCode,
}: {
  selectedCount: number;
  selectedDue: number;
  selectedSaldo: number;
  missingNasCount: number;
  manualTaxCode: string;
  onManualTaxCodeChange: (value: string) => void;
  onAddManualTaxCode: () => void;
}) {
  return (
    <aside className="rounded-[28px] border border-[#d7e0d2] bg-white p-5 shadow-panel">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Riepilogo selezione</p>
      <div className="mt-5 grid gap-3">
        <DetailField label="Utenze" value={String(selectedCount)} />
        <DetailField label="Dovuto" value={formatEuro(selectedDue)} />
        <DetailField label="Saldo" value={formatEuro(selectedSaldo)} />
        <DetailField label="NAS mancanti" value={String(missingNasCount)} />
      </div>
      <div className="mt-5 rounded-2xl border border-[#e5ebe1] bg-[#fbfcfa] p-4">
        <p className="text-sm font-semibold text-gray-900">Selezione manuale</p>
        <p className="mt-1 text-xs leading-5 text-gray-500">Aggiungi un codice fiscale/P.IVA non presente nella pagina corrente.</p>
        <div className="mt-3 flex gap-2">
          <input
            value={manualTaxCode}
            onChange={(event) => onManualTaxCodeChange(event.target.value)}
            placeholder="Codice fiscale"
            className="min-w-0 flex-1 rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[#8CB39D]"
          />
          <button type="button" className="btn-secondary" onClick={onAddManualTaxCode}>
            Aggiungi
          </button>
        </div>
      </div>
    </aside>
  );
}

function TributiDetailPanel({
  detail,
  loading,
  operationError,
  operationMessage,
  onSubmitPayment,
  onSubmitStatus,
  onSubmitNote,
  onQueueInCassSubjectSync,
  onPrepareReminder,
  onOpenSubject,
  reminderGenerating,
  incassSyncing,
}: {
  detail: RuoloTributiAvvisoDetailResponse | null;
  loading: boolean;
  operationError: string | null;
  operationMessage: string | null;
  onSubmitPayment: (event: FormEvent<HTMLFormElement>) => void;
  onSubmitStatus: (event: FormEvent<HTMLFormElement>) => void;
  onSubmitNote: (event: FormEvent<HTMLFormElement>) => void;
  onQueueInCassSubjectSync: () => void;
  onPrepareReminder: (item: RuoloTributiAvvisoListItemResponse) => void;
  onOpenSubject: (item: RuoloTributiAvvisoListItemResponse) => void;
  reminderGenerating: boolean;
  incassSyncing: boolean;
}) {
  if (loading) {
    return (
      <section className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
        <div className="h-28 animate-pulse rounded-[24px] bg-gradient-to-r from-[#edf4ed] to-[#f8faf6]" />
        <div className="mt-5 grid gap-3 md:grid-cols-3">
          <div className="h-20 animate-pulse rounded-2xl bg-gray-100" />
          <div className="h-20 animate-pulse rounded-2xl bg-gray-100" />
          <div className="h-20 animate-pulse rounded-2xl bg-gray-100" />
        </div>
        <p className="mt-4 text-sm text-gray-400">Caricamento dettaglio...</p>
      </section>
    );
  }
  if (!detail) {
    return (
      <section className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 text-center shadow-panel">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-[#e8f2ec] text-[#1D4E35]">
          <DocumentIcon className="h-6 w-6" />
        </div>
        <p className="mt-4 section-title">Dettaglio tributo</p>
        {operationError ? <div className="mx-auto mt-3 max-w-xl rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{operationError}</div> : null}
        <p className="mx-auto mt-2 max-w-xl section-copy">Seleziona un avviso dalla lista per registrare pagamenti, note e link CapaciTas.</p>
      </section>
    );
  }

  const saldo = detail.saldo_amount ?? 0;
  const reminderEnabled = canPrepareReminder(detail);
  const missingRuleReminderAction = shouldShowMissingRuleReminderAction(detail);
  const reminderTitle = "Predisponi e apri la preview del PDF";
  const rateizationInsight = buildIncassRateizationInsight(detail);
  const operationalSummary =
    saldo <= 0
      ? {
          title: "Posizione economicamente chiusa",
          description: "Il saldo aggiornato risulta allineato. Usa note e storico per validare gli ultimi passaggi amministrativi.",
          tone: "success" as const,
        }
      : !detail.workflow_status
        ? {
            title: "Serve uno stato operativo",
            description: "Assegna workflow e riferimenti CapaciTas per evitare lavorazioni fuori canale su una posizione ancora aperta.",
            tone: "warning" as const,
          }
        : {
            title: "Saldo ancora aperto",
            description: "Verifica incassi, aggiorna CapaciTas e prepara il sollecito solo se la posizione resta effettivamente morosa.",
            tone: "warning" as const,
          };
  const gaiaLinkSummary = detail.is_linked
    ? {
        title: "Collegamento GAIA disponibile",
        description: detail.subject_id
          ? "Puoi aprire subito il soggetto GAIA per controllare anagrafica e storico collegato."
          : "La posizione risulta collegata, ma non espone un soggetto apribile da questo pannello.",
        tone: "success" as const,
      }
    : {
        title: "Collegamento GAIA assente",
        description: "La posizione non è ancora agganciata a un soggetto GAIA. Gestisci pagamenti e note con attenzione al matching anagrafico.",
        tone: "neutral" as const,
      };
  const deliverySummary = detail.mailing_delivery
    ? {
        title: detail.mailing_delivery.delivery_status || "PEC acquisita",
        description: `${formatDeliveryDate(detail.mailing_delivery.delivered_at)} · ${detail.mailing_delivery.receipt_documents_count} ricevute archiviate`,
        tone: "success" as const,
      }
    : {
        title: "Nessuna PEC collegata",
        description: "Non risultano ricevute PEC su questo avviso. Verifica eventuali altri canali di notifica prima di sollecitare.",
        tone: "neutral" as const,
      };

  return (
    <section className="space-y-4">
      <div className="overflow-hidden rounded-[24px] border border-[#cddacc] bg-[#183325] text-white shadow-panel">
        <div className="relative p-4 md:p-5">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(232,242,218,0.18),_transparent_36%),radial-gradient(circle_at_top_right,_rgba(202,224,173,0.28),_transparent_30%),linear-gradient(135deg,_rgba(29,78,53,0.96),_rgba(24,51,37,1))]" />
          <div className="relative space-y-4">
            <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr),340px]">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${getPaymentStatusClassName(detail.payment_status)} bg-white/95`}>
                    {PAYMENT_STATUS_LABELS[detail.payment_status]}
                  </span>
                  <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-semibold text-white">
                    {detail.workflow_status ?? "Nessuno stato operativo"}
                  </span>
                  {detail.annuality_manager_label ? (
                    <span className="rounded-full border border-[#cfe2b8]/70 bg-[#e9f2da] px-3 py-1 text-xs font-semibold text-[#183325]">
                      {detail.annuality_manager_label}
                    </span>
                  ) : null}
                  {!detail.is_linked ? (
                    <span className="rounded-full border border-amber-200/60 bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">
                      Orfano GAIA
                    </span>
                  ) : null}
                </div>

                <p className="mt-3 text-xl font-semibold tracking-tight sm:text-2xl">
                  {detail.display_name ?? detail.nominativo_raw ?? "Avviso selezionato"}
                </p>
                <p className="mt-2 max-w-3xl text-sm leading-5 text-white/78">
                  CNC {displayTributiNoticeCode(detail)} · Anno {detail.anno_tributario} · Utenza {detail.codice_utenza ?? "-"} · CF/P.IVA {detail.codice_fiscale_raw ?? "-"}
                </p>
                <p className="mt-1.5 max-w-3xl text-sm leading-5 text-white/66">
                  {detail.capacitas_avviso_code
                    ? `Riferimento CapaciTas ${detail.capacitas_avviso_code}.`
                    : "Nessun riferimento CapaciTas configurato."}{" "}
                  {operationalSummary.description}
                </p>

                <div className="mt-4 flex flex-wrap gap-2">
                  {detail.capacitas_url ? (
                    <Link
                      className="btn-secondary border-white/20 bg-white text-[#203829] hover:bg-[#eef7ef]"
                      href={detail.capacitas_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Apri CapaciTas
                    </Link>
                  ) : null}
                  <Link className="btn-secondary border-white/20 bg-white/10 text-white hover:bg-white/20" href={`/ruolo/tributi/${detail.id}`}>
                    Pagina dettaglio
                  </Link>
                  {detail.subject_id ? (
                    <button
                      type="button"
                      className="btn-secondary border-white/20 bg-white/10 text-white hover:bg-white/20"
                      onClick={() => onOpenSubject(detail)}
                    >
                      Dettaglio soggetto
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="btn-secondary border-white/15 bg-white/5 text-white/60"
                      disabled
                      title="Avviso non collegato a un soggetto GAIA"
                    >
                      Dettaglio soggetto
                    </button>
                  )}
                  {reminderEnabled ? (
                    <button
                      type="button"
                      className="btn-secondary border-[#cfe2b8] bg-[#e9f2da] text-[#183325] hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
                      onClick={() => onPrepareReminder(detail)}
                      disabled={reminderGenerating}
                      title={reminderTitle}
                    >
                      {reminderGenerating ? "Creazione avviso..." : "Preview avviso sollecito"}
                    </button>
                  ) : null}
                </div>
              </div>

              <div className="grid gap-2">
                <HeroInsightCard
                  eyebrow="Priorita operativa"
                  title={operationalSummary.title}
                  description={operationalSummary.description}
                  tone={operationalSummary.tone}
                />
                <HeroInsightCard
                  eyebrow="Collegamento GAIA"
                  title={gaiaLinkSummary.title}
                  description={gaiaLinkSummary.description}
                  tone={gaiaLinkSummary.tone}
                />
                <HeroInsightCard
                  eyebrow="Tracciamento consegna"
                  title={deliverySummary.title}
                  description={deliverySummary.description}
                  tone={deliverySummary.tone}
                />
              </div>
            </div>

            <div className="grid gap-2 md:grid-cols-3 xl:grid-cols-6">
              <DetailMetric label="Ruolo originario" value={formatEuro(detail.importo_totale_euro)} />
              <DetailMetric label="Maggiorazione" value={formatEuro(detail.surcharge_amount)} tone={(detail.surcharge_amount ?? 0) > 0 ? "warning" : "neutral"} />
              <DetailMetric label="Interessi" value={formatEuro(detail.interest_amount)} tone={(detail.interest_amount ?? 0) > 0 ? "warning" : "neutral"} />
              <DetailMetric label="Dovuto aggiornato" value={formatEuro(detail.adjusted_due_amount ?? detail.importo_totale_euro)} />
              <DetailMetric label="Pagato" value={formatEuro(detail.paid_amount)} tone="success" />
              <DetailMetric label="Saldo aggiornato" value={formatEuro(detail.saldo_amount)} tone={saldo > 0 ? "warning" : "success"} />
            </div>
          </div>
        </div>
      </div>

      {operationError ? <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">{operationError}</div> : null}
      {operationMessage ? <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700">{operationMessage}</div> : null}

      <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr),360px]">
        <div className="space-y-3">
          <div className="grid gap-3 2xl:grid-cols-[minmax(0,1.05fr),0.95fr]">
            <DetailSection
              eyebrow="Profilo contribuente"
              title="Anagrafica, collegamenti e riferimenti esterni"
              description="Qui trovi i dati identificativi utili per riconciliare rapidamente la posizione con GAIA e CapaciTas."
            >
              <div className="grid gap-2 md:grid-cols-2">
                <DetailField label="CF/P.IVA" value={detail.codice_fiscale_raw} />
                <DetailField label="Codice utenza" value={detail.codice_utenza} />
                <DetailField label="Domicilio" value={detail.domicilio_raw} />
                <DetailField label="Residenza" value={detail.residenza_raw} />
                <DetailField label="Ultimo pagamento" value={formatDate(detail.last_payment_at)} />
                <DetailField label="Codice avviso CapaciTas" value={detail.capacitas_avviso_code} />
                <DetailField label="Collegamento GAIA" value={detail.is_linked ? "Collegato" : "Da collegare"} />
                <DetailField label="Gestore annualita" value={detail.annuality_manager_label} />
                <DetailField label="Policy calcolo" value={detail.calculation_policy} />
                <DetailField label="Decorrenza interessi" value={formatDate(detail.interest_start_date)} />
                <DetailField label="Sorgente decorrenza" value={formatInterestStartSource(detail.interest_start_source)} />
              </div>
            </DetailSection>

            <DetailSection
              eyebrow="Quadro economico"
              title="Ripartizione degli importi per tributo"
              description="La scomposizione aiuta a capire subito la composizione del dovuto e l&apos;ultimo movimento registrato."
            >
              <div className="grid gap-2">
                <ModuleWorkspaceMiniStat eyebrow="Tributo 0648" value={formatEuro(detail.importo_totale_0648)} description="Quota manutenzione consortile." compact />
                <ModuleWorkspaceMiniStat eyebrow="Tributo 0985" value={formatEuro(detail.importo_totale_0985)} description="Quota irrigazione." compact />
                <ModuleWorkspaceMiniStat eyebrow="Tributo 0668" value={formatEuro(detail.importo_totale_0668)} description="Quota sistemazione idraulica." compact />
                <ModuleWorkspaceMiniStat eyebrow="Stato saldo" value={formatEuro(detail.saldo_amount)} description={saldo > 0 ? "Residuo ancora da lavorare." : "Posizione economicamente chiusa."} tone={saldo > 0 ? "warning" : "success"} compact />
              </div>
            </DetailSection>
          </div>

          {rateizationInsight ? (
            <DetailSection
              eyebrow="Avviso di pagamento inCASS"
              title="Rateizzazione visibile in GAIA"
              description="Per gli avvisi rateizzati GAIA usa il totale emesso da inCASS e il versato dell'utenza per calcolare il saldo operativo."
            >
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800">
                  Avviso {rateizationInsight.sourceNoticeId ?? "-"}
                </span>
                {rateizationInsight.statusLabel ? (
                  <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-700">{rateizationInsight.statusLabel}</span>
                ) : null}
              </div>
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-5">
                <ModuleWorkspaceMiniStat eyebrow="Emesso inCASS" value={formatEuro(rateizationInsight.issuedAmount)} description="Carico originario sincronizzato." compact />
                <ModuleWorkspaceMiniStat eyebrow="Totale rateizzato" value={formatEuro(rateizationInsight.rateizedAmount)} description="Importo emesso in rateizzazione." compact />
                <ModuleWorkspaceMiniStat eyebrow="Costo rateizzazione" value={formatEuro(rateizationInsight.feeAmount)} description="Differenza fra rateizzato e carico." tone="warning" compact />
                <ModuleWorkspaceMiniStat eyebrow="Versato utenza" value={formatEuro(rateizationInsight.paidAmount)} description="Riscosso inCASS normalizzato in positivo." tone="success" compact />
                <ModuleWorkspaceMiniStat eyebrow="Residuo inCASS" value={formatEuro(rateizationInsight.residualAmount)} description="Importo ancora da regolarizzare." tone={(rateizationInsight.residualAmount ?? 0) > 0 ? "warning" : "success"} compact />
              </div>
            </DetailSection>
          ) : null}

          <DetailSection
            eyebrow="PEC e consegna"
            title="Ricevute inCASS collegate all&apos;avviso"
            description="Verifica esiti, date e numero di ricevute archiviate senza uscire dal dettaglio."
          >
            {detail.mailing_delivery ? (
              <>
                {detail.mailing_delivery.receipt_groups.length ? (
                  <div className="mb-3 flex flex-wrap gap-2">
                    {detail.mailing_delivery.receipt_groups.map((group) => (
                      <span key={group} className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                        {group}
                      </span>
                    ))}
                  </div>
                ) : null}
                <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                  <DetailField label="PEC destinatario" value={detail.mailing_delivery.pec_recipient} />
                  <DetailField label="Data consegna" value={formatDeliveryDate(detail.mailing_delivery.delivered_at)} />
                  <DetailField label="Data accettazione" value={formatDeliveryDate(detail.mailing_delivery.accepted_at)} />
                  <DetailField label="Ricevute archiviate" value={String(detail.mailing_delivery.receipt_documents_count)} />
                  <DetailField label="Stato PEC" value={detail.mailing_delivery.delivery_status} />
                  <DetailField label="Avviso inCASS" value={detail.mailing_delivery.source_notice_id} />
                </div>
              </>
            ) : (
              <EmptyState
                icon={DocumentIcon}
                title="Nessuna ricevuta PEC collegata"
                description="Nessuna ricevuta PEC di consegna collegata all'avviso."
              />
            )}
          </DetailSection>
        </div>

        <aside className="space-y-3 xl:sticky xl:top-0">
          <ActionCard
            eyebrow="Azioni operative"
            title="Registra pagamento"
            description="Aggiorna saldo e storico appena ricevi un incasso manuale o una riconciliazione esterna."
            tone="emerald"
          >
            <form className="space-y-3" onSubmit={onSubmitPayment}>
              <div className="grid gap-2 sm:grid-cols-2">
                <ActionField htmlFor="tributi-payment-amount" label="Importo">
                  <input id="tributi-payment-amount" name="amount" inputMode="decimal" placeholder="Importo" className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:border-[#8CB39D]" />
                </ActionField>
                <ActionField htmlFor="tributi-payment-date" label="Data pagamento">
                  <input id="tributi-payment-date" name="paid_at" type="date" className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:border-[#8CB39D]" />
                </ActionField>
                <ActionField htmlFor="tributi-payment-reference" label="Riferimento">
                  <input id="tributi-payment-reference" name="payment_reference" placeholder="Riferimento" className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:border-[#8CB39D]" />
                </ActionField>
                <ActionField htmlFor="tributi-payment-method" label="Metodo">
                  <input id="tributi-payment-method" name="payment_method" placeholder="Metodo" className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:border-[#8CB39D]" />
                </ActionField>
              </div>
              <button type="submit" className="btn-secondary w-full">Salva pagamento</button>
            </form>
          </ActionCard>

          <ActionCard
            eyebrow="Workflow"
            title="Stato operativo e CapaciTas"
            description="Allinea il workflow interno e mantieni aggiornati i riferimenti usati dagli operatori."
            tone="sky"
          >
            <form className="space-y-3" onSubmit={onSubmitStatus}>
              <ActionField htmlFor="tributi-workflow-status" label="Stato operativo">
                <select id="tributi-workflow-status" name="workflow_status" defaultValue={detail.workflow_status ?? ""} className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:border-[#8CB39D]">
                  <option value="">Nessuno stato operativo</option>
                  {WORKFLOW_STATUS_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                </select>
              </ActionField>
              <ActionField htmlFor="tributi-capacitas-url" label="Link CapaciTas">
                <input id="tributi-capacitas-url" name="capacitas_url" defaultValue={detail.capacitas_url ?? ""} placeholder="Link CapaciTas" className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:border-[#8CB39D]" />
              </ActionField>
              {detail.capacitas_url ? (
                <Link className="inline-flex text-xs font-semibold text-[#1D4E35] underline-offset-4 hover:underline" href={detail.capacitas_url} target="_blank" rel="noreferrer">
                  Apri link CapaciTas
                </Link>
              ) : null}
              <ActionField htmlFor="tributi-capacitas-code" label="Codice avviso">
                <input id="tributi-capacitas-code" name="capacitas_avviso_code" defaultValue={detail.capacitas_avviso_code ?? ""} placeholder="Codice avviso CapaciTas" className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:border-[#8CB39D]" />
              </ActionField>
              <button type="submit" className="btn-secondary w-full">Aggiorna stato</button>
            </form>
          </ActionCard>

          <ActionCard
            eyebrow="inCASS"
            title="Sincronizza il soggetto collegato"
            description="Accoda un recupero puntuale degli avvisi inCASS per il soggetto GAIA collegato a questa posizione."
            tone="sky"
          >
            <div className="space-y-3">
              <div className="rounded-xl border border-dashed border-[#d6dfd2] bg-white/70 px-3 py-2 text-sm leading-5 text-gray-600">
                {detail.subject_id
                  ? "La sync include dettaglio e partitario; il worker aggiornera gli avvisi del soggetto in coda."
                  : "L'avviso non espone un soggetto GAIA collegato: collega prima la posizione per accodare una sync puntuale."}
              </div>
              <button
                type="button"
                className="btn-secondary w-full disabled:cursor-not-allowed disabled:opacity-60"
                onClick={onQueueInCassSubjectSync}
                disabled={incassSyncing}
                title={detail.subject_id ? "Accoda sync inCASS puntuale" : "Avviso non collegato a un soggetto GAIA"}
              >
                {incassSyncing ? "Accodo sync..." : "Accoda sync inCASS"}
              </button>
            </div>
          </ActionCard>

          <ActionCard
            eyebrow="Tracciamento"
            title="Nota interna"
            description="Usa note brevi e operative per lasciare il contesto utile al prossimo passaggio."
          >
            <form className="space-y-3" onSubmit={onSubmitNote}>
              <ActionField htmlFor="tributi-note-body" label="Nota operativa">
                <textarea id="tributi-note-body" name="body" rows={3} placeholder="Es. utente contattato, pratica contestata..." className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:border-[#8CB39D]" />
              </ActionField>
              <button type="submit" className="btn-secondary w-full">Salva nota</button>
            </form>
          </ActionCard>

          {reminderEnabled ? (
            <ActionCard
              eyebrow="Sollecito"
              title="Apri la preview del documento"
              description="Genera o riapri l'anteprima PDF del nuovo avviso di sollecito."
              tone="amber"
            >
              <div className="space-y-3">
                <div className="rounded-xl border border-dashed border-[#d6dfd2] bg-white/70 px-3 py-2 text-sm leading-5 text-gray-600">
                  {detail.mailing_delivery
                    ? "Le ricevute PEC sono già visibili sopra: verifica consegna e saldo prima di procedere con il nuovo sollecito."
                    : "Non risultano ricevute PEC collegate: controlla il canale di notifica prima di generare un nuovo sollecito."}
                </div>
                <button
                  type="button"
                  className="btn-secondary w-full"
                  onClick={() => onPrepareReminder(detail)}
                  disabled={reminderGenerating}
                  title={reminderTitle}
                >
                  {reminderGenerating ? "Creo preview..." : "Genera o riapri preview"}
                </button>
              </div>
            </ActionCard>
          ) : missingRuleReminderAction ? (
            <ActionCard
              eyebrow="Sollecito"
              title="Regola ruolo mancante"
              description="Configura prima una Regola ruolo per questa annualita: la preview resta disabilitata per evitare avvisi errati."
              tone="amber"
            >
              <button
                type="button"
                className="btn-secondary w-full"
                disabled
                title="Regola ruolo non configurata per questa annualita"
              >
                Genera o riapri preview
              </button>
            </ActionCard>
          ) : null}
        </aside>
      </div>

      <section className="grid gap-3 xl:grid-cols-2">
        <HistoryCard
          title="Pagamenti registrati"
          description="Storico degli incassi associati a questa posizione."
          empty="Nessun pagamento registrato."
          count={detail.payments.length}
        >
          {detail.payments.map((payment) => (
            <div key={payment.id} className="rounded-2xl border border-gray-100 bg-[#fbfcfa] px-4 py-3 text-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-gray-900">{formatEuro(payment.amount)}</p>
                  <p className="mt-1 text-xs text-gray-500">{formatDate(payment.paid_at)} · {payment.payment_method ?? "Metodo non indicato"}</p>
                </div>
                <span className="rounded-full bg-gray-100 px-2.5 py-1 text-[11px] font-semibold text-gray-600">{payment.status}</span>
              </div>
              <p className="mt-2 text-xs text-gray-500">Riferimento {payment.payment_reference ?? payment.source}</p>
            </div>
          ))}
        </HistoryCard>

        <HistoryCard
          title="Note"
          description="Passaggi operativi e contatti registrati dagli operatori."
          empty="Nessuna nota."
          count={detail.notes.length}
        >
          {detail.notes.map((note) => (
            <div key={note.id} className="rounded-2xl border border-gray-100 bg-[#fbfcfa] px-4 py-3 text-sm">
              <p className="text-gray-800">{note.body}</p>
              <p className="mt-2 text-xs text-gray-500">{formatDate(note.created_at)}</p>
            </div>
          ))}
        </HistoryCard>
      </section>
    </section>
  );
}

function SubjectQuickViewModal({ subject, onClose }: { subject: SubjectQuickView; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-[105] flex items-center justify-center bg-black/50 px-3 py-5 backdrop-blur-sm xl:px-5">
      <div className="flex h-full max-h-[95vh] w-full max-w-[min(1600px,98vw)] flex-col overflow-hidden rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.28)]">
        <div className="flex items-center justify-between gap-4 border-b border-gray-100 bg-white px-6 py-4">
          <div className="min-w-0">
            <p className="section-title">Dettaglio soggetto</p>
            <p className="mt-1 truncate text-sm text-gray-500">{subject.label || subject.id}</p>
          </div>
          <div className="flex items-center gap-3">
            <Link className="btn-secondary" href={`/utenze/${subject.id}`} target="_blank">
              Apri pagina
            </Link>
            <button className="btn-secondary" type="button" onClick={onClose}>
              Chiudi
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-hidden bg-[#f4f7f5] p-4 xl:px-5 xl:py-5">
          <iframe
            key={subject.id}
            src={`/utenze/${subject.id}?embedded=1`}
            title={`Dettaglio soggetto ${subject.label || subject.id}`}
            className="h-full w-full rounded-2xl border border-gray-200 bg-white shadow-sm"
          />
        </div>
      </div>
    </div>
  );
}

function getReminderPreviewZoom(): number {
  return Number(globalThis.innerWidth) < REMINDER_PREVIEW_MOBILE_BREAKPOINT_PX ? REMINDER_PREVIEW_MOBILE_ZOOM : REMINDER_PREVIEW_DESKTOP_ZOOM;
}

function buildPdfPreviewUrlWithoutToolbar(objectUrl: string, zoom: number): string {
  const separator = objectUrl.includes("#") ? "&" : "#";
  return `${objectUrl}${separator}toolbar=0&navpanes=0&zoom=${zoom}`;
}

function ReminderPreviewModal({
  documents,
  error,
  loading,
  subjectLabel,
  onClose,
}: {
  documents: ReminderPreviewDocument[];
  error: string | null;
  loading: boolean;
  subjectLabel: string;
  onClose: () => void;
}) {
  const [activeKey, setActiveKey] = useState<ReminderPreviewTemplateKey>(documents[0]?.key ?? "gaia");
  const [pdfPreviewZoom, setPdfPreviewZoom] = useState(getReminderPreviewZoom);
  const activeDocument = documents.find((document) => document.key === activeKey) ?? documents[0];
  useEffect(() => {
    function syncPreviewZoom() {
      setPdfPreviewZoom(getReminderPreviewZoom());
    }
    syncPreviewZoom();
    window.addEventListener("resize", syncPreviewZoom);
    return () => window.removeEventListener("resize", syncPreviewZoom);
  }, []);
  if (!activeDocument) {
    return (
      <div className="fixed inset-0 z-[100] flex items-center justify-center bg-[#0f172a]/65 px-3 py-3 backdrop-blur-sm">
        <div className="w-full max-w-xl overflow-hidden rounded-[28px] border border-[#d6dfd2] bg-white shadow-[0_34px_110px_rgba(15,23,42,0.34)]">
          <div className="border-b border-[#e5eadf] bg-[#203829] px-6 py-5 text-white">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#cfe2b8]">Preview avviso sollecito</p>
            <h2 className="mt-2 text-xl font-semibold">{subjectLabel}</h2>
            <p className="mt-1 text-xs text-white/70">Generazione del template GAIA</p>
          </div>
          <div className="bg-[#f8faf5] px-6 py-6">
            {loading ? (
              <div className="rounded-3xl border border-[#dfe7db] bg-white p-5">
                <div className="flex items-center gap-4">
                  <span className="h-10 w-10 animate-spin rounded-full border-4 border-[#d8e6cf] border-t-[#1D4E35]" aria-hidden="true" />
                  <div>
                    <p className="text-base font-semibold text-gray-900">Creazione preview avviso sollecito...</p>
                    <p className="mt-1 text-sm leading-6 text-gray-600">GAIA sta generando i documenti e preparando l&apos;anteprima.</p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="rounded-3xl border border-red-200 bg-red-50 p-5">
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-red-700">Preview non disponibile</p>
                <p className="mt-3 text-base font-medium text-red-900">{error}</p>
              </div>
            )}
            <div className="mt-5 flex justify-end">
              <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>
                Chiudi
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }
  const { item, objectUrl, mimeType } = activeDocument;
  const filename = item.generated_document_path?.split("/").pop() || `${item.codice_fiscale}_avviso_sollecito.pdf`;
  const isPdf = mimeType === "application/pdf" || filename.toLowerCase().endsWith(".pdf");
  const downloadLabel = isPdf ? "Scarica PDF" : "Scarica DOCX";
  const pdfPreviewUrl = isPdf ? buildPdfPreviewUrlWithoutToolbar(objectUrl, pdfPreviewZoom) : objectUrl;
  /* c8 ignore start -- Multi-template tabs stay dormant while only the GAIA template is configured. */
  const templateTabs =
    documents.length > 1 ? (
      <div className="flex flex-wrap gap-2 border-b border-[#dfe7db] bg-white px-6 py-3" role="tablist" aria-label="Template avviso sollecito">
        {documents.map((document) => {
          const selected = document.key === activeDocument.key;
          return (
            <button
              key={document.key}
              type="button"
              role="tab"
              aria-selected={selected}
              className={`rounded-full border px-4 py-2 text-sm font-semibold transition ${
                selected
                  ? "border-[#1D4E35] bg-[#1D4E35] text-white shadow-sm"
                  : "border-[#d8dfd3] bg-[#f7faf4] text-[#315340] hover:border-[#8CB39D]"
              }`}
              onClick={() => setActiveKey(document.key)}
            >
              {document.label}
            </button>
          );
        })}
      </div>
    ) : null;
  /* c8 ignore stop */

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-[#0f172a]/65 px-3 py-3 backdrop-blur-sm">
      <div className="flex max-h-[96vh] w-full max-w-[min(1680px,97vw)] flex-col overflow-hidden rounded-[28px] border border-[#d6dfd2] bg-white shadow-[0_34px_110px_rgba(15,23,42,0.34)]">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-[#e5eadf] bg-[#203829] px-6 py-5 text-white">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#cfe2b8]">Preview avviso sollecito</p>
            <h2 className="mt-2 truncate text-xl font-semibold">{item.display_name ?? item.codice_fiscale}</h2>
            <p className="mt-1 break-all text-xs text-white/70">
              {activeDocument.label} · {item.generated_document_path ?? filename}
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            <a className="btn-secondary border-white/20 bg-white text-[#203829] hover:bg-[#eef7ef]" href={objectUrl} download={filename}>
              {downloadLabel}
            </a>
            <button type="button" className="btn-secondary border-white/20 bg-white/10 text-white hover:bg-white/20" onClick={onClose}>
              Chiudi
            </button>
          </div>
        </div>
        {templateTabs}
        <div className="grid gap-3 border-b border-[#edf1eb] bg-[#f8faf5] px-6 py-3 md:grid-cols-4">
          <DetailField label="CF/P.IVA" value={item.codice_fiscale} />
          <DetailField label="Anni" value={item.years_json?.join(", ")} />
          <DetailField label="Saldo" value={formatEuro(item.saldo_amount)} />
          <DetailField label="Stato" value={item.status} />
        </div>
        <div className="min-h-0 flex-1 bg-[#eef2ea] p-4">
          {isPdf ? (
            <iframe title="Preview PDF avviso sollecito" src={pdfPreviewUrl} className="h-[74vh] w-full rounded-2xl border border-[#d6dfd2] bg-white" />
          ) : (
            <div className="flex h-[74vh] items-center justify-center rounded-2xl border border-[#d6dfd2] bg-white p-8 text-center">
              <div className="max-w-xl">
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#1D4E35]">Preview PDF non disponibile</p>
                <h3 className="mt-3 text-xl font-semibold text-gray-900">Documento DOCX generato</h3>
                <p className="mt-3 text-sm leading-6 text-gray-600">
                  LibreOffice non e disponibile nel runtime che ha generato questo sollecito, quindi GAIA ha prodotto il DOCX scaricabile senza conversione PDF.
                </p>
                <a className="btn-primary mt-5 inline-flex" href={objectUrl} download={filename}>
                  Scarica DOCX
                </a>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function DetailMetric({ label, value, tone = "neutral" }: { label: string; value: string; tone?: "neutral" | "success" | "warning" }) {
  const toneClassName = {
    neutral: "border-white/15 bg-white/10 text-white",
    success: "border-emerald-200/40 bg-emerald-50 text-emerald-950",
    warning: "border-amber-200/60 bg-amber-50 text-amber-950",
  }[tone];

  return (
    <div className={`rounded-xl border px-3 py-2 ${toneClassName}`}>
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] opacity-70">{label}</p>
      <p className="mt-0.5 text-sm font-semibold">{value}</p>
    </div>
  );
}

function HeroInsightCard({
  eyebrow,
  title,
  description,
  tone = "neutral",
}: {
  eyebrow: string;
  title: string;
  description: string;
  tone?: "neutral" | "success" | "warning";
}) {
  const toneClassName = {
    neutral: "border-white/15 bg-white/10 text-white",
    success: "border-emerald-200/35 bg-emerald-50/95 text-emerald-950",
    warning: "border-amber-200/60 bg-amber-50/95 text-amber-950",
  }[tone];

  return (
    <div className={`rounded-[18px] border px-3 py-2.5 backdrop-blur ${toneClassName}`}>
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] opacity-70">{eyebrow}</p>
      <p className="mt-1 text-sm font-semibold leading-5">{title}</p>
      <p className="mt-0.5 text-xs leading-5 opacity-80">{description}</p>
    </div>
  );
}

function DetailSection({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <article className="overflow-hidden rounded-[22px] border border-[#d8dfd3] bg-white shadow-panel">
      <div className="border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(29,78,53,0.06),_rgba(255,255,255,0.94))] px-4 py-3">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">{eyebrow}</p>
        <p className="mt-1 text-base font-semibold text-gray-900">{title}</p>
        <p className="mt-1 text-sm leading-5 text-gray-600">{description}</p>
      </div>
      <div className="p-4">{children}</div>
    </article>
  );
}

function ActionCard({
  eyebrow,
  title,
  description,
  children,
  tone = "neutral",
}: {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
  tone?: "neutral" | "emerald" | "sky" | "amber";
}) {
  const toneClassName = {
    neutral: "border-[#d8dfd3] bg-white",
    emerald: "border-emerald-200 bg-[linear-gradient(180deg,_rgba(236,253,245,0.9),_#ffffff)]",
    sky: "border-sky-200 bg-[linear-gradient(180deg,_rgba(240,249,255,0.9),_#ffffff)]",
    amber: "border-amber-200 bg-[linear-gradient(180deg,_rgba(255,251,235,0.92),_#ffffff)]",
  }[tone];

  return (
    <article className={`rounded-[22px] border p-3.5 shadow-panel ${toneClassName}`}>
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">{eyebrow}</p>
      <p className="mt-1 text-base font-semibold text-gray-900">{title}</p>
      <p className="mt-1 text-sm leading-5 text-gray-600">{description}</p>
      <div className="mt-3">{children}</div>
    </article>
  );
}

function ActionField({
  htmlFor,
  label,
  children,
}: {
  htmlFor: string;
  label: string;
  children: ReactNode;
}) {
  return (
    <label htmlFor={htmlFor} className="grid gap-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
      <span>{label}</span>
      {children}
    </label>
  );
}

function DetailField({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="rounded-xl border border-gray-100 bg-[#fbfcfa] px-3 py-2">
      <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-gray-500">{label}</p>
      <p className="mt-1 break-words text-sm font-medium text-gray-900">{value || "-"}</p>
    </div>
  );
}

function HistoryCard({
  title,
  description,
  empty,
  count,
  children,
}: {
  title: string;
  description: string;
  empty: string;
  count: number;
  children: ReactNode[];
}) {
  return (
    <article className="rounded-[22px] border border-[#d8dfd3] bg-white p-3.5 shadow-panel">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">{title}</p>
          <p className="mt-1 text-sm leading-5 text-gray-600">{description}</p>
        </div>
        <span className="rounded-full bg-[#eef7ef] px-3 py-1 text-xs font-semibold text-[#1D4E35]">
          {count}
        </span>
      </div>
      <div className="mt-3 space-y-2">
        {children.length > 0 ? children : <p className="rounded-xl bg-gray-50 px-3 py-2 text-sm text-gray-500">{empty}</p>}
      </div>
    </article>
  );
}
