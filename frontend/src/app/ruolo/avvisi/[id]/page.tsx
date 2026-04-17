"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceMiniStat,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { RuoloModulePage } from "@/components/ruolo/module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon, FolderIcon, LockIcon } from "@/components/ui/icons";
import { getStoredAccessToken } from "@/lib/auth";
import { getAvviso } from "@/lib/ruolo-api";
import type { RuoloAvvisoDetailResponse, RuoloPartitaResponse } from "@/types/ruolo";

function formatEuro(value: number | null | undefined): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(value);
}

function LabelValue({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-[#e3e9e0] bg-[#fbfcfb] p-4">
      <dt className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">{label}</dt>
      <dd className="mt-2 text-sm leading-6 text-gray-900">{value || "—"}</dd>
    </div>
  );
}

function PartitaCard({ partita }: { partita: RuoloPartitaResponse }) {
  const [expanded, setExpanded] = useState(false);
  const particelleTotal = useMemo(
    () =>
      partita.particelle.reduce(
        (sum, item) => sum + (item.importo_manut ?? 0) + (item.importo_irrig ?? 0) + (item.importo_ist ?? 0),
        0,
      ),
    [partita.particelle],
  );

  return (
    <div className="rounded-[24px] border border-[#e6ebe5] bg-[linear-gradient(180deg,_#ffffff,_#fbfcfa)] shadow-sm">
      <button
        type="button"
        className="flex w-full flex-wrap items-center justify-between gap-4 px-5 py-4 text-left"
        onClick={() => setExpanded((value) => !value)}
      >
        <div>
          <p className="text-sm font-semibold text-gray-900">{partita.comune_nome ?? "Comune non disponibile"}</p>
          <p className="mt-1 text-xs leading-5 text-gray-500">
            Partita {partita.codice_partita || "—"} · {partita.particelle.length} particelle
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Totale partita</p>
            <p className="mt-1 text-sm font-semibold text-gray-900">
              {formatEuro((partita.importo_0648 ?? 0) + (partita.importo_0985 ?? 0) + (partita.importo_0668 ?? 0))}
            </p>
          </div>
          <span className="text-xs text-gray-400">{expanded ? "▲ Chiudi" : "▼ Apri"}</span>
        </div>
      </button>

      {expanded ? (
        <div className="border-t border-[#edf1eb] px-5 py-5">
          {partita.co_intestati_raw ? (
            <div className="mb-4 rounded-2xl border border-[#e3e9e0] bg-[#fbfcfb] px-4 py-3 text-sm text-gray-600">
              <span className="font-semibold text-gray-900">Co-intestatari:</span> {partita.co_intestati_raw}
            </div>
          ) : null}
          {partita.particelle.length === 0 ? (
            <EmptyState
              icon={FolderIcon}
              title="Nessuna particella"
              description="La partita non contiene particelle associate nel dataset storico importato."
            />
          ) : (
            <div className="space-y-3">
              {partita.particelle.map((p) => (
                <div key={p.id} className="rounded-2xl border border-[#e3e9e0] bg-[#fbfcfb] p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-gray-900">
                        Foglio {p.foglio} · Particella {p.particella}{p.subalterno ? ` · Sub ${p.subalterno}` : ""}
                      </p>
                      <p className="mt-1 text-xs leading-5 text-gray-500">
                        Coltura {p.coltura ?? "—"} · Sup. cat. {p.sup_catastale_ha != null ? `${p.sup_catastale_ha.toFixed(4)} ha` : "—"} · Sup. irr. {p.sup_irrigata_ha != null ? `${p.sup_irrigata_ha.toFixed(4)} ha` : "—"}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Totale particella</p>
                      <p className="mt-1 text-sm font-semibold text-gray-900">
                        {formatEuro((p.importo_manut ?? 0) + (p.importo_irrig ?? 0) + (p.importo_ist ?? 0))}
                      </p>
                    </div>
                  </div>
                  <div className="mt-4 grid gap-3 sm:grid-cols-3">
                    <div className="rounded-xl border border-white bg-white px-3 py-2">
                      <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Manutenzione</p>
                      <p className="mt-1 font-semibold text-gray-900">{formatEuro(p.importo_manut)}</p>
                    </div>
                    <div className="rounded-xl border border-white bg-white px-3 py-2">
                      <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Irrigazione</p>
                      <p className="mt-1 font-semibold text-gray-900">{formatEuro(p.importo_irrig)}</p>
                    </div>
                    <div className="rounded-xl border border-white bg-white px-3 py-2">
                      <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Sistemazione</p>
                      <p className="mt-1 font-semibold text-gray-900">{formatEuro(p.importo_ist)}</p>
                    </div>
                  </div>
                </div>
              ))}
              <div className="rounded-2xl border border-[#d6e5db] bg-white px-4 py-3 text-sm text-gray-600">
                <span className="font-semibold text-gray-900">Totale particelle della partita:</span> {formatEuro(particelleTotal)}
              </div>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}

export default function AvvisoDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [token, setToken] = useState<string | null>(null);
  const [avviso, setAvviso] = useState<RuoloAvvisoDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  useEffect(() => {
    if (!token || !id) return;
    setLoading(true);
    getAvviso(token, id)
      .then(setAvviso)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Errore"))
      .finally(() => setLoading(false));
  }, [token, id]);

  if (loading) {
    return (
      <RuoloModulePage title="Avviso" description="Dettaglio avviso ruolo." breadcrumb="Dettaglio avviso">
        <p className="text-sm text-gray-400">Caricamento...</p>
      </RuoloModulePage>
    );
  }

  if (error || !avviso) {
    return (
      <RuoloModulePage title="Avviso" description="Dettaglio avviso ruolo." breadcrumb="Dettaglio avviso">
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error ?? "Avviso non trovato."}
        </div>
      </RuoloModulePage>
    );
  }

  return (
    <RuoloModulePage
      title={`Avviso ${avviso.codice_cnc}`}
      description={`Anno ${avviso.anno_tributario} — ${avviso.nominativo_raw ?? avviso.codice_cnc}`}
      breadcrumb="Dettaglio avviso"
    >
      <div className="space-y-8">
        <div className="flex items-center justify-between gap-4">
          <Link
            href="/ruolo/avvisi"
            className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-[#1D4E35]"
          >
            ← Torna agli avvisi
          </Link>
          {avviso.subject_id ? (
            <Link
              href={`/utenze/subjects/${avviso.subject_id}`}
              className="rounded-xl border border-[#d6e5db] bg-white px-4 py-2 text-sm font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]"
            >
              Apri soggetto GAIA
            </Link>
          ) : null}
        </div>

        <ModuleWorkspaceHero
          badge={
            <>
              <LockIcon className="h-3.5 w-3.5" />
              Scheda avviso
            </>
          }
          title={avviso.display_name ?? avviso.nominativo_raw ?? avviso.codice_cnc}
          description={`Anno ${avviso.anno_tributario} · CNC ${avviso.codice_cnc} · CF/P.IVA ${avviso.codice_fiscale_raw ?? "non disponibile"}. Consulta partite e particelle del ruolo storicizzato per questo avviso.`}
          actions={
            <>
              <ModuleWorkspaceNoticeCard
                title={avviso.subject_id ? "Avviso collegato" : "Avviso non collegato"}
                description={
                  avviso.subject_id
                    ? `Il soggetto GAIA è già associato all'avviso con display name ${avviso.display_name ?? avviso.subject_id}.`
                    : "L'avviso non è ancora collegato a un soggetto GAIA e richiede verifica anagrafica."
                }
                tone={avviso.subject_id ? "success" : "warning"}
              />
              <ModuleWorkspaceNoticeCard
                title={`${avviso.partite.length} partite`}
                description="Espandi ogni partita per consultare le particelle storiche e i relativi importi puntuali."
                tone="info"
              />
            </>
          }
        >
          <ModuleWorkspaceKpiRow>
            <ModuleWorkspaceKpiTile
              label="Totale avviso"
              value={formatEuro(avviso.importo_totale_euro)}
              hint="Importo complessivo"
            />
            <ModuleWorkspaceKpiTile
              label="Partite"
              value={avviso.partite.length}
              hint="Comuni / partite associate"
            />
            <ModuleWorkspaceKpiTile
              label="Codice utenza"
              value={avviso.codice_utenza ?? "—"}
              hint="Riferimento utenza"
            />
            <ModuleWorkspaceKpiTile
              label="Stato soggetto"
              value={avviso.subject_id ? "Collegato" : "Orfano"}
              hint={avviso.subject_id ? "Link anagrafico presente" : "Da collegare"}
              variant={avviso.subject_id ? "emerald" : "amber"}
            />
          </ModuleWorkspaceKpiRow>
        </ModuleWorkspaceHero>

        <section className="grid gap-4 xl:grid-cols-[1.05fr,0.95fr]">
          <article className="rounded-[28px] border border-[#d8dfd3] bg-white shadow-panel">
            <div className="border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(29,78,53,0.06),_rgba(255,255,255,0.92))] px-6 py-5">
              <p className="inline-flex items-center gap-2 rounded-full bg-[#e8f2ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
                <DocumentIcon className="h-3.5 w-3.5" />
                Anagrafica avviso
              </p>
              <p className="mt-3 text-lg font-semibold text-gray-900">Dati identificativi e collegamenti.</p>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-600">
                Qui trovi i riferimenti amministrativi dell&apos;avviso importato, insieme ai dati raw acquisiti dal file Ruolo.
              </p>
            </div>
            <div className="grid gap-4 p-6 sm:grid-cols-2 lg:grid-cols-3">
              <LabelValue label="Anno tributario" value={avviso.anno_tributario} />
              <LabelValue label="Codice CNC" value={<span className="font-mono text-xs">{avviso.codice_cnc}</span>} />
              <LabelValue label="CF / P.IVA" value={<span className="font-mono text-xs">{avviso.codice_fiscale_raw}</span>} />
              <LabelValue label="Codice utenza" value={avviso.codice_utenza} />
              <LabelValue label="Domicilio" value={avviso.domicilio_raw} />
              <LabelValue label="Residenza" value={avviso.residenza_raw} />
              {avviso.subject_id ? (
                <LabelValue
                  label="Soggetto GAIA"
                  value={
                    <Link
                      href={`/utenze/subjects/${avviso.subject_id}`}
                      className="text-[#1D4E35] hover:underline"
                    >
                      {avviso.display_name ?? avviso.subject_id}
                    </Link>
                  }
                />
              ) : null}
            </div>
          </article>

          <article className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
            <div>
              <p className="inline-flex items-center gap-2 rounded-full bg-[#eef3ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
                <FolderIcon className="h-3.5 w-3.5" />
                Ripartizione importi
              </p>
              <p className="mt-3 text-lg font-semibold text-gray-900">Quadro economico sintetico dell&apos;avviso.</p>
              <p className="mt-2 text-sm leading-6 text-gray-600">
                Gli importi sono separati per tributo e aiutano a leggere rapidamente il peso amministrativo della posizione.
              </p>
            </div>
            <div className="mt-6 grid gap-3">
              <ModuleWorkspaceMiniStat
                eyebrow="Tributo 0648"
                value={formatEuro(avviso.importo_totale_0648)}
                description="Quota manutenzione consortile."
                compact
              />
              <ModuleWorkspaceMiniStat
                eyebrow="Tributo 0985"
                value={formatEuro(avviso.importo_totale_0985)}
                description="Quota irrigazione."
                compact
              />
              <ModuleWorkspaceMiniStat
                eyebrow="Tributo 0668"
                value={formatEuro(avviso.importo_totale_0668)}
                description="Quota sistemazione idraulica."
                compact
              />
              <ModuleWorkspaceMiniStat
                eyebrow="Totale complessivo"
                value={formatEuro(avviso.importo_totale_euro)}
                description="Somma finale dell'avviso."
                tone="success"
                compact
              />
            </div>
          </article>
        </section>

        <section className="rounded-[28px] border border-[#d8dfd3] bg-white shadow-panel">
          <div className="border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(29,78,53,0.06),_rgba(255,255,255,0.92))] px-6 py-5">
            <p className="inline-flex items-center gap-2 rounded-full bg-[#e8f2ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
              <FolderIcon className="h-3.5 w-3.5" />
              Partite e particelle
            </p>
            <p className="mt-3 text-lg font-semibold text-gray-900">Naviga il dettaglio storico del ruolo.</p>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-600">
              Ogni partita rappresenta una vista per comune; espandi la card per leggere le particelle importate e gli importi puntuali.
            </p>
          </div>
          <div className="p-6">
            {avviso.partite.length === 0 ? (
              <EmptyState
                icon={FolderIcon}
                title="Nessuna partita trovata"
                description="L'avviso non contiene partite associate nel dataset Ruolo disponibile."
              />
            ) : (
              <div className="space-y-3">
                {avviso.partite.map((p) => (
                  <PartitaCard key={p.id} partita={p} />
                ))}
              </div>
            )}
          </div>
        </section>
      </div>
    </RuoloModulePage>
  );
}
