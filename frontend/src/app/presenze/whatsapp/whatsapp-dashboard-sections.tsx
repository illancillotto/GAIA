import { MetricCard } from "@/components/ui/metric-card";
import type { PresenzeWhatsAppDashboardSummary, PresenzeWhatsAppMessage } from "@/types/api";

import { formatWhatsAppDateTime, WHATSAPP_STATUS_OPTIONS, whatsappSessionLabel, whatsappStatusLabel, whatsappStatusTone } from "./whatsapp-ui";

function channelMetrics(summary: PresenzeWhatsAppDashboardSummary | null) {
  if (!summary) {
    return { channel: "Stato non disponibile", detail: "Caricamento del canale", healthy: false, nextRun: "Non pianificata", cron: "Caricamento", delivered: 0, readAndSent: "0 letti · 0 inviati", attention: 0, attentionDetail: "0 incerti · 0 STOP" };
  }
  const healthy = summary.session_status === "working" || summary.session_status === "dry_run";
  const providerDetail = summary.session_detail ? ` · ${summary.session_detail}` : "";
  return {
    channel: whatsappSessionLabel(summary.session_status),
    detail: summary.provider_enabled ? `${summary.provider} · ${summary.send_window}${providerDetail}` : "Canale non attivo",
    healthy,
    nextRun: summary.next_run_at ? formatWhatsAppDateTime(summary.next_run_at) : "Non pianificata",
    cron: `Cron ${summary.cron}`,
    delivered: summary.delivered_total,
    readAndSent: `${summary.read_total} letti · ${summary.sent_total} inviati`,
    attention: summary.failed_total + summary.uncertain_total + summary.opted_out_total,
    attentionDetail: `${summary.uncertain_total} incerti · ${summary.opted_out_total} STOP`,
  };
}

export function WhatsAppChannelOverview({ summary, busy, onOpenPreview }: { summary: PresenzeWhatsAppDashboardSummary | null; busy: boolean; onOpenPreview: () => void }) {
  const metrics = channelMetrics(summary);
  return (
    <section className="overflow-hidden rounded-[30px] border border-emerald-950/10 bg-[radial-gradient(circle_at_top_right,_#dff4df,_transparent_42%),linear-gradient(135deg,_#f8fbf4,_#eef5ed)] p-5 shadow-sm sm:p-8">
      <div className="flex flex-wrap items-start justify-between gap-5"><div className="max-w-3xl"><p className="text-xs font-bold uppercase tracking-[0.24em] text-emerald-700">GAIA · canale persone</p><h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">Ogni messaggio, fino alla lettura.</h2><p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">Anteprima i destinatari senza inviare, individua telefoni mancanti e ricostruisci per ogni utente cosa è successo.</p></div><button className="btn-primary" disabled={busy} type="button" onClick={onOpenPreview}>{busy ? "Calcolo..." : "Apri anteprima"}</button></div>
      <div className="mt-7 grid auto-rows-fr gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Canale" value={metrics.channel} sub={metrics.detail} variant={metrics.healthy ? "success" : "warning"} />
        <MetricCard label="Prossima esecuzione" value={metrics.nextRun} sub={metrics.cron} />
        <MetricCard label="Consegnati" value={metrics.delivered} sub={metrics.readAndSent} variant="success" />
        <MetricCard label="Richiedono attenzione" value={metrics.attention} sub={metrics.attentionDetail} variant="warning" />
      </div>
    </section>
  );
}

type HistoryProps = { messages: PresenzeWhatsAppMessage[]; total: number; query: string; status: string; page: number; loading: boolean; onQuery: (value: string) => void; onStatus: (value: string) => void; onPage: (value: number) => void; onOpen: (message: PresenzeWhatsAppMessage) => void };

export function WhatsAppMessageHistory({ messages, total, query, status, page, loading, onQuery, onStatus, onPage, onOpen }: HistoryProps) {
  const lastPage = Math.max(1, Math.ceil(total / 25));
  return (
    <section className="rounded-[28px] border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
      <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">Registro utenti</p><h2 className="mt-1 text-2xl font-semibold">Messaggi inviati</h2></div><div className="flex w-full flex-wrap gap-3 sm:w-auto"><label className="min-w-[220px] flex-1 text-xs font-semibold text-slate-500">Cerca utente o numero<input className="field mt-1 w-full" value={query} onChange={(event) => onQuery(event.target.value)} placeholder="Nome, username, telefono" /></label><label className="min-w-[180px] text-xs font-semibold text-slate-500">Stato<select className="field mt-1 w-full" value={status} onChange={(event) => onStatus(event.target.value)}>{WHATSAPP_STATUS_OPTIONS.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label></div></div>
      <div className="mt-5 overflow-x-auto"><table className="min-w-full text-left text-sm"><thead><tr className="border-b border-slate-200 text-xs uppercase tracking-[0.14em] text-slate-400"><th className="px-3 py-3">Utente</th><th className="px-3 py-3">Giornate</th><th className="px-3 py-3">Stato</th><th className="px-3 py-3">Invio</th><th className="px-3 py-3 text-right">Dettagli</th></tr></thead><tbody className="divide-y divide-slate-100">{messages.map((message) => <tr key={message.id} className="hover:bg-slate-50"><td className="px-3 py-4"><p className="font-semibold text-slate-900">{message.user_label}</p><p className="mt-0.5 text-xs text-slate-500">{message.phone_e164}{message.username ? ` · @${message.username}` : ""}</p></td><td className="px-3 py-4"><strong>{message.days.length}</strong><span className="ml-1 text-slate-500">{message.days.length === 1 ? "giornata" : "giornate"}</span></td><td className="px-3 py-4"><span className={`rounded-full px-2.5 py-1 text-xs font-bold ring-1 ${whatsappStatusTone(message.status)}`}>{whatsappStatusLabel(message.status)}</span></td><td className="px-3 py-4 text-slate-500">{formatWhatsAppDateTime(message.created_at)}</td><td className="px-3 py-4 text-right"><button className="btn-secondary" type="button" onClick={() => onOpen(message)}>Apri</button></td></tr>)}</tbody></table>{!loading && messages.length === 0 ? <p className="py-12 text-center text-sm text-slate-500">Nessun messaggio corrisponde ai filtri.</p> : null}{loading ? <p className="py-12 text-center text-sm text-slate-500">Caricamento storico...</p> : null}</div>
      <footer className="mt-4 flex items-center justify-between border-t border-slate-100 pt-4 text-sm text-slate-500"><span>{total} messaggi tracciati</span><div className="flex items-center gap-2"><button className="btn-secondary" disabled={page === 1} type="button" onClick={() => onPage(page - 1)}>Indietro</button><span>{page} / {lastPage}</span><button className="btn-secondary" disabled={page === lastPage} type="button" onClick={() => onPage(page + 1)}>Avanti</button></div></footer>
    </section>
  );
}
