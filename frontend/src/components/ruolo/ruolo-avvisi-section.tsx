"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import {
  ModuleWorkspaceHero,
  ModuleWorkspaceMiniStat,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { DocumentIcon, FolderIcon, SearchIcon } from "@/components/ui/icons";
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

  const linkedCount = avvisi.filter((avviso) => Boolean(avviso.subject_id)).length;
  const totaleEuro = avvisi.reduce((sum, avviso) => sum + (avviso.importo_totale_euro ?? 0), 0);
  const latestYear = avvisi.reduce<number | null>(
    (maxYear, avviso) => (maxYear == null || avviso.anno_tributario > maxYear ? avviso.anno_tributario : maxYear),
    null,
  );

  return (
    <section className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
      <div className="border-b border-[#edf1eb] p-5">
        <ModuleWorkspaceHero
          compact
          badge={
            <>
              <FolderIcon className="h-3.5 w-3.5" />
              Ruolo consortile
            </>
          }
          title="Avvisi collegati al soggetto selezionato."
          description="Consulta rapidamente annualita, importi e stato di collegamento senza uscire dalla scheda anagrafica."
          actions={
            <>
              <ModuleWorkspaceNoticeCard
                compact
                title={latestYear ? `Ultimo anno disponibile: ${latestYear}` : "Storico disponibile"}
                description={`${avvisi.length} avviso${avvisi.length !== 1 ? "i" : ""} associato${avvisi.length !== 1 ? "i" : ""} al soggetto corrente.`}
                tone="info"
              />
              <ModuleWorkspaceNoticeCard
                compact
                title="Totale storico"
                description={formatEuro(totaleEuro)}
                tone="success"
              />
            </>
          }
        />
      </div>
      <div className="space-y-4 p-5">
        <div className="grid gap-3 md:grid-cols-3">
          <ModuleWorkspaceMiniStat
            eyebrow="Avvisi"
            value={avvisi.length}
            description={`${avvisi.length} avviso${avvisi.length !== 1 ? "i" : ""} trovato${avvisi.length !== 1 ? "i" : ""} sul soggetto.`}
            compact
          />
          <ModuleWorkspaceMiniStat
            eyebrow="Collegati"
            value={linkedCount}
            description="Rientrano nel perimetro GAIA del soggetto corrente."
            tone="success"
            compact
          />
          <ModuleWorkspaceMiniStat
            eyebrow="Totale €"
            value={formatEuro(totaleEuro)}
            description="Somma degli importi totali degli avvisi mostrati."
            compact
          />
        </div>
        <div className="space-y-3">
          {avvisi.map((a) => (
            <div key={a.id} className="rounded-[24px] border border-[#e6ebe5] bg-[linear-gradient(180deg,_#ffffff,_#fbfcfa)] px-4 py-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="truncate text-sm font-semibold text-gray-900">Anno {a.anno_tributario}</p>
                    <span className="rounded-full bg-[#eef3ec] px-2.5 py-1 text-xs font-medium text-[#1D4E35]">
                      CNC {a.codice_cnc}
                    </span>
                    {a.codice_utenza ? (
                      <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600">
                        Utenza {a.codice_utenza}
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-1 truncate text-xs leading-5 text-gray-500">
                    {a.display_name ?? a.nominativo_raw ?? "Nominativo non disponibile"}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Totale €</p>
                  <p className="mt-1 text-sm font-semibold text-gray-900">{formatEuro(a.importo_totale_euro)}</p>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${a.subject_id ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
                  {a.subject_id ? "Collegato" : "Orfano"}
                </span>
                <div className="flex flex-wrap gap-2">
                  <Link
                    href="/ruolo/avvisi"
                    className="inline-flex items-center gap-2 rounded-xl border border-[#d6e5db] bg-white px-3 py-2 text-xs font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]"
                  >
                    <SearchIcon className="h-3.5 w-3.5" />
                    Apri lista
                  </Link>
                  <Link
                    href={`/ruolo/avvisi/${a.id}`}
                    className="inline-flex items-center gap-2 rounded-xl border border-[#d6e5db] bg-white px-3 py-2 text-xs font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]"
                  >
                    <DocumentIcon className="h-3.5 w-3.5" />
                    Apri dettaglio
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
