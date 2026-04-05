"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { ChevronRightIcon } from "@/components/ui/icons";

const statusLabels: Record<string, string> = {
  draft: "Bozza",
  in_progress: "In corso",
  submitted: "Inviata",
  under_review: "In revisione",
  approved: "Approvata",
  rejected: "Respinta",
};

const statusTone: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600",
  in_progress: "bg-sky-50 text-sky-700",
  submitted: "bg-amber-50 text-amber-700",
  under_review: "bg-purple-50 text-purple-700",
  approved: "bg-emerald-50 text-emerald-700",
  rejected: "bg-rose-50 text-rose-700",
};

function AttivitaDetailContent({ token, activityId }: { token: string; activityId: string }) {
  const [activity, setActivity] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadActivity = useCallback(async () => {
    try {
      const res = await fetch(`/api/operazioni/activities/${activityId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Errore caricamento attività");
      const data = await res.json();
      setActivity(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore caricamento attività");
    } finally {
      setLoading(false);
    }
  }, [token, activityId]);

  useEffect(() => {
    void loadActivity();
  }, [loadActivity]);

  if (loading) {
    return <p className="text-sm text-gray-500">Caricamento attività in corso...</p>;
  }

  if (error || !activity) {
    return (
      <article className="panel-card">
        <p className="text-sm font-medium text-red-700">{error || "Attività non trovata"}</p>
      </article>
    );
  }

  return (
    <div className="page-stack">
      <nav className="flex items-center gap-1 text-sm text-gray-500">
        <Link href="/operazioni" className="hover:text-[#1D4E35]">Operazioni</Link>
        <ChevronRightIcon className="h-3 w-3" />
        <Link href="/operazioni/attivita" className="hover:text-[#1D4E35]">Attività</Link>
        <ChevronRightIcon className="h-3 w-3" />
        <span className="text-gray-800">Dettaglio</span>
      </nav>

      <article className="panel-card">
        <div className="flex items-start justify-between">
          <div>
            <p className="section-title">Attività</p>
            <p className="mt-1 text-sm text-gray-500">ID: {String(activity.id)}</p>
          </div>
          <span className={`rounded-full px-3 py-1 text-xs font-medium ${statusTone[String(activity.status)] || "bg-gray-100 text-gray-600"}`}>
            {statusLabels[String(activity.status)] || String(activity.status)}
          </span>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
          <div>
            <p className="text-xs uppercase tracking-widest text-gray-400">Inizio</p>
            <p className="mt-1 font-medium text-gray-900">{activity.started_at ? new Date(activity.started_at as string).toLocaleString("it-IT") : "—"}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-widest text-gray-400">Fine</p>
            <p className="mt-1 font-medium text-gray-900">{activity.ended_at ? new Date(activity.ended_at as string).toLocaleString("it-IT") : "—"}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-widest text-gray-400">Operatore</p>
            <p className="mt-1 font-medium text-gray-900">{activity.operator_user_id ? `ID: ${activity.operator_user_id}` : "—"}</p>
          </div>
        </div>

        {activity.text_note != null && (
          <div className="mt-4 rounded-lg bg-gray-50 p-3 text-sm text-gray-700">
            <p className="font-medium text-gray-600">Note</p>
            <p className="mt-1">{String(activity.text_note)}</p>
          </div>
        )}
      </article>

      <div className="grid gap-6 sm:grid-cols-2">
        <article className="panel-card">
          <p className="section-title">Dati GPS</p>
          <p className="mt-2 text-sm text-gray-500">Riepilogo GPS in implementazione.</p>
        </article>
        <article className="panel-card">
          <p className="section-title">Allegati</p>
          <p className="mt-2 text-sm text-gray-500">Lista allegati in implementazione.</p>
        </article>
      </div>

      <Link href="/operazioni/attivita" className="btn-secondary">
        Torna alla lista attività
      </Link>
    </div>
  );
}

export default function AttivitaDetailPage() {
  const params = useParams<{ id: string }>();
  return (
    <OperazioniModulePage
      title="Dettaglio attività"
      description="Stato, tempi e metadati dell’attività operatore."
      breadcrumb={`ID ${params.id}`}
    >
      {({ token }) => <AttivitaDetailContent token={token} activityId={params.id} />}
    </OperazioniModulePage>
  );
}
