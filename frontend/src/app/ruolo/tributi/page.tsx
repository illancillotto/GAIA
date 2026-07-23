"use client";

import { FormEvent, Suspense, useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { RuoloModulePage } from "@/components/ruolo/module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon, LockIcon, SearchIcon } from "@/components/ui/icons";
import { getStoredAccessToken } from "@/lib/auth";
import { RuoloTributiFallback } from "./fallback";
import {
  addTributiNote,
  createTributiReminderBatch,
  createTributiPayment,
  createTributiYearManager,
  deleteTributiYearManager,
  downloadTributiReminderDocument,
  getTributiAvviso,
  getTributiSummary,
  listTributiReminderCandidates,
  listTributiAvvisi,
  listTributiYearManagers,
  updateTributiAvvisoStatus,
  updateTributiYearManager,
} from "@/lib/ruolo-api";
import type {
  RuoloTributiAvvisoDetailResponse,
  RuoloTributiAvvisoListItemResponse,
  RuoloTributiReminderBatchItemResponse,
  RuoloTributiReminderBatchResponse,
  RuoloTributiReminderCandidateResponse,
  RuoloTributiPaymentStatus,
  RuoloTributiSummaryResponse,
  RuoloTributiYearManagerResponse,
  RuoloTributiWorkflowStatus,
} from "@/types/ruolo";

const PAGE_SIZE = 25;
const FILTER_AUTOSUBMIT_DELAY_MS = 350;
const DEFAULT_MANAGER_KEY = "gaia";
const REMINDER_MIN_YEAR = 2022;
const DEFAULT_REMINDER_TEMPLATE_LABEL = "Template interno GAIA: Avviso_Sollecito_Template.docx";
const GAIA_REMINDER_TEMPLATE_PATH = "__gaia_proposal__";
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

function formatEuro(value: number | null | undefined): string {
  if (value == null) return "-";
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(value);
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  return new Intl.DateTimeFormat("it-IT", { dateStyle: "short" }).format(new Date(value));
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

function parseOptionalYear(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  /* c8 ignore next -- Year inputs are digit-normalised before submit; this keeps the helper defensive. */
  return Number.isInteger(parsed) ? parsed : null;
}

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

function canPrepareReminder(item: Pick<RuoloTributiAvvisoListItemResponse, "saldo_amount" | "payment_status">): boolean {
  return (item.saldo_amount ?? 0) > 0 && item.payment_status !== "paid";
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
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<RuoloTributiAvvisoDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [operationError, setOperationError] = useState<string | null>(null);
  const [operationMessage, setOperationMessage] = useState<string | null>(null);
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

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

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
  }, [anno, comune, managerKey, openOnly, page, paymentStatus, query, token, unlinked, workflowStatus]);

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
  }, [selectedId, token]);

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
        listTributiReminderCandidates(token, {
          anno_from: year,
          anno_to: year,
          comune: comune || undefined,
          q: query || undefined,
          manager_key: managerKey,
          page: 1,
          page_size: 80,
        }),
      ),
    )
      .then((responses) => {
        const mergedCandidates = mergeReminderCandidates(responses.map((response) => response.items));
        setCandidateItems(mergedCandidates);
        setCandidateTotal(mergedCandidates.length);
        setSelectedTaxCodes((current) => {
          const preserved = current.filter((taxCode) => mergedCandidates.some((item) => item.codice_fiscale === taxCode));
          if (preserved.length > 0) return preserved;
          return mergedCandidates.filter((item) => item.has_nas_folder).map((item) => item.codice_fiscale);
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

  useEffect(() => {
    if (!token) return;
    void refreshYearManagers(token);
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

  function closeDetailModal() {
    setSelectedId(null);
    setDetail(null);
    setOperationError(null);
    setOperationMessage(null);
  }

  function openReminderWizard() {
    setWizardOpen(true);
    setWizardStep(1);
    setWizardError(null);
    setBatchResult(null);
    setSelectedReminderYears(defaultReminderYears);
  }

  function closeReminderWizard() {
    setWizardOpen(false);
    setWizardStep(1);
    setWizardError(null);
    setBatchResult(null);
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
        codice_fiscale: selectedTaxCodes,
        filters: {
          anno_from: Math.min(...selectedReminderYears),
          anno_to: Math.max(...selectedReminderYears),
          years: selectedReminderYears,
          comune: comune || null,
          q: query || null,
          manager_key: managerKey,
        },
        template_path: null,
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
    try {
      for (const template of REMINDER_PREVIEW_TEMPLATES) {
        const result = await createTributiReminderBatch(token, {
          title: `Sollecito tributi ${taxCode} - ${template.label}`,
          codice_fiscale: [taxCode],
          filters: {
            anno_from: Math.min(...defaultReminderYears),
            anno_to: Math.max(...defaultReminderYears),
            years: defaultReminderYears,
            codice_fiscale: [taxCode],
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
          <button type="button" className="btn-primary" onClick={openReminderWizard}>
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
              <ModuleWorkspaceKpiTile label="Totale avvisi" value={formatEuro(summary.total_amount)} hint={`${summary.total_count} avvisi nel perimetro corrente`} />
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

          <YearManagersPanel
            managers={yearManagers}
            loading={yearManagersLoading}
            error={yearManagerError}
            message={yearManagerMessage}
            editingId={editingYearManagerId}
            form={yearManagerForm}
            modalOpen={yearManagersModalOpen}
            onFormChange={setYearManagerForm}
            onSubmit={submitYearManager}
            onEdit={editYearManager}
            onDelete={removeYearManager}
            onCancel={resetYearManagerForm}
            onOpen={() => setYearManagersModalOpen(true)}
            onClose={() => setYearManagersModalOpen(false)}
          />

          <section className="rounded-[28px] border border-[#d8dfd3] bg-white shadow-panel">
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
                    const reminderEnabled = canPrepareReminder(item);
                    const reminderBusy = previewGeneratingId === item.id;
                    return (
                    <article
                      key={item.id}
                      className={`grid w-full gap-3 rounded-[24px] border px-4 py-4 text-left transition hover:-translate-y-0.5 hover:shadow-sm xl:grid-cols-[minmax(0,1fr),auto] ${
                        selectedId === item.id ? "border-[#1D4E35] bg-[#f4faf6]" : "border-[#e6ebe5] bg-white"
                      }`}
                    >
                      <button type="button" onClick={() => setSelectedId(item.id)} className="grid min-w-0 gap-3 text-left md:grid-cols-[minmax(0,1fr),300px]">
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
                            Anno {item.anno_tributario} · CNC {item.codice_cnc} · CF/P.IVA {item.codice_fiscale_raw ?? "-"} · Utenza {item.codice_utenza ?? "-"}
                          </p>
                        </div>
                        <div className="grid grid-cols-3 gap-3 text-right text-xs md:min-w-[300px]">
                          <AmountCell label="Dovuto" value={item.importo_totale_euro} />
                          <AmountCell label="Pagato" value={item.paid_amount} />
                          <AmountCell label="Saldo" value={item.saldo_amount} strong />
                        </div>
                      </button>
                      <div className="flex flex-wrap items-center justify-end gap-2 xl:min-w-[210px]">
                        <button type="button" className="btn-secondary" onClick={() => setSelectedId(item.id)}>
                          Dettaglio
                        </button>
                        {item.subject_id ? (
                          <button type="button" className="btn-secondary" onClick={() => openSubjectQuickView(item)}>
                            Dettaglio soggetto
                          </button>
                        ) : (
                          <button type="button" className="btn-secondary" disabled title="Avviso non collegato a un soggetto GAIA">
                            Dettaglio soggetto
                          </button>
                        )}
                        <button
                          type="button"
                          className="btn-primary"
                          onClick={() => prepareReminderPreview(item)}
                          disabled={!reminderEnabled || reminderBusy}
                          title={reminderEnabled ? "Predisponi e apri la preview del PDF" : "Disponibile solo per avvisi con saldo aperto"}
                        >
                          {reminderBusy ? "Creo..." : "Avviso sollecito"}
                        </button>
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
          <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-sm">
            <div className="flex max-h-[94vh] w-full max-w-[1500px] flex-col overflow-hidden rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
              <div className="flex items-start justify-between gap-4 border-b border-gray-100 px-6 py-4">
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Dettaglio tributo</p>
                  <p className="mt-1 truncate text-lg font-semibold text-gray-900">
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
              <div className="overflow-y-auto bg-[#f7f9f5] p-5">
                <TributiDetailPanel
                  detail={detail}
                  loading={detailLoading}
                  operationError={operationError}
                  operationMessage={operationMessage}
                  onSubmitPayment={submitPayment}
                  onSubmitStatus={submitStatus}
                  onSubmitNote={submitNote}
                  onPrepareReminder={prepareReminderPreview}
                  onOpenSubject={openSubjectQuickView}
                  reminderGenerating={detail ? previewGeneratingId === detail.id : false}
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

  return (
    <>
      <section className="rounded-[24px] border border-[#d8dfd3] bg-white px-5 py-4 shadow-panel">
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
                activeManagers.slice(0, 4).map((manager) => (
                  <span key={manager.id} className="rounded-full bg-[#eef7ef] px-3 py-1 text-xs font-semibold text-[#1D4E35]">
                    {formatYearRange(manager)} · {manager.manager_label}
                  </span>
                ))
              )}
              {activeManagers.length > 4 ? (
                <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-500">+{activeManagers.length - 4}</span>
              ) : null}
            </div>
          </div>
          <div className="flex flex-wrap items-start justify-end gap-2">
            <button type="button" className="btn-secondary" onClick={onOpen}>
              Gestisci regole
            </button>
          </div>
        </div>

        {error ? <div className="mt-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm font-medium text-red-700">{error}</div> : null}
        {message ? <div className="mt-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm font-medium text-emerald-700">{message}</div> : null}
      </section>

      {modalOpen ? (
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
  onPrepareReminder,
  onOpenSubject,
  reminderGenerating,
}: {
  detail: RuoloTributiAvvisoDetailResponse | null;
  loading: boolean;
  operationError: string | null;
  operationMessage: string | null;
  onSubmitPayment: (event: FormEvent<HTMLFormElement>) => void;
  onSubmitStatus: (event: FormEvent<HTMLFormElement>) => void;
  onSubmitNote: (event: FormEvent<HTMLFormElement>) => void;
  onPrepareReminder: (item: RuoloTributiAvvisoListItemResponse) => void;
  onOpenSubject: (item: RuoloTributiAvvisoListItemResponse) => void;
  reminderGenerating: boolean;
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

  return (
    <section className="space-y-5">
      <div className="overflow-hidden rounded-[26px] border border-[#cddacc] bg-[#183325] text-white shadow-panel">
        <div className="relative p-5 md:p-6">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(202,224,173,0.32),_transparent_34%),linear-gradient(135deg,_rgba(29,78,53,0.96),_rgba(24,51,37,1))]" />
          <div className="relative grid gap-5 xl:grid-cols-[minmax(0,1fr),360px]">
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
                {!detail.is_linked ? <span className="rounded-full border border-amber-200/60 bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">Orfano GAIA</span> : null}
              </div>
              <p className="mt-4 text-2xl font-semibold tracking-tight">{detail.display_name ?? detail.nominativo_raw ?? "Avviso selezionato"}</p>
              <p className="mt-2 text-sm leading-6 text-white/75">
                CNC {detail.codice_cnc} · Anno {detail.anno_tributario} · Utenza {detail.codice_utenza ?? "-"} · CF/P.IVA {detail.codice_fiscale_raw ?? "-"}
              </p>
              {detail.capacitas_url ? (
                <Link className="mt-4 inline-flex rounded-full border border-white/25 bg-white/10 px-4 py-2 text-sm font-semibold text-white hover:bg-white/20" href={detail.capacitas_url} target="_blank" rel="noreferrer">
                  Apri avviso CapaciTas
                </Link>
              ) : null}
              <button
                type="button"
                className="ml-0 mt-3 inline-flex rounded-full border border-[#cfe2b8] bg-[#e9f2da] px-4 py-2 text-sm font-semibold text-[#183325] hover:bg-white disabled:cursor-not-allowed disabled:opacity-60 sm:ml-2"
                onClick={() => onPrepareReminder(detail)}
                disabled={!reminderEnabled || reminderGenerating}
              >
                {reminderGenerating ? "Creazione avviso..." : "Preview avviso sollecito"}
              </button>
            </div>
            <div className="grid gap-2 sm:grid-cols-3 xl:grid-cols-1">
              <DetailMetric label="Dovuto" value={formatEuro(detail.importo_totale_euro)} />
              <DetailMetric label="Pagato" value={formatEuro(detail.paid_amount)} tone="success" />
              <DetailMetric label="Saldo" value={formatEuro(detail.saldo_amount)} tone={saldo > 0 ? "warning" : "success"} />
            </div>
          </div>
        </div>
      </div>

      {operationError ? <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">{operationError}</div> : null}
      {operationMessage ? <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700">{operationMessage}</div> : null}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr),360px]">
        <div className="space-y-4">
          <article className="rounded-[24px] border border-[#d8dfd3] bg-white p-4 shadow-panel">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Posizione</p>
                <p className="mt-1 text-base font-semibold text-gray-900">Dati anagrafici, importi e CapaciTas</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {detail.capacitas_url ? (
                  <Link className="btn-secondary" href={detail.capacitas_url} target="_blank" rel="noreferrer">
                    CapaciTas
                  </Link>
                ) : null}
                <Link className="btn-secondary" href={`/ruolo/tributi/${detail.id}`}>
                  Pagina dettaglio
                </Link>
                {detail.subject_id ? (
                  <button type="button" className="btn-secondary" onClick={() => onOpenSubject(detail)}>
                    Dettaglio soggetto
                  </button>
                ) : (
                  <button type="button" className="btn-secondary" disabled title="Avviso non collegato a un soggetto GAIA">
                    Dettaglio soggetto
                  </button>
                )}
                <button type="button" className="btn-primary" onClick={() => onPrepareReminder(detail)} disabled={!reminderEnabled || reminderGenerating}>
                  {reminderGenerating ? "Creo..." : "Avviso sollecito"}
                </button>
              </div>
            </div>
            <div className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
              <DetailField label="Domicilio" value={detail.domicilio_raw} />
              <DetailField label="Residenza" value={detail.residenza_raw} />
              <DetailField label="0648" value={formatEuro(detail.importo_totale_0648)} />
              <DetailField label="0985" value={formatEuro(detail.importo_totale_0985)} />
              <DetailField label="0668" value={formatEuro(detail.importo_totale_0668)} />
              <DetailField label="Ultimo pagamento" value={formatDate(detail.last_payment_at)} />
              <DetailField label="Codice avviso CapaciTas" value={detail.capacitas_avviso_code} />
              <DetailField label="Collegamento GAIA" value={detail.is_linked ? "Collegato" : "Da collegare"} />
              <DetailField label="Gestore annualita" value={detail.annuality_manager_label} />
              <DetailField label="Policy calcolo" value={detail.calculation_policy} />
            </div>
          </article>

          <article className="rounded-[24px] border border-[#d8dfd3] bg-white p-4 shadow-panel">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">PEC e consegna</p>
                <p className="mt-1 text-base font-semibold text-gray-900">Ricevute inCASS collegate all&apos;avviso</p>
              </div>
              {detail.mailing_delivery?.receipt_groups.length ? (
                <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                  {detail.mailing_delivery.receipt_groups.join(", ")}
                </span>
              ) : null}
            </div>
            {detail.mailing_delivery ? (
              <div className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                <DetailField label="PEC destinatario" value={detail.mailing_delivery.pec_recipient} />
                <DetailField label="Data consegna" value={formatDeliveryDate(detail.mailing_delivery.delivered_at)} />
                <DetailField label="Data accettazione" value={formatDeliveryDate(detail.mailing_delivery.accepted_at)} />
                <DetailField label="Ricevute archiviate" value={String(detail.mailing_delivery.receipt_documents_count)} />
                <DetailField label="Stato PEC" value={detail.mailing_delivery.delivery_status} />
                <DetailField label="Avviso inCASS" value={detail.mailing_delivery.source_notice_id} />
              </div>
            ) : (
              <p className="mt-3 text-sm text-gray-500">Nessuna ricevuta PEC di consegna collegata all&apos;avviso.</p>
            )}
          </article>

          <article className="rounded-[24px] border border-[#d8dfd3] bg-white p-4 shadow-panel">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Azioni rapide</p>
            <div className="mt-4 grid gap-3 xl:grid-cols-2">
              <form className="rounded-2xl border border-[#e4ebe2] bg-[#fbfcfa] p-3" onSubmit={onSubmitPayment}>
                <p className="text-sm font-semibold text-gray-900">Registra pagamento</p>
                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                  <input name="amount" inputMode="decimal" placeholder="Importo" className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[#8CB39D]" />
                  <input name="paid_at" type="date" className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[#8CB39D]" />
                  <input name="payment_reference" placeholder="Riferimento" className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[#8CB39D]" />
                  <input name="payment_method" placeholder="Metodo" className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[#8CB39D]" />
                </div>
                <button type="submit" className="btn-secondary mt-3 w-full">Salva pagamento</button>
              </form>

              <form className="rounded-2xl border border-[#e4ebe2] bg-[#fbfcfa] p-3" onSubmit={onSubmitStatus}>
                <p className="text-sm font-semibold text-gray-900">Stato operativo e CapaciTas</p>
                <div className="mt-3 grid gap-2">
                  <select name="workflow_status" defaultValue={detail.workflow_status ?? ""} className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[#8CB39D]">
                    <option value="">Nessuno stato operativo</option>
                    {WORKFLOW_STATUS_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                  </select>
                  <input name="capacitas_url" defaultValue={detail.capacitas_url ?? ""} placeholder="Link CapaciTas" className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[#8CB39D]" />
                  <input name="capacitas_avviso_code" defaultValue={detail.capacitas_avviso_code ?? ""} placeholder="Codice avviso CapaciTas" className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[#8CB39D]" />
                </div>
                <button type="submit" className="btn-secondary mt-3 w-full">Aggiorna stato</button>
              </form>
            </div>
          </article>

          <form className="rounded-[24px] border border-[#d8dfd3] bg-white p-4 shadow-panel" onSubmit={onSubmitNote}>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Nota interna</p>
            <div className="mt-3 grid gap-3 md:grid-cols-[minmax(0,1fr),auto]">
              <textarea name="body" rows={3} placeholder="Es. utente contattato, pratica contestata..." className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm outline-none focus:border-[#8CB39D]" />
              <button type="submit" className="btn-secondary self-end">Salva nota</button>
            </div>
          </form>
        </div>

        <div className="space-y-4">
          <HistoryCard title="Pagamenti registrati" empty="Nessun pagamento registrato.">
            {detail.payments.map((payment) => (
              <div key={payment.id} className="rounded-2xl border border-gray-100 bg-[#fbfcfa] px-4 py-3 text-sm">
                <div className="flex items-start justify-between gap-3">
                  <p className="font-semibold text-gray-900">{formatEuro(payment.amount)}</p>
                  <span className="rounded-full bg-gray-100 px-2.5 py-1 text-[11px] font-semibold text-gray-600">{payment.status}</span>
                </div>
                <p className="mt-1 text-xs text-gray-500">{formatDate(payment.paid_at)} · {payment.payment_reference ?? payment.source}</p>
              </div>
            ))}
          </HistoryCard>

          <HistoryCard title="Note" empty="Nessuna nota.">
            {detail.notes.map((note) => (
              <div key={note.id} className="rounded-2xl border border-gray-100 bg-[#fbfcfa] px-4 py-3 text-sm">
                <p className="text-gray-800">{note.body}</p>
                <p className="mt-2 text-xs text-gray-500">{formatDate(note.created_at)}</p>
              </div>
            ))}
          </HistoryCard>
        </div>
      </div>
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

function buildPdfPreviewUrlWithoutToolbar(objectUrl: string): string {
  const separator = objectUrl.includes("#") ? "&" : "#";
  return `${objectUrl}${separator}toolbar=0&navpanes=0&zoom=125`;
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
  const activeDocument = documents.find((document) => document.key === activeKey) ?? documents[0];
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
  const pdfPreviewUrl = isPdf ? buildPdfPreviewUrlWithoutToolbar(objectUrl) : objectUrl;

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
        {documents.length > 1 ? (
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
        ) : null}
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
    <div className={`rounded-2xl border px-3 py-2.5 ${toneClassName}`}>
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] opacity-70">{label}</p>
      <p className="mt-1 text-base font-semibold">{value}</p>
    </div>
  );
}

function DetailField({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="rounded-2xl border border-gray-100 bg-[#fbfcfa] px-3 py-2.5">
      <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-gray-500">{label}</p>
      <p className="mt-1 break-words text-sm font-medium text-gray-900">{value || "-"}</p>
    </div>
  );
}

function HistoryCard({ title, empty, children }: { title: string; empty: string; children: ReactNode[] }) {
  return (
    <article className="rounded-[24px] border border-[#d8dfd3] bg-white p-4 shadow-panel">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">{title}</p>
      <div className="mt-3 space-y-2">
        {children.length > 0 ? children : <p className="rounded-2xl bg-gray-50 px-4 py-3 text-sm text-gray-500">{empty}</p>}
      </div>
    </article>
  );
}
