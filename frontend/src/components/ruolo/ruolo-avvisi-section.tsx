"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { getAvvisiBySubject } from "@/lib/ruolo-api";
import type { RuoloAvvisoDetailResponse } from "@/types/ruolo";

type Props = {
  subjectId: string;
  token: string;
};

function formatEuro(value: number | null | undefined): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(value);
}

export function RuoloAvvisiSection({ subjectId, token }: Props) {
  const [avvisi, setAvvisi] = useState<RuoloAvvisoDetailResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAvvisiBySubject(token, subjectId)
      .then(setAvvisi)
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : String(err);
        if (!msg.includes("403") && !msg.includes("Module access")) {
          setError(msg);
        }
      })
      .finally(() => setLoading(false));
  }, [subjectId, token]);

  if (loading) return null;
  if (error) return null;
  if (avvisi.length === 0) return null;

  return (
    <section className="rounded-2xl border border-[#D9E8DF] bg-white p-4">
      <div className="mb-3">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">
          Avvisi Ruolo consortile
        </p>
        <p className="mt-1 text-sm text-gray-600">
          {avvisi.length} avviso{avvisi.length !== 1 ? "i" : ""} trovato{avvisi.length !== 1 ? "i" : ""}.
        </p>
      </div>
      <div className="space-y-2">
        {avvisi.map((a) => (
          <div key={a.id} className="flex items-center justify-between rounded-xl border border-gray-100 px-3 py-2.5">
            <div>
              <span className="text-sm font-medium text-gray-800">Anno {a.anno_tributario}</span>
              {a.codice_utenza && (
                <span className="ml-2 text-xs text-gray-400">Utenza: {a.codice_utenza}</span>
              )}
              <p className="text-xs text-gray-500">CNC: {a.codice_cnc}</p>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm font-semibold text-gray-800">{formatEuro(a.importo_totale_euro)}</span>
              <Link
                href={`/ruolo/avvisi/${a.id}`}
                className="text-xs font-medium text-[#1D4E35] hover:underline"
              >
                Dettaglio →
              </Link>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
