"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

import { ProtectedPage } from "@/components/app/protected-page";
import { DocumentIcon, ChevronRightIcon } from "@/components/ui/icons";
import { getStoredAccessToken } from "@/lib/auth";

const OPERAZIONI_API = process.env.NEXT_PUBLIC_API_BASE_URL || "";

export default function PraticaDetailPage() {
  const params = useParams<{ id: string }>();
  const [caseData, setCaseData] = useState<Record<string, unknown> | null>(null);
  const [events, setEvents] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadCase = useCallback(async () => {
    const token = getStoredAccessToken();
    if (!token || !params.id) return;
    try {
      const [caseRes, eventsRes] = await Promise.all([
        fetch(`${OPERAZIONI_API}/api/operazioni/cases/${params.id}`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${OPERAZIONI_API}/api/operazioni/cases/${params.id}/events`, {
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
  }, [params.id]);

  useEffect(() => {
    void loadCase();
  }, [loadCase]);

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

  const statusColors: Record<string, string> = {
    open: "bg-blue-100 text-blue-800",
    assigned: "bg-indigo-100 text-indigo-800",
    acknowledged: "bg-purple-100 text-purple-800",
    in_progress: "bg-amber-100 text-amber-800",
    resolved: "bg-green-100 text-green-800",
    closed: "bg-gray-100 text-gray-800",
    cancelled: "bg-red-100 text-red-800",
    reopened: "bg-orange-100 text-orange-800",
  };

  if (loading) {
    return (
      <ProtectedPage title="Dettaglio Pratica" description="Caricamento..." breadcrumb="Pratiche" requiredModule="operazioni">
        <div className="py-8 text-center text-sm text-gray-500">Caricamento...</div>
      </ProtectedPage>
    );
  }

  if (error || !caseData) {
    return (
      <ProtectedPage title="Dettaglio Pratica" description="Errore" breadcrumb="Pratiche" requiredModule="operazioni">
        <div className="py-8 text-center text-sm text-red-600">{error || "Pratica non trovata"}</div>
      </ProtectedPage>
    );
  }

  return (
    <ProtectedPage title={`Pratica: ${caseData.case_number as string}`} description="Dettaglio pratica" breadcrumb="Pratiche" requiredModule="operazioni">
      <nav className="mb-4 flex items-center gap-1 text-sm text-gray-500">
        <Link href="/operazioni" className="hover:text-gray-700">Operazioni</Link>
        <ChevronRightIcon className="h-3 w-3" />
        <Link href="/operazioni/pratiche" className="hover:text-gray-700">Pratiche</Link>
        <ChevronRightIcon className="h-3 w-3" />
        <span className="text-gray-800">{caseData.case_number as string}</span>
      </nav>

      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">{caseData.title as string}</h2>
            <p className="mt-1 text-sm text-gray-500">{caseData.case_number as string}</p>
          </div>
          <span className={`rounded-full px-3 py-1 text-xs font-medium ${statusColors[caseData.status as string] || "bg-gray-100 text-gray-800"}`}>
            {statusLabels[caseData.status as string] || caseData.status}
          </span>
        </div>

        {caseData.description && (
          <p className="mt-4 text-sm text-gray-700">{caseData.description as string}</p>
        )}

        <div className="mt-6 grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
          <div>
            <p className="text-gray-500">Categoria</p>
            <p className="font-medium text-gray-900">{(caseData.category as Record<string, unknown>)?.name || "—"}</p>
          </div>
          <div>
            <p className="text-gray-500">Gravità</p>
            <p className="font-medium text-gray-900">{(caseData.severity as Record<string, unknown>)?.name || "—"}</p>
          </div>
          <div>
            <p className="text-gray-500">Segnalazione</p>
            <p className="font-medium text-gray-900">{(caseData.source_report as Record<string, unknown>)?.report_number || "—"}</p>
          </div>
        </div>
      </div>

      {/* Timeline eventi */}
      <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6">
        <h3 className="text-sm font-semibold text-gray-700">Cronologia eventi</h3>
        {events.length === 0 ? (
          <p className="mt-3 text-sm text-gray-500">Nessun evento registrato.</p>
        ) : (
          <div className="mt-4 space-y-3">
            {events.map((event, idx) => (
              <div key={idx} className="flex gap-3 text-sm">
                <div className="mt-1 h-2 w-2 shrink-0 rounded-full bg-gray-400" />
                <div>
                  <p className="font-medium text-gray-700">{event.event_type as string}</p>
                  <p className="text-xs text-gray-500">
                    {event.event_at ? new Date(event.event_at as string).toLocaleString("it-IT") : ""}
                    {event.note ? ` — ${event.note as string}` : ""}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Azioni */}
      <div className="mt-6 flex flex-wrap gap-3">
        <button
          type="button"
          className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Assegna
        </button>
        <button
          type="button"
          className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Avvia lavorazione
        </button>
        <button
          type="button"
          className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Risolvi
        </button>
        <button
          type="button"
          className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
        >
          Chiudi pratica
        </button>
      </div>
    </ProtectedPage>
  );
}
