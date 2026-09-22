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
import {
  buildRuoloAvvisoDigitalDeliveryLabel,
  buildRuoloAvvisoRegisteredMailLabel,
} from "@/lib/ruolo-avvisi-notifications";
import type { RuoloAvvisoListItemResponse } from "@/types/ruolo";

type Props = {
  subjectId: string;
  token: string;
};

function formatEuro(value: number | null | undefined): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(value);
}

function RuoloAvvisoCard({ avviso }: { avviso: RuoloAvvisoListItemResponse }) {
  const digitalDeliveryLabel = buildRuoloAvvisoDigitalDeliveryLabel(avviso);
  const registeredMailLabel = buildRuoloAvvisoRegisteredMailLabel(avviso);
  return (
    <div className="rounded-[24px] border border-[#e6ebe5] bg-[linear-gradient(180deg,_#ffffff,_#fbfcfa)] px-4 py-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="truncate text-sm font-semibold text-gray-900">Anno {avviso.anno_tributario}</p>
            <span className="rounded-full bg-[#eef3ec] px-2.5 py-1 text-xs font-medium text-[#1D4E35]">CNC {avviso.codice_cnc}</span>
            {avviso.codice_utenza ? (
              <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600">Utenza {avviso.codice_utenza}</span>
            ) : null}
          </div>
          <p className="mt-1 truncate text-xs leading-5 text-gray-500">
            {avviso.display_name ?? avviso.nominativo_raw ?? "Nominativo non disponibile"}
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Totale €</p>
          <p className="mt-1 text-sm font-semibold text-gray-900">{formatEuro(avviso.importo_totale_euro)}</p>
        </div>
      </div>
      <div className="mt-4 space-y-2" aria-label={`Notifiche ruolo ${avviso.codice_cnc}`}>
        {digitalDeliveryLabel ? (
          <p className="rounded-2xl border border-sky-100 bg-sky-50/70 px-3 py-2 text-xs leading-5 text-sky-900">{digitalDeliveryLabel}</p>
        ) : null}
        {registeredMailLabel ? (
          <p className="rounded-2xl border border-amber-100 bg-amber-50/70 px-3 py-2 text-xs leading-5 text-amber-900">
            <span className="font-semibold">Associata al ruolo.</span> {registeredMailLabel}
          </p>
        ) : null}
        {!digitalDeliveryLabel && !registeredMailLabel ? (
          <p className="rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-500">
            Nessuna PEC o raccomandata associata al ruolo.
          </p>
        ) : null}
      </div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${avviso.subject_id ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
          {avviso.subject_id ? "Collegato" : "Orfano"}
        </span>
        <div className="flex flex-wrap gap-2">
          <Link href="/ruolo/avvisi" className="inline-flex items-center gap-2 rounded-xl border border-[#d6e5db] bg-white px-3 py-2 text-xs font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]">
            <SearchIcon className="h-3.5 w-3.5" />
            Apri lista
          </Link>
          <Link href={`/ruolo/avvisi/${avviso.id}`} className="inline-flex items-center gap-2 rounded-xl border border-[#d6e5db] bg-white px-3 py-2 text-xs font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]">
            <DocumentIcon className="h-3.5 w-3.5" />
            Apri dettaglio
          </Link>
        </div>
      </div>
    </div>
  );
}

export function RuoloAvvisiSection({ subjectId, token }: Props) {
  const [avvisi, setAvvisi] = useState<RuoloAvvisoListItemResponse[]>([]);
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
  const registeredMailCount = avvisi.filter((avviso) => Boolean(avviso.registered_mail)).length;
  const totaleEuro = avvisi.reduce((sum, avviso) => sum + (avviso.importo_totale_euro ?? 0), 0);
  const latestYear = Math.max(...avvisi.map((avviso) => avviso.anno_tributario));

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
                title={`Ultimo anno disponibile: ${latestYear}`}
                description={`${avvisi.length} avvis${avvisi.length !== 1 ? "i" : "o"} associat${avvisi.length !== 1 ? "i" : "o"} al soggetto corrente.`}
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
            description={`${avvisi.length} avvis${avvisi.length !== 1 ? "i" : "o"} trovat${avvisi.length !== 1 ? "i" : "o"} sul soggetto.`}
            compact
          />
          <ModuleWorkspaceMiniStat eyebrow="Collegati" value={linkedCount} description="Rientrano nel perimetro GAIA del soggetto corrente." tone="success" compact />
          <ModuleWorkspaceMiniStat
            eyebrow="Via raccomandata"
            value={registeredMailCount}
            description="Ruoli con una raccomandata Poste Online associata."
            compact
          />
        </div>
        <div className="space-y-3">
          {avvisi.map((avviso) => <RuoloAvvisoCard avviso={avviso} key={avviso.id} />)}
        </div>
      </div>
    </section>
  );
}
