"use client";

import { FormEvent, Suspense, useEffect, useMemo, useState } from "react";
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
import {
  addTributiNote,
  createTributiPayment,
  getTributiAvviso,
  listTributiAvvisi,
  updateTributiAvvisoStatus,
} from "@/lib/ruolo-api";
import type {
  RuoloTributiAvvisoDetailResponse,
  RuoloTributiAvvisoListItemResponse,
  RuoloTributiPaymentStatus,
  RuoloTributiWorkflowStatus,
} from "@/types/ruolo";

const PAGE_SIZE = 25;

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

  function applyFilters() {
    const qs = new URLSearchParams();
    if (filterQuery.trim()) qs.set("q", filterQuery.trim());
    if (filterAnno.trim()) qs.set("anno", filterAnno.trim());
    if (filterComune.trim()) qs.set("comune", filterComune.trim());
    if (filterPaymentStatus) qs.set("payment_status", filterPaymentStatus);
    if (filterWorkflowStatus) qs.set("workflow_status", filterWorkflowStatus);
    if (!filterOpenOnly) qs.set("open_only", "false");
    if (filterUnlinked) qs.set("unlinked", "true");
    qs.set("page", "1");
    router.replace(`/ruolo/tributi?${qs}`);
  }

  function resetFilters() {
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
        </div>
      }
    >
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr),420px]">
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
                  title="Excel CapaciTas"
                  description="Il parser definitivo resta in attesa del tracciato reale; intanto sono disponibili pagamenti manuali e note."
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
                type="number"
                placeholder="Anno"
                value={filterAnno}
                onChange={(event) => setFilterAnno(event.target.value)}
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
              <button type="button" className="btn-secondary" onClick={applyFilters}>
                Applica
              </button>
              <button type="button" className="btn-secondary" onClick={resetFilters}>
                Reset
              </button>
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
                  {items.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => setSelectedId(item.id)}
                      className={`grid w-full gap-3 rounded-[24px] border px-4 py-4 text-left transition hover:-translate-y-0.5 hover:shadow-sm md:grid-cols-[minmax(0,1fr),auto] ${
                        selectedId === item.id ? "border-[#1D4E35] bg-[#f4faf6]" : "border-[#e6ebe5] bg-white"
                      }`}
                    >
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
                  ))}
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

        <aside className="xl:sticky xl:top-6 xl:self-start">
          <TributiDetailPanel
            detail={detail}
            loading={detailLoading}
            operationError={operationError}
            operationMessage={operationMessage}
            onSubmitPayment={submitPayment}
            onSubmitStatus={submitStatus}
            onSubmitNote={submitNote}
          />
        </aside>
      </div>
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

function TributiDetailPanel({
  detail,
  loading,
  operationError,
  operationMessage,
  onSubmitPayment,
  onSubmitStatus,
  onSubmitNote,
}: {
  detail: RuoloTributiAvvisoDetailResponse | null;
  loading: boolean;
  operationError: string | null;
  operationMessage: string | null;
  onSubmitPayment: (event: FormEvent<HTMLFormElement>) => void;
  onSubmitStatus: (event: FormEvent<HTMLFormElement>) => void;
  onSubmitNote: (event: FormEvent<HTMLFormElement>) => void;
}) {
  if (loading) {
    return <section className="panel-card"><p className="text-sm text-gray-400">Caricamento dettaglio...</p></section>;
  }
  if (!detail) {
    return (
      <section className="panel-card">
        <p className="section-title">Dettaglio tributo</p>
        {operationError ? <div className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{operationError}</div> : null}
        <p className="section-copy">Seleziona un avviso dalla lista per registrare pagamenti, note e link CapaciTas.</p>
      </section>
    );
  }

  return (
    <section className="space-y-4 rounded-[28px] border border-[#d8dfd3] bg-white p-5 shadow-panel">
      <div>
        <p className="section-title">{detail.display_name ?? detail.nominativo_raw ?? "Avviso selezionato"}</p>
        <p className="mt-1 text-sm text-gray-500">CNC {detail.codice_cnc} · Anno {detail.anno_tributario}</p>
      </div>

      <div className="grid grid-cols-3 gap-2 rounded-2xl bg-[#f6f8f4] p-3 text-xs">
        <AmountCell label="Dovuto" value={detail.importo_totale_euro} />
        <AmountCell label="Pagato" value={detail.paid_amount} />
        <AmountCell label="Saldo" value={detail.saldo_amount} strong />
      </div>

      {operationError ? <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{operationError}</div> : null}
      {operationMessage ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{operationMessage}</div> : null}

      <form className="space-y-3 rounded-2xl border border-gray-100 p-4" onSubmit={onSubmitPayment}>
        <p className="text-sm font-semibold text-gray-900">Registra pagamento</p>
        <input name="amount" inputMode="decimal" placeholder="Importo" className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none" />
        <input name="paid_at" type="date" className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none" />
        <input name="payment_reference" placeholder="Riferimento pagamento" className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none" />
        <input name="payment_method" placeholder="Metodo, es. bonifico" className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none" />
        <button type="submit" className="btn-secondary w-full">Salva pagamento</button>
      </form>

      <form className="space-y-3 rounded-2xl border border-gray-100 p-4" onSubmit={onSubmitStatus}>
        <p className="text-sm font-semibold text-gray-900">Stato operativo e CapaciTas</p>
        <select name="workflow_status" defaultValue={detail.workflow_status ?? ""} className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none">
          <option value="">Nessuno stato operativo</option>
          {WORKFLOW_STATUS_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>
        <input name="capacitas_url" defaultValue={detail.capacitas_url ?? ""} placeholder="Link CapaciTas" className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none" />
        <input name="capacitas_avviso_code" defaultValue={detail.capacitas_avviso_code ?? ""} placeholder="Codice avviso CapaciTas" className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none" />
        <div className="flex gap-2">
          <button type="submit" className="btn-secondary flex-1">Aggiorna stato</button>
          {detail.capacitas_url ? <Link className="btn-secondary flex-1 text-center" href={detail.capacitas_url} target="_blank" rel="noreferrer">Apri CapaciTas</Link> : null}
        </div>
      </form>

      <Link className="btn-secondary block text-center" href={`/ruolo/tributi/${detail.id}`}>
        Apri pagina dettaglio
      </Link>

      <form className="space-y-3 rounded-2xl border border-gray-100 p-4" onSubmit={onSubmitNote}>
        <p className="text-sm font-semibold text-gray-900">Nota interna</p>
        <textarea name="body" rows={3} placeholder="Es. utente contattato, pratica contestata..." className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none" />
        <button type="submit" className="btn-secondary w-full">Salva nota</button>
      </form>

      <div className="rounded-2xl border border-gray-100 p-4">
        <p className="text-sm font-semibold text-gray-900">Pagamenti registrati</p>
        <div className="mt-3 space-y-2">
          {detail.payments.length === 0 ? <p className="text-sm text-gray-500">Nessun pagamento registrato.</p> : detail.payments.map((payment) => (
            <div key={payment.id} className="rounded-xl bg-gray-50 px-3 py-2 text-sm">
              <p className="font-medium text-gray-900">{formatEuro(payment.amount)} · {payment.status}</p>
              <p className="text-xs text-gray-500">{formatDate(payment.paid_at)} · {payment.payment_reference ?? payment.source}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-2xl border border-gray-100 p-4">
        <p className="text-sm font-semibold text-gray-900">Note</p>
        <div className="mt-3 space-y-2">
          {detail.notes.length === 0 ? <p className="text-sm text-gray-500">Nessuna nota.</p> : detail.notes.map((note) => (
            <div key={note.id} className="rounded-xl bg-gray-50 px-3 py-2 text-sm">
              <p className="text-gray-800">{note.body}</p>
              <p className="mt-1 text-xs text-gray-500">{formatDate(note.created_at)}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export function RuoloTributiFallback() {
  return (
    <RuoloModulePage
      title="Tributi Ruolo"
      description="Tracciamento pagamenti, scoperti, note operative e link CapaciTas sugli avvisi a ruolo."
      breadcrumb="Tributi"
      requiredSection="ruolo.tributi.view"
    >
      <p className="text-sm text-gray-400">Caricamento sezione tributi...</p>
    </RuoloModulePage>
  );
}
