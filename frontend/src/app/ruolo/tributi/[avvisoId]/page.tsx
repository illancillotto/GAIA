"use client";

import { FormEvent, Suspense, useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { RuoloModulePage } from "@/components/ruolo/module-page";
import { DocumentIcon, LockIcon } from "@/components/ui/icons";
import { getStoredAccessToken } from "@/lib/auth";
import {
  addTributiNote,
  createTributiReminder,
  createTributiPayment,
  downloadTributiReminderDocument,
  getTributiAvviso,
  listTributiReminders,
  updateTributiAvvisoStatus,
} from "@/lib/ruolo-api";
import type {
  RuoloTributiAvvisoDetailResponse,
  RuoloTributiPaymentStatus,
  RuoloTributiReminderResponse,
  RuoloTributiWorkflowStatus,
} from "@/types/ruolo";

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

export default function RuoloTributiDetailPage() {
  return (
    <Suspense fallback={<RuoloTributiDetailFallback />}>
      <RuoloTributiDetailContent />
    </Suspense>
  );
}

function RuoloTributiDetailContent() {
  const params = useParams<{ avvisoId: string }>();
  const avvisoId = params.avvisoId;

  const [token, setToken] = useState<string | null>(null);
  const [detail, setDetail] = useState<RuoloTributiAvvisoDetailResponse | null>(null);
  const [reminders, setReminders] = useState<RuoloTributiReminderResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    setError(null);
    Promise.all([getTributiAvviso(token, avvisoId), listTributiReminders(token, avvisoId)])
      .then(([nextDetail, nextReminders]) => {
        setDetail(nextDetail);
        setReminders(nextReminders);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Errore dettaglio tributi"))
      .finally(() => setLoading(false));
  }, [avvisoId, token]);

  async function refreshDetail() {
    /* c8 ignore next -- Refresh is only triggered after the token-backed detail has been loaded. */
    if (!token) return;
    const [nextDetail, nextReminders] = await Promise.all([
      getTributiAvviso(token, avvisoId),
      listTributiReminders(token, avvisoId),
    ]);
    setDetail(nextDetail);
    setReminders(nextReminders);
  }

  async function submitPayment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    /* c8 ignore next -- The form is rendered only when token and detail are available. */
    if (!token || !detail) return;
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const amount = Number(String(form.get("amount")).replace(",", "."));
    if (!Number.isFinite(amount) || amount <= 0) {
      setError("Inserisci un importo pagamento valido.");
      return;
    }
    setError(null);
    setMessage(null);
    await createTributiPayment(token, detail.id, {
      amount,
      paid_at: String(form.get("paid_at") || "") || null,
      payment_reference: String(form.get("payment_reference") || "") || null,
      payment_method: String(form.get("payment_method") || "") || null,
    });
    formElement.reset();
    await refreshDetail();
    setMessage("Pagamento registrato.");
  }

  async function submitStatus(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    /* c8 ignore next -- The form is rendered only when token and detail are available. */
    if (!token || !detail) return;
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    setError(null);
    setMessage(null);
    await updateTributiAvvisoStatus(token, detail.id, {
      workflow_status: (String(form.get("workflow_status") || "") || null) as RuoloTributiWorkflowStatus | null,
      capacitas_url: String(form.get("capacitas_url") || "") || null,
      capacitas_avviso_code: String(form.get("capacitas_avviso_code") || "") || null,
    });
    await refreshDetail();
    setMessage("Stato aggiornato.");
  }

  async function submitNote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    /* c8 ignore next -- The form is rendered only when token and detail are available. */
    if (!token || !detail) return;
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const body = String(form.get("body") || "").trim();
    if (!body) {
      setError("Scrivi una nota prima di salvarla.");
      return;
    }
    setError(null);
    setMessage(null);
    await addTributiNote(token, detail.id, { body, visibility: "internal" });
    formElement.reset();
    await refreshDetail();
    setMessage("Nota salvata.");
  }

  async function submitReminder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    /* c8 ignore next -- The form is rendered only when token and detail are available. */
    if (!token || !detail) return;
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    setError(null);
    setMessage(null);
    await createTributiReminder(token, detail.id, {
      notes: String(form.get("notes") || "") || null,
    });
    formElement.reset();
    await refreshDetail();
    setMessage("Sollecito generato.");
  }

  async function downloadReminder(reminder: RuoloTributiReminderResponse) {
    /* c8 ignore next -- The download button is rendered only when token and download URL are available. */
    if (!token || !reminder.download_url) return;
    const blob = await downloadTributiReminderDocument(token, reminder.download_url);
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `sollecito_${reminder.id}.docx`;
    anchor.click();
    window.URL.revokeObjectURL(url);
  }

  return (
    <RuoloModulePage
      title="Dettaglio Tributo"
      description="Gestione puntuale di pagamento, stato operativo, note e link CapaciTas."
      breadcrumb="Dettaglio tributo"
      requiredSection="ruolo.tributi.view"
      topbarActions={<Link className="btn-secondary" href="/ruolo/tributi">Torna ai tributi</Link>}
    >
      {loading ? (
        <section className="panel-card"><p className="text-sm text-gray-400">Caricamento dettaglio tributo...</p></section>
      ) : detail ? (
        <TributiDetailWorkspace
          detail={detail}
          error={error}
          message={message}
          onSubmitPayment={submitPayment}
          onSubmitStatus={submitStatus}
          onSubmitNote={submitNote}
          onSubmitReminder={submitReminder}
          onDownloadReminder={downloadReminder}
          reminders={reminders}
        />
      ) : (
        <section className="panel-card">
          <p className="section-title">Dettaglio non disponibile</p>
          <p className="section-copy">{error ?? "L'avviso richiesto non e stato trovato o non e accessibile."}</p>
        </section>
      )}
    </RuoloModulePage>
  );
}

function TributiDetailWorkspace({
  detail,
  error,
  message,
  onSubmitPayment,
  onSubmitStatus,
  onSubmitNote,
  onSubmitReminder,
  onDownloadReminder,
  reminders,
}: {
  detail: RuoloTributiAvvisoDetailResponse;
  reminders: RuoloTributiReminderResponse[];
  error: string | null;
  message: string | null;
  onSubmitPayment: (event: FormEvent<HTMLFormElement>) => void;
  onSubmitStatus: (event: FormEvent<HTMLFormElement>) => void;
  onSubmitNote: (event: FormEvent<HTMLFormElement>) => void;
  onSubmitReminder: (event: FormEvent<HTMLFormElement>) => void;
  onDownloadReminder: (reminder: RuoloTributiReminderResponse) => void;
}) {
  return (
    <div className="space-y-6">
      <ModuleWorkspaceHero
        badge={<><LockIcon className="h-3.5 w-3.5" /> Dettaglio tributo</>}
        title={detail.display_name ?? detail.nominativo_raw ?? "Avviso senza nominativo"}
        description={`Anno ${detail.anno_tributario} · CNC ${detail.codice_cnc} · Utenza ${detail.codice_utenza ?? "-"}`}
        actions={
          <>
            <ModuleWorkspaceNoticeCard
              title={PAYMENT_STATUS_LABELS[detail.payment_status]}
              description={`Saldo corrente ${formatEuro(detail.saldo_amount)} su dovuto ${formatEuro(detail.importo_totale_euro)}.`}
              tone={detail.payment_status === "paid" ? "success" : "warning"}
            />
            <ModuleWorkspaceNoticeCard
              title={detail.workflow_status ?? "Nessuno stato operativo"}
              description={detail.capacitas_url ? "Link CapaciTas disponibile." : "Link CapaciTas non ancora configurato."}
              tone={detail.workflow_status ? "info" : "neutral"}
            />
          </>
        }
      >
        <ModuleWorkspaceKpiRow>
          <ModuleWorkspaceKpiTile label="Dovuto" value={formatEuro(detail.importo_totale_euro)} hint="Totale avviso" />
          <ModuleWorkspaceKpiTile label="Pagato" value={formatEuro(detail.paid_amount)} hint="Pagamenti validi" variant="emerald" />
          <ModuleWorkspaceKpiTile label="Saldo" value={formatEuro(detail.saldo_amount)} hint="Residuo" variant={(detail.saldo_amount ?? 0) > 0 ? "amber" : "default"} />
          <ModuleWorkspaceKpiTile label="Solleciti" value={reminders.length} hint="Documenti predisposti" />
        </ModuleWorkspaceKpiRow>
      </ModuleWorkspaceHero>

      {error ? <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
      {message ? <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{message}</div> : null}

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr),380px]">
        <article className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
          <p className="inline-flex items-center gap-2 rounded-full bg-[#e8f2ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
            <DocumentIcon className="h-3.5 w-3.5" />
            Posizione
          </p>
          <dl className="mt-5 grid gap-3 text-sm md:grid-cols-2">
            <DetailItem label="CF/P.IVA" value={detail.codice_fiscale_raw} />
            <DetailItem label="Codice utenza" value={detail.codice_utenza} />
            <DetailItem label="Domicilio" value={detail.domicilio_raw} />
            <DetailItem label="Residenza" value={detail.residenza_raw} />
            <DetailItem label="0648" value={formatEuro(detail.importo_totale_0648)} />
            <DetailItem label="0985" value={formatEuro(detail.importo_totale_0985)} />
            <DetailItem label="0668" value={formatEuro(detail.importo_totale_0668)} />
            <DetailItem label="Ultimo pagamento" value={formatDate(detail.last_payment_at)} />
          </dl>
        </article>

        <article className="space-y-4 rounded-[28px] border border-[#d8dfd3] bg-white p-5 shadow-panel">
          <form className="space-y-3" onSubmit={onSubmitPayment}>
            <p className="text-sm font-semibold text-gray-900">Registra pagamento</p>
            <input name="amount" inputMode="decimal" placeholder="Importo" className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none" />
            <input name="paid_at" type="date" className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none" />
            <input name="payment_reference" placeholder="Riferimento pagamento" className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none" />
            <input name="payment_method" placeholder="Metodo" className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none" />
            <button type="submit" className="btn-secondary w-full">Salva pagamento</button>
          </form>

          <form className="space-y-3 border-t border-gray-100 pt-4" onSubmit={onSubmitStatus}>
            <p className="text-sm font-semibold text-gray-900">Stato e CapaciTas</p>
            <select name="workflow_status" defaultValue={detail.workflow_status ?? ""} className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none">
              <option value="">Nessuno stato operativo</option>
              {WORKFLOW_STATUS_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
            <input name="capacitas_url" defaultValue={detail.capacitas_url ?? ""} placeholder="Link CapaciTas" className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none" />
            <input name="capacitas_avviso_code" defaultValue={detail.capacitas_avviso_code ?? ""} placeholder="Codice avviso CapaciTas" className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none" />
            <button type="submit" className="btn-secondary w-full">Aggiorna stato</button>
            {detail.capacitas_url ? <Link className="btn-secondary block text-center" href={detail.capacitas_url} target="_blank" rel="noreferrer">Apri CapaciTas</Link> : null}
          </form>

          <form className="space-y-3 border-t border-gray-100 pt-4" onSubmit={onSubmitNote}>
            <p className="text-sm font-semibold text-gray-900">Nota interna</p>
            <textarea name="body" rows={3} placeholder="Nota operativa" className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none" />
            <button type="submit" className="btn-secondary w-full">Salva nota</button>
          </form>

          <form className="space-y-3 border-t border-gray-100 pt-4" onSubmit={onSubmitReminder}>
            <p className="text-sm font-semibold text-gray-900">Sollecito pagamento</p>
            <textarea name="notes" rows={3} placeholder="Note per sollecito" className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none" />
            <button type="submit" className="btn-secondary w-full">Genera sollecito .docx</button>
          </form>
        </article>
      </section>

      <section className="grid gap-6 xl:grid-cols-3">
        <HistoryPanel title="Pagamenti" empty="Nessun pagamento registrato.">
          {detail.payments.map((payment) => (
            <div key={payment.id} className="rounded-xl bg-gray-50 px-3 py-2 text-sm">
              <p className="font-medium text-gray-900">{formatEuro(payment.amount)} · {payment.status}</p>
              <p className="text-xs text-gray-500">{formatDate(payment.paid_at)} · {payment.payment_reference ?? payment.source}</p>
            </div>
          ))}
        </HistoryPanel>
        <HistoryPanel title="Note" empty="Nessuna nota registrata.">
          {detail.notes.map((note) => (
            <div key={note.id} className="rounded-xl bg-gray-50 px-3 py-2 text-sm">
              <p className="text-gray-800">{note.body}</p>
              <p className="mt-1 text-xs text-gray-500">{formatDate(note.created_at)}</p>
            </div>
          ))}
        </HistoryPanel>
        <HistoryPanel title="Solleciti" empty="Nessun sollecito generato.">
          {reminders.map((reminder) => (
            <div key={reminder.id} className="rounded-xl bg-gray-50 px-3 py-2 text-sm">
              <p className="font-medium text-gray-900">{reminder.status} · {formatDate(reminder.generated_at)}</p>
              <p className="text-xs text-gray-500">{reminder.notes ?? "Documento predisposto da GAIA"}</p>
              {reminder.download_url ? (
                <button type="button" className="mt-2 rounded-lg border border-[#d6e5db] bg-white px-3 py-1.5 text-xs font-medium text-[#1D4E35]" onClick={() => onDownloadReminder(reminder)}>
                  Scarica .docx
                </button>
              ) : null}
            </div>
          ))}
        </HistoryPanel>
      </section>
    </div>
  );
}

function DetailItem({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="rounded-2xl border border-gray-100 bg-[#fbfcfa] px-4 py-3">
      <dt className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">{label}</dt>
      <dd className="mt-1 font-medium text-gray-900">{value || "-"}</dd>
    </div>
  );
}

function HistoryPanel({ title, empty, children }: { title: string; empty: string; children: ReactNode[] }) {
  return (
    <article className="rounded-[28px] border border-[#d8dfd3] bg-white p-5 shadow-panel">
      <p className="text-sm font-semibold text-gray-900">{title}</p>
      <div className="mt-3 space-y-2">{children.length > 0 ? children : <p className="text-sm text-gray-500">{empty}</p>}</div>
    </article>
  );
}

export function RuoloTributiDetailFallback() {
  return (
    <RuoloModulePage
      title="Dettaglio Tributo"
      description="Gestione puntuale di pagamento, stato operativo, note e link CapaciTas."
      breadcrumb="Dettaglio tributo"
      requiredSection="ruolo.tributi.view"
    >
      <p className="text-sm text-gray-400">Caricamento dettaglio tributo...</p>
    </RuoloModulePage>
  );
}
