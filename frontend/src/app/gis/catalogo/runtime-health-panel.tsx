"use client";

import { useEffect, useState } from "react";

import { getGisRuntimeHealth } from "@/lib/api/gis";
import type {
  GisRuntimeHealthResponse,
  GisRuntimeHealthStatus,
} from "@/types/gis";

const statusLabels: Record<GisRuntimeHealthStatus, string> = {
  ok: "Disponibile",
  warning: "Da verificare",
  critical: "Non disponibile",
  not_configured: "Non configurato",
  disabled: "Disabilitato",
  unreachable: "Non raggiungibile",
};

const statusClasses: Record<GisRuntimeHealthStatus, string> = {
  ok: "bg-[#EAF3E8] text-[#1D4E35]",
  warning: "bg-[#FFF6D8] text-[#76560C]",
  critical: "bg-[#FFE5E1] text-[#9A2B1F]",
  not_configured: "bg-gray-100 text-gray-700",
  disabled: "bg-stone-100 text-stone-700",
  unreachable: "bg-amber-100 text-amber-900",
};

export function GisRuntimeHealthPanel({ token }: { token: string }) {
  const [health, setHealth] = useState<GisRuntimeHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    void getGisRuntimeHealth(token)
      .then((response) => {
        if (!cancelled) setHealth(response);
      })
      .catch((loadError: unknown) => {
        if (!cancelled) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Controllo servizi GIS non disponibile",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [reloadKey, token]);

  return (
    <section className="rounded-[28px] border border-[#d9dfd6] bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#526a59]">Disponibilità reale</p>
          <h3 className="mt-2 text-xl font-semibold text-gray-950">Stato dei servizi GIS</h3>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-600">Questa verifica contatta i servizi e controlla il percorso NAS. Un componente non configurato non viene mostrato come disponibile.</p>
        </div>
        <button className="btn-secondary" type="button" disabled={loading} onClick={() => setReloadKey((value) => value + 1)}>{loading ? "Verifica..." : "Verifica di nuovo"}</button>
      </div>

      {loading ? <p className="mt-4 text-sm font-semibold text-[#1D4E35]" role="status">Controllo servizi in corso...</p> : null}
      {error ? <p className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700" role="alert">{error}</p> : null}
      {health ? (
        <>
          <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {health.components.map((component) => (
              <article key={component.key} className="rounded-2xl border border-[#e2e9e3] bg-[#f8faf8] p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h4 className="font-semibold text-gray-950">{component.label}</h4>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${statusClasses[component.status]}`}>{statusLabels[component.status]}</span>
                </div>
                <p className="mt-3 text-sm leading-6 text-gray-600">{component.message}</p>
                {component.latency_ms != null ? <p className="mt-2 text-xs text-gray-500">Risposta in {component.latency_ms} ms</p> : null}
              </article>
            ))}
          </div>
          <p className={`mt-4 rounded-2xl px-4 py-3 text-sm font-semibold ${health.export_scheduler_enabled ? statusClasses.ok : statusClasses.warning}`} role="status">
            Scheduler export: {health.export_scheduler_enabled ? "attivo" : "disabilitato"}.
          </p>
        </>
      ) : null}
    </section>
  );
}
