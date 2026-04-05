"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { ChevronRightIcon } from "@/components/ui/icons";

function SegnalazioneDetailContent({ token, reportId }: { token: string; reportId: string }) {
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadReport = useCallback(async () => {
    try {
      const res = await fetch(`/api/operazioni/reports/${reportId}`, {
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
  }, [token, reportId]);

  useEffect(() => {
    void loadReport();
  }, [loadReport]);

  if (loading) {
    return <p className="text-sm text-gray-500">Caricamento segnalazione in corso...</p>;
  }

  if (error || !report) {
    return (
      <article className="panel-card">
        <p className="text-sm font-medium text-red-700">{error || "Segnalazione non trovata"}</p>
      </article>
    );
  }

  return (
    <div className="page-stack">
      <nav className="flex items-center gap-1 text-sm text-gray-500">
        <Link href="/operazioni" className="hover:text-[#1D4E35]">Operazioni</Link>
        <ChevronRightIcon className="h-3 w-3" />
        <Link href="/operazioni/segnalazioni" className="hover:text-[#1D4E35]">Segnalazioni</Link>
        <ChevronRightIcon className="h-3 w-3" />
        <span className="text-gray-800">{String(report.report_number)}</span>
      </nav>

      <article className="panel-card">
        <div className="flex items-start justify-between">
          <div>
            <p className="section-title">{String(report.title)}</p>
            <p className="mt-1 text-sm text-gray-500">{String(report.report_number)}</p>
          </div>
          <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700">
            {String(report.status)}
          </span>
        </div>

        {report.internal_case_id != null && (
          <div className="mt-4 rounded-lg bg-sky-50 p-3 text-sm">
            <p className="font-medium text-sky-700">Pratica collegata</p>
            <Link href={`/operazioni/pratiche/${report.internal_case_id as string}`} className="mt-1 inline-block text-sm font-medium text-[#1D4E35] hover:underline">
              Vai alla pratica →
            </Link>
          </div>
        )}
      </article>

      <Link href="/operazioni/segnalazioni" className="btn-secondary">
        Torna alla lista segnalazioni
      </Link>
    </div>
  );
}

export default function SegnalazioneDetailPage() {
  const params = useParams<{ id: string }>();
  return (
    <OperazioniModulePage
      title="Dettaglio segnalazione"
      description="Contenuto, allegati e collegamento alla pratica."
      breadcrumb={`ID ${params.id}`}
    >
      {({ token }) => <SegnalazioneDetailContent token={token} reportId={params.id} />}
    </OperazioniModulePage>
  );
}
