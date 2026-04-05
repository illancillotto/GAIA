"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

import { ProtectedPage } from "@/components/app/protected-page";
import { AlertTriangleIcon, ChevronRightIcon } from "@/components/ui/icons";
import { getStoredAccessToken } from "@/lib/auth";

const OPERAZIONI_API = process.env.NEXT_PUBLIC_API_BASE_URL || "";

export default function SegnalazioneDetailPage() {
  const params = useParams<{ id: string }>();
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadReport = useCallback(async () => {
    const token = getStoredAccessToken();
    if (!token || !params.id) return;
    try {
      const res = await fetch(`${OPERAZIONI_API}/api/operazioni/reports/${params.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Errore caricamento segnalazione");
      const data = await res.json();
      setReport(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore caricamento segnalazione");
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  useEffect(() => {
    void loadReport();
  }, [loadReport]);

  if (loading) {
    return (
      <ProtectedPage title="Dettaglio Segnalazione" description="Caricamento..." breadcrumb="Segnalazioni" requiredModule="operazioni">
        <div className="py-8 text-center text-sm text-gray-500">Caricamento...</div>
      </ProtectedPage>
    );
  }

  if (error || !report) {
    return (
      <ProtectedPage title="Dettaglio Segnalazione" description="Errore" breadcrumb="Segnalazioni" requiredModule="operazioni">
        <div className="py-8 text-center text-sm text-red-600">{error || "Segnalazione non trovata"}</div>
      </ProtectedPage>
    );
  }

  return (
    <ProtectedPage title={`Segnalazione: ${report.report_number as string}`} description="Dettaglio segnalazione" breadcrumb="Segnalazioni" requiredModule="operazioni">
      <nav className="mb-4 flex items-center gap-1 text-sm text-gray-500">
        <Link href="/operazioni" className="hover:text-gray-700">Operazioni</Link>
        <ChevronRightIcon className="h-3 w-3" />
        <Link href="/operazioni/segnalazioni" className="hover:text-gray-700">Segnalazioni</Link>
        <ChevronRightIcon className="h-3 w-3" />
        <span className="text-gray-800">{report.report_number as string}</span>
      </nav>

      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">{report.title as string}</h2>
            <p className="mt-1 text-sm text-gray-500">{report.report_number as string}</p>
          </div>
          <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800">
            {report.status as string}
          </span>
        </div>

        {report.internal_case_id && (
          <div className="mt-4 rounded-lg bg-blue-50 p-3 text-sm">
            <p className="font-medium text-blue-700">Pratica collegata</p>
            <Link href={`/operazioni/pratiche/${report.internal_case_id as string}`} className="mt-1 text-blue-600 hover:underline">
              Vai alla pratica →
            </Link>
          </div>
        )}
      </div>
    </ProtectedPage>
  );
}
