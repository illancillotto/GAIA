"use client";

import { FormEvent, Suspense, useEffect, useMemo, useState, type ReactNode } from "react";
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
  downloadTributiReminderDocument,
  getTributiAvviso,
  listTributiReminderCandidates,
  listTributiAvvisi,
  updateTributiAvvisoStatus,
} from "@/lib/ruolo-api";
import type {
  RuoloTributiAvvisoDetailResponse,
  RuoloTributiAvvisoListItemResponse,
  RuoloTributiReminderBatchItemResponse,
  RuoloTributiReminderBatchResponse,
  RuoloTributiReminderCandidateResponse,
  RuoloTributiPaymentStatus,
  RuoloTributiWorkflowStatus,
} from "@/types/ruolo";

const PAGE_SIZE = 25;
const FILTER_AUTOSUBMIT_DELAY_MS = 350;
const DEFAULT_REMINDER_TEMPLATE_LABEL = "Template interno GAIA: Avviso_Sollecito_22.23_R1_da_mail_ordinarie.docx";

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

type SubjectQuickView = {
  id: string;
  label: string | null;
};

function buildFiltersSearchParams({
  query,
  anno,
  comune,
  paymentStatus,
  workflowStatus,
  openOnly,
  unlinked,
}: {
  query: string;
  anno: string;
  comune: string;
  paymentStatus: string;
  workflowStatus: string;
  openOnly: boolean;
  unlinked: boolean;
}) {
  const qs = new URLSearchParams();
  if (query.trim()) qs.set("q", query.trim());
  if (anno.trim()) qs.set("anno", anno.trim());
  if (comune.trim()) qs.set("comune", comune.trim());
  if (paymentStatus) qs.set("payment_status", paymentStatus);
  if (workflowStatus) qs.set("workflow_status", workflowStatus);
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
  const [manualTaxCode, setManualTaxCode] = useState("");
  const [batchResult, setBatchResult] = useState<RuoloTributiReminderBatchResponse | null>(null);
  const [batchGenerating, setBatchGenerating] = useState(false);
  const [previewItem, setPreviewItem] = useState<RuoloTributiReminderBatchItemResponse | null>(null);
  const [previewObjectUrl, setPreviewObjectUrl] = useState<string | null>(null);
  const [previewGeneratingId, setPreviewGeneratingId] = useState<string | null>(null);
  const [subjectQuickView, setSubjectQuickView] = useState<SubjectQuickView | null>(null);

  const query = searchParams.get("q")?.trim() || "";
  const anno = searchParams.get("anno")?.trim() || "";
  const comune = searchParams.get("comune")?.trim() || "";
  const paymentStatus = searchParams.get("payment_status")?.trim() || "";
  const workflowStatus = searchParams.get("workflow_status")?.trim() || "";
  const openOnly = searchParams.get("open_only") !== "false";
  const unlinked = searchParams.get("unlinked") === "true";
  const page = Math.max(1, Number(searchParams.get("page") ?? 1));

  const [filterQuery, setFilterQuery] = useState(query);
  const [filterAnno, setFilterAnno] = useState(anno);
  const [filterComune, setFilterComune] = useState(comune);
  const [filterPaymentStatus, setFilterPaymentStatus] = useState(paymentStatus);
  const [filterWorkflowStatus, setFilterWorkflowStatus] = useState(workflowStatus);
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
    setFilterOpenOnly(openOnly);
    setFilterUnlinked(unlinked);
  }, [anno, comune, openOnly, paymentStatus, query, unlinked, workflowStatus]);

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
    filterPaymentStatus,
    filterQuery,
    filterUnlinked,
    filterWorkflowStatus,
    anno,
    comune,
    openOnly,
    paymentStatus,
    query,
    router,
    unlinked,
    workflowStatus,
  ]);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    setError(null);
    listTributiAvvisi(token, {
      anno: anno ? Number(anno) : undefined,
      comune: comune || undefined,
      q: query || undefined,
      payment_status: paymentStatus || undefined,
      workflow_status: workflowStatus || undefined,
      open_only: openOnly,
      unlinked,
      page,
      page_size: PAGE_SIZE,
    })
      .then((response) => {
        setItems(response.items);
        setTotal(response.total);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Errore caricamento tributi"))
      .finally(() => setLoading(false));
  }, [anno, comune, openOnly, page, paymentStatus, query, token, unlinked, workflowStatus]);

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
    setCandidatesLoading(true);
    setWizardError(null);
    listTributiReminderCandidates(token, {
      anno_from: anno ? Number(anno) : undefined,
      anno_to: anno ? Number(anno) : undefined,
      comune: comune || undefined,
      q: query || undefined,
      page: 1,
      page_size: 80,
    })
      .then((response) => {
        setCandidateItems(response.items);
        setCandidateTotal(response.total);
        setSelectedTaxCodes((current) =>
          current.length > 0 ? current : response.items.filter((item) => item.has_nas_folder).map((item) => item.codice_fiscale),
        );
      })
      .catch((err: unknown) => setWizardError(err instanceof Error ? err.message : "Errore caricamento utenze sollecitabili"))
      .finally(() => setCandidatesLoading(false));
  }, [anno, comune, query, token, wizardOpen]);

  useEffect(() => {
    return () => {
      if (previewObjectUrl) URL.revokeObjectURL(previewObjectUrl);
    };
  }, [previewObjectUrl]);

  function resetFilters() {
    setFilterQuery("");
    setFilterAnno("");
    setFilterComune("");
    setFilterPaymentStatus("");
    setFilterWorkflowStatus("");
    setFilterOpenOnly(true);
    setFilterUnlinked(false);
    router.push("/ruolo/tributi?page=1");
  }

  function setPage(nextPage: number) {
    const qs = new URLSearchParams(searchParams.toString());
    qs.set("page", String(nextPage));
    router.push(`/ruolo/tributi?${qs}`);
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
  }

  function closeReminderWizard() {
    setWizardOpen(false);
    setWizardStep(1);
    setWizardError(null);
    setBatchResult(null);
    setManualTaxCode("");
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

  async function generateReminderBatch() {
    /* c8 ignore next -- Defensive guard: wizard actions are not reachable before the token is loaded. */
    if (!token) return;
    /* c8 ignore next 3 -- Defensive guard: the wizard disables progression when no tax code is selected. */
    if (selectedTaxCodes.length === 0) {
      setWizardError("Seleziona almeno una utenza o aggiungi un codice fiscale manualmente.");
      return;
    }
    setBatchGenerating(true);
    setWizardError(null);
    try {
      const result = await createTributiReminderBatch(token, {
        title: `Solleciti tributi ${new Date().toLocaleDateString("it-IT")}`,
        codice_fiscale: selectedTaxCodes,
        filters: {
          anno_from: anno || null,
          anno_to: anno || null,
          comune: comune || null,
          q: query || null,
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
    /* c8 ignore next -- The preview modal is rendered only when an object URL exists. */
    if (previewObjectUrl) URL.revokeObjectURL(previewObjectUrl);
    setPreviewObjectUrl(null);
    setPreviewItem(null);
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
    setPreviewGeneratingId(item.id);
    setOperationError(null);
    setOperationMessage(null);
    try {
      const result = await createTributiReminderBatch(token, {
        title: `Sollecito tributi ${taxCode}`,
        codice_fiscale: [taxCode],
        filters: { codice_fiscale: [taxCode] },
        template_path: null,
        notes: `Preview sollecito generata da Elenco tributi per avviso ${item.codice_cnc}.`,
      });
      const generatedItem = result.items.find((batchItem) => batchItem.status === "generated" && batchItem.download_url) ?? result.items[0];
      if (!generatedItem?.download_url) {
        throw new Error(generatedItem?.error_detail || "PDF sollecito non disponibile per la preview.");
      }
      const blob = await downloadTributiReminderDocument(token, generatedItem.download_url);
      const nextObjectUrl = URL.createObjectURL(blob);
      if (previewObjectUrl) URL.revokeObjectURL(previewObjectUrl);
      setPreviewItem(generatedItem);
      setPreviewObjectUrl(nextObjectUrl);
      setOperationMessage("Avviso di sollecito predisposto.");
    } catch (err) {
      setOperationError(err instanceof Error ? err.message : "Errore predisposizione avviso di sollecito");
    } finally {
      setPreviewGeneratingId(null);
    }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const pageDue = useMemo(() => items.reduce((sum, item) => sum + (item.importo_totale_euro ?? 0), 0), [items]);
  const pagePaid = useMemo(() => items.reduce((sum, item) => sum + item.paid_amount, 0), [items]);
  const pageOpen = useMemo(() => items.reduce((sum, item) => sum + (item.saldo_amount ?? 0), 0), [items]);
  const pageMorosi = useMemo(
    () => items.filter((item) => item.payment_status === "unpaid" || item.payment_status === "partial").length,
    [items],
  );

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
              <ModuleWorkspaceKpiTile label="Risultati" value={total} hint={`Pagina ${page}${totalPages ? ` di ${totalPages}` : ""}`} />
              <ModuleWorkspaceKpiTile label="Dovuto pagina" value={formatEuro(pageDue)} hint="Importi avvisi" />
              <ModuleWorkspaceKpiTile label="Pagato pagina" value={formatEuro(pagePaid)} hint="Pagamenti validi" variant="emerald" />
              <ModuleWorkspaceKpiTile label="Scoperto pagina" value={formatEuro(pageOpen)} hint={`${pageMorosi} posizioni aperte`} variant={pageOpen > 0 ? "amber" : "default"} />
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

          <section className="rounded-[28px] border border-[#d8dfd3] bg-white shadow-panel">
            <div className="border-b border-[#edf1eb] px-6 py-5">
              <p className="inline-flex items-center gap-2 rounded-full bg-[#e8f2ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
                <DocumentIcon className="h-3.5 w-3.5" />
                Elenco tributi
              </p>
              <p className="mt-3 text-lg font-semibold text-gray-900">Avvisi e saldo pagamento.</p>
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

        {previewItem && previewObjectUrl ? (
          <ReminderPreviewModal
            item={previewItem}
            objectUrl={previewObjectUrl}
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
            manualTaxCode={manualTaxCode}
            step={wizardStep}
            error={wizardError}
            batchResult={batchResult}
            generating={batchGenerating}
            onClose={closeReminderWizard}
            onStepChange={setWizardStep}
            onToggleTaxCode={toggleTaxCode}
            onManualTaxCodeChange={setManualTaxCode}
            onAddManualTaxCode={addManualTaxCode}
            onGenerate={generateReminderBatch}
          />
        ) : null}
      </>
    </RuoloModulePage>
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
  manualTaxCode,
  step,
  error,
  batchResult,
  generating,
  onClose,
  onStepChange,
  onToggleTaxCode,
  onManualTaxCodeChange,
  onAddManualTaxCode,
  onGenerate,
}: {
  candidates: RuoloTributiReminderCandidateResponse[];
  candidatesLoading: boolean;
  candidateTotal: number;
  selectedTaxCodes: string[];
  manualTaxCode: string;
  step: 1 | 2 | 3;
  error: string | null;
  batchResult: RuoloTributiReminderBatchResponse | null;
  generating: boolean;
  onClose: () => void;
  onStepChange: (step: 1 | 2 | 3) => void;
  onToggleTaxCode: (taxCode: string) => void;
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
                    <p className="mt-1 text-sm text-gray-600">{candidateTotal} utenze aperte trovate dai filtri pagina.</p>
                  </div>
                  <button type="button" className="btn-secondary" onClick={() => onStepChange(2)} disabled={selectedTaxCodes.length === 0}>
                    Avanti
                  </button>
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
            </div>
          </article>

          <article className="rounded-[24px] border border-[#d8dfd3] bg-white p-4 shadow-panel">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">PEC e consegna</p>
                <p className="mt-1 text-base font-semibold text-gray-900">Ricevute inCASS collegate all'avviso</p>
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
              <p className="mt-3 text-sm text-gray-500">Nessuna ricevuta PEC di consegna collegata all'avviso.</p>
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

function ReminderPreviewModal({
  item,
  objectUrl,
  onClose,
}: {
  item: RuoloTributiReminderBatchItemResponse;
  objectUrl: string;
  onClose: () => void;
}) {
  const filename = item.generated_document_path?.split("/").pop() || `${item.codice_fiscale}_avviso_sollecito.pdf`;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-[#0f172a]/65 px-4 py-6 backdrop-blur-sm">
      <div className="flex max-h-[95vh] w-full max-w-[1320px] flex-col overflow-hidden rounded-[30px] border border-[#d6dfd2] bg-white shadow-[0_34px_110px_rgba(15,23,42,0.34)]">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-[#e5eadf] bg-[#203829] px-6 py-5 text-white">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#cfe2b8]">Preview avviso sollecito</p>
            <h2 className="mt-2 truncate text-xl font-semibold">{item.display_name ?? item.codice_fiscale}</h2>
            <p className="mt-1 break-all text-xs text-white/70">{item.generated_document_path ?? filename}</p>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            <a className="btn-secondary border-white/20 bg-white text-[#203829] hover:bg-[#eef7ef]" href={objectUrl} download={filename}>
              Scarica PDF
            </a>
            <button type="button" className="btn-secondary border-white/20 bg-white/10 text-white hover:bg-white/20" onClick={onClose}>
              Chiudi
            </button>
          </div>
        </div>
        <div className="grid gap-3 border-b border-[#edf1eb] bg-[#f8faf5] px-6 py-3 md:grid-cols-4">
          <DetailField label="CF/P.IVA" value={item.codice_fiscale} />
          <DetailField label="Anni" value={item.years_json?.join(", ")} />
          <DetailField label="Saldo" value={formatEuro(item.saldo_amount)} />
          <DetailField label="Stato" value={item.status} />
        </div>
        <div className="min-h-0 flex-1 bg-[#eef2ea] p-4">
          <iframe title="Preview PDF avviso sollecito" src={objectUrl} className="h-[70vh] w-full rounded-2xl border border-[#d6dfd2] bg-white" />
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
