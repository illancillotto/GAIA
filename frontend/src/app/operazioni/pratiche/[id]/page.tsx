"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { ChevronRightIcon } from "@/components/ui/icons";

const statusLabels: Record<string, string> = {
  open: "Aperta",
  assigned: "Assegnata",
  acknowledged: "Presa in carico",
  in_progress: "In lavorazione",
  resolved: "Risolto",
  closed: "Chiusa",
  cancelled: "Annullata",
  reopened: "Riaperta",
};

const statusTone: Record<string, string> = {
  open: "bg-sky-50 text-sky-700",
  assigned: "bg-indigo-50 text-indigo-700",
  acknowledged: "bg-purple-50 text-purple-700",
  in_progress: "bg-amber-50 text-amber-700",
  resolved: "bg-emerald-50 text-emerald-700",
  closed: "bg-gray-100 text-gray-600",
  cancelled: "bg-rose-50 text-rose-700",
  reopened: "bg-orange-50 text-orange-700",
};

function PraticaDetailContent({ token, caseId }: { token: string; caseId: string }) {
  const [caseData, setCaseData] = useState<Record<string, unknown> | null>(null);
  const [events, setEvents] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadCase = useCallback(async () => {
    try {
      const [caseRes, eventsRes] = await Promise.all([
        fetch(`/api/operazioni/cases/${caseId}`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`/api/operazioni/cases/${caseId}/events`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);
      if (!caseRes.ok) throw new Error("Errore caricamento pratica");
      const data = await caseRes.json();
      setCaseData(data);
      if (eventsRes.ok) {
        const eventsData = await eventsRes.json();
        setEvents(Array.isArray(eventsData) ? eventsData : []);
      }
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore caricamento pratica");
    } finally {
      setLoading(false);
    }
  }, [token, caseId]);

  useEffect(() => {
    void loadCase();
  }, [loadCase]);

  if (loading) {
    return <p className="text-sm text-gray-500">Caricamento pratica in corso...</p>;
  }

  if (error || !caseData) {
    return (
      <article className="panel-card">
        <p className="text-sm font-medium text-red-700">{error || "Pratica non trovata"}</p>
      </article>
    );
  }

  return (
    <div className="page-stack">
      <nav className="flex items-center gap-1 text-sm text-gray-500">
        <Link href="/operazioni" className="hover:text-[#1D4E35]">Operazioni</Link>
        <ChevronRightIcon className="h-3 w-3" />
        <Link href="/operazioni/pratiche" className="hover:text-[#1D4E35]">Pratiche</Link>
        <ChevronRightIcon className="h-3 w-3" />
        <span className="text-gray-800">{String(caseData.case_number)}</span>
      </nav>

      <article className="panel-card">
        <div className="flex items-start justify-between">
          <div>
            <p className="section-title">{String(caseData.title)}</p>
            <p className="mt-1 text-sm text-gray-500">{String(caseData.case_number)}</p>
          </div>
          <span className={`rounded-full px-3 py-1 text-xs font-medium ${statusTone[String(caseData.status)] || "bg-gray-100 text-gray-600"}`}>
            {statusLabels[String(caseData.status)] || String(caseData.status)}
          </span>
        </div>

        {caseData.description != null && (
          <p className="mt-4 text-sm text-gray-700">{String(caseData.description)}</p>
        )}

        <div className="mt-6 grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
          <div>
            <p className="text-xs uppercase tracking-widest text-gray-400">Categoria</p>
            <p className="mt-1 font-medium text-gray-900">{String((caseData.category as Record<string, unknown>)?.name ?? "—")}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-widest text-gray-400">Gravità</p>
            <p className="mt-1 font-medium text-gray-900">{String((caseData.severity as Record<string, unknown>)?.name ?? "—")}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-widest text-gray-400">Segnalazione</p>
            <p className="mt-1 font-medium text-gray-900">{String((caseData.source_report as Record<string, unknown>)?.report_number ?? "—")}</p>
          </div>
        </div>
      </article>

      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Cronologia eventi</p>
          <p className="section-copy">Timeline completa degli eventi della pratica.</p>
        </div>

        {events.length === 0 ? (
          <p className="text-sm text-gray-500">Nessun evento registrato.</p>
        ) : (
          <div className="space-y-3">
            {events.map((event, idx) => (
              <div key={idx} className="flex gap-3 text-sm">
                <div className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-gray-400" />
                <div>
                  <p className="font-medium text-gray-700">{String(event.event_type)}</p>
                  <p className="text-xs text-gray-500">
                    {event.event_at ? new Date(event.event_at as string).toLocaleString("it-IT") : ""}
                    {event.note ? ` — ${String(event.note)}` : ""}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </article>

      <div className="flex flex-wrap gap-3">
        <button type="button" className="btn-secondary">Assegna</button>
        <button type="button" className="btn-secondary">Avvia lavorazione</button>
        <button type="button" className="btn-secondary">Risolvi</button>
        <button type="button" className="btn-primary">Chiudi pratica</button>
      </div>

      <Link href="/operazioni/pratiche" className="btn-secondary">
        Torna alla lista pratiche
      </Link>
    </div>
  );
}

export default function PraticaDetailPage() {
  const params = useParams<{ id: string }>();
  return (
    <OperazioniModulePage
      title="Dettaglio pratica"
      description="Stato, assegnazioni e timeline della pratica."
      breadcrumb={`ID ${params.id}`}
    >
      {({ token }) => <PraticaDetailContent token={token} caseId={params.id} />}
    </OperazioniModulePage>
  );
}
