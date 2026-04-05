"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

import { ProtectedPage } from "@/components/app/protected-page";
import { RefreshIcon, ChevronRightIcon } from "@/components/ui/icons";
import { getStoredAccessToken } from "@/lib/auth";

const OPERAZIONI_API = process.env.NEXT_PUBLIC_API_BASE_URL || "";

export default function AttivitaDetailPage() {
  const params = useParams<{ id: string }>();
  const [activity, setActivity] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadActivity = useCallback(async () => {
    const token = getStoredAccessToken();
    if (!token || !params.id) return;
    try {
      const res = await fetch(`${OPERAZIONI_API}/api/operazioni/activities/${params.id}`, {
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
  }, [params.id]);

  useEffect(() => {
    void loadActivity();
  }, [loadActivity]);

  const statusLabels: Record<string, string> = {
    draft: "Bozza",
    in_progress: "In corso",
    submitted: "Inviata",
    under_review: "In revisione",
    approved: "Approvata",
    rejected: "Respinta",
    rectified: "Rettificata",
  };

  const statusColors: Record<string, string> = {
    draft: "bg-gray-100 text-gray-700",
    in_progress: "bg-blue-100 text-blue-800",
    submitted: "bg-amber-100 text-amber-800",
    under_review: "bg-purple-100 text-purple-800",
    approved: "bg-green-100 text-green-800",
    rejected: "bg-red-100 text-red-800",
    rectified: "bg-orange-100 text-orange-800",
  };

  if (loading) {
    return (
      <ProtectedPage title="Dettaglio Attività" description="Caricamento..." breadcrumb="Attività" requiredModule="operazioni">
        <div className="py-8 text-center text-sm text-gray-500">Caricamento...</div>
      </ProtectedPage>
    );
  }

  if (error || !activity) {
    return (
      <ProtectedPage title="Dettaglio Attività" description="Errore" breadcrumb="Attività" requiredModule="operazioni">
        <div className="py-8 text-center text-sm text-red-600">{error || "Attività non trovata"}</div>
      </ProtectedPage>
    );
  }

  return (
    <ProtectedPage title={`Attività ${activity.id as string}`} description="Dettaglio attività" breadcrumb="Attività" requiredModule="operazioni">
      <nav className="mb-4 flex items-center gap-1 text-sm text-gray-500">
        <Link href="/operazioni" className="hover:text-gray-700">Operazioni</Link>
        <ChevronRightIcon className="h-3 w-3" />
        <Link href="/operazioni/attivita" className="hover:text-gray-700">Attività</Link>
        <ChevronRightIcon className="h-3 w-3" />
        <span className="text-gray-800">Dettaglio</span>
      </nav>

      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Attività</h2>
            <p className="mt-1 text-sm text-gray-500">ID: {activity.id as string}</p>
          </div>
          <span className={`rounded-full px-3 py-1 text-xs font-medium ${statusColors[activity.status as string] || "bg-gray-100 text-gray-800"}`}>
            {statusLabels[activity.status as string] || activity.status}
          </span>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
          <div>
            <p className="text-gray-500">Inizio</p>
            <p className="font-medium text-gray-900">{activity.started_at ? new Date(activity.started_at as string).toLocaleString("it-IT") : "—"}</p>
          </div>
          <div>
            <p className="text-gray-500">Fine</p>
            <p className="font-medium text-gray-900">{activity.ended_at ? new Date(activity.ended_at as string).toLocaleString("it-IT") : "—"}</p>
          </div>
          <div>
            <p className="text-gray-500">Operatore</p>
            <p className="font-medium text-gray-900">{activity.operator_user_id ? `ID: ${activity.operator_user_id}` : "—"}</p>
          </div>
        </div>

        {activity.text_note && (
          <div className="mt-4 rounded-lg bg-gray-50 p-3 text-sm text-gray-700">
            <p className="font-medium text-gray-600">Note</p>
            <p className="mt-1">{activity.text_note as string}</p>
          </div>
        )}
      </div>

      <div className="mt-6 grid gap-6 sm:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h3 className="text-sm font-semibold text-gray-700">Dati GPS</h3>
          <p className="mt-2 text-sm text-gray-500">Riepilogo GPS in implementazione.</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h3 className="text-sm font-semibold text-gray-700">Allegati</h3>
          <p className="mt-2 text-sm text-gray-500">Lista allegati in implementazione.</p>
        </div>
      </div>
    </ProtectedPage>
  );
}
