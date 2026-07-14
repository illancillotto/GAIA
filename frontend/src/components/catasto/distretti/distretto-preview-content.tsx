"use client";

import { useEffect, useState } from "react";

import { DistrettoGisPreview } from "@/components/catasto/distretti/distretto-gis-preview";
import { catastoGetDistretto, catastoGetDistrettoKpi } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatDistretto, CatDistrettoKpi } from "@/types/catasto";

type CatastoDistrettoPreviewContentProps = {
  open: boolean;
  distrettoId: string;
  numDistretto: string | null;
  anno?: number | null;
};

function buildFallbackDistrettoMessage(numDistretto: string | null): string {
  if (numDistretto) {
    return `Impossibile caricare il dettaglio del distretto ${numDistretto}.`;
  }
  return "Impossibile caricare il dettaglio del distretto.";
}

export function CatastoDistrettoPreviewContent({
  open,
  distrettoId,
  numDistretto,
  anno,
}: CatastoDistrettoPreviewContentProps) {
  const [distretto, setDistretto] = useState<CatDistretto | null>(null);
  const [kpi, setKpi] = useState<CatDistrettoKpi | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }

    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile. Riapri la pagina e riprova.");
      setLoading(false);
      return;
    }

    let cancelled = false;
    setError(null);
    setLoading(true);

    void Promise.allSettled([
      catastoGetDistretto(token, distrettoId),
      catastoGetDistrettoKpi(token, distrettoId, anno ?? undefined),
    ]).then(([distrettoResult, kpiResult]) => {
      if (cancelled) {
        return;
      }

      if (distrettoResult.status === "fulfilled") {
        setDistretto(distrettoResult.value);
      } else {
        setError(
          distrettoResult.reason instanceof Error
            ? distrettoResult.reason.message
            : buildFallbackDistrettoMessage(numDistretto),
        );
      }

      if (kpiResult.status === "fulfilled") {
        setKpi(kpiResult.value);
      } else {
        setKpi(null);
      }

      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [anno, distrettoId, numDistretto, open]);

  if (distretto) {
    return <DistrettoGisPreview distretto={distretto} kpi={kpi} />;
  }

  if (loading) {
    return (
      <section className="overflow-hidden rounded-[1.75rem] border border-[#cfe8d8] bg-white shadow-[0_16px_45px_rgba(15,23,42,0.12)]">
        <div className="px-5 py-4">
          <p className="text-[0.68rem] font-semibold uppercase tracking-[0.2em] text-[#2d6b47]">Vista GIS read-only</p>
          <h3 className="mt-1 text-lg font-semibold text-slate-950">Caricamento distretto</h3>
          <p className="mt-1 text-sm text-slate-500">Recupero perimetro, particelle e indicatori del distretto selezionato.</p>
        </div>
        <div className="h-[430px] animate-pulse bg-slate-100" />
      </section>
    );
  }

  return (
    <section className="rounded-[1.75rem] border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-800 shadow-[0_16px_45px_rgba(15,23,42,0.12)]">
      {error ?? buildFallbackDistrettoMessage(numDistretto)}
    </section>
  );
}
