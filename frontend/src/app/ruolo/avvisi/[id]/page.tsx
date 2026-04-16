"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

import { RuoloModulePage } from "@/components/ruolo/module-page";
import { getStoredAccessToken } from "@/lib/auth";
import { getAvviso } from "@/lib/ruolo-api";
import type { RuoloAvvisoDetailResponse, RuoloPartitaResponse } from "@/types/ruolo";

function formatEuro(value: number | null | undefined): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(value);
}

function LabelValue({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wider text-gray-400">{label}</dt>
      <dd className="mt-0.5 text-sm text-gray-800">{value || "—"}</dd>
    </div>
  );
}

function PartitaCard({ partita }: { partita: RuoloPartitaResponse }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="rounded-xl border border-gray-100 bg-gray-50">
      <button
        type="button"
        className="flex w-full items-center justify-between px-4 py-3 text-left"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex items-center gap-3">
          <span className="font-medium text-gray-800">{partita.comune_nome ?? "—"}</span>
          {partita.codice_partita && (
            <span className="text-xs text-gray-400">Partita {partita.codice_partita}</span>
          )}
        </div>
        <div className="flex items-center gap-4 text-sm text-gray-600">
          <span>{formatEuro(partita.importo_0648)} (0648)</span>
          <span>{formatEuro(partita.importo_0985)} (0985)</span>
          <span>{formatEuro(partita.importo_0668)} (0668)</span>
          <span className="text-xs text-gray-400">{expanded ? "▲" : "▼"}</span>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-gray-100 px-4 py-4">
          {partita.co_intestati_raw && (
            <p className="mb-3 text-xs text-gray-500">Co-intestatari: {partita.co_intestati_raw}</p>
          )}
          {partita.particelle.length === 0 ? (
            <p className="text-xs text-gray-400">Nessuna particella.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-gray-200 text-left font-medium uppercase tracking-wider text-gray-400">
                    <th className="py-2 pr-3">Foglio</th>
                    <th className="py-2 pr-3">Particella</th>
                    <th className="py-2 pr-3">Sub.</th>
                    <th className="py-2 pr-3">Sup. Cat. (ha)</th>
                    <th className="py-2 pr-3">Sup. Irr. (ha)</th>
                    <th className="py-2 pr-3">Coltura</th>
                    <th className="py-2 pr-3">Manut.</th>
                    <th className="py-2 pr-3">Irrig.</th>
                    <th className="py-2 pr-3">Ist.</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {partita.particelle.map((p) => (
                    <tr key={p.id} className="hover:bg-white">
                      <td className="py-2 pr-3 font-medium text-gray-700">{p.foglio}</td>
                      <td className="py-2 pr-3 text-gray-700">{p.particella}</td>
                      <td className="py-2 pr-3 text-gray-500">{p.subalterno ?? "—"}</td>
                      <td className="py-2 pr-3 text-gray-700">
                        {p.sup_catastale_ha != null ? p.sup_catastale_ha.toFixed(4) : "—"}
                      </td>
                      <td className="py-2 pr-3 text-gray-700">
                        {p.sup_irrigata_ha != null ? p.sup_irrigata_ha.toFixed(4) : "—"}
                      </td>
                      <td className="py-2 pr-3 text-gray-500">{p.coltura ?? "—"}</td>
                      <td className="py-2 pr-3 text-gray-700">{formatEuro(p.importo_manut)}</td>
                      <td className="py-2 pr-3 text-gray-700">{formatEuro(p.importo_irrig)}</td>
                      <td className="py-2 pr-3 text-gray-700">{formatEuro(p.importo_ist)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
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
      <RuoloModulePage title="Avviso" description="Dettaglio avviso ruolo." breadcrumb="Dettaglio">
        <p className="text-sm text-gray-400">Caricamento...</p>
      </RuoloModulePage>
    );
  }

  if (error || !avviso) {
    return (
      <RuoloModulePage title="Avviso" description="Dettaglio avviso ruolo." breadcrumb="Dettaglio">
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
      <div className="space-y-6">
        {/* Back link */}
        <Link
          href="/ruolo/avvisi"
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-[#1D4E35]"
        >
          ← Torna agli avvisi
        </Link>

        {/* Header card */}
        <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center gap-3">
            <h2 className="text-xl font-semibold text-gray-800">
              {avviso.display_name ?? avviso.nominativo_raw ?? avviso.codice_cnc}
            </h2>
            {avviso.subject_id ? (
              <span className="rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700">
                Collegato
              </span>
            ) : (
              <span className="rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-orange-600">
                Non collegato
              </span>
            )}
          </div>

          <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            <LabelValue label="Anno tributario" value={avviso.anno_tributario} />
            <LabelValue label="Codice CNC" value={<span className="font-mono text-xs">{avviso.codice_cnc}</span>} />
            <LabelValue label="CF / PIVA" value={<span className="font-mono text-xs">{avviso.codice_fiscale_raw}</span>} />
            <LabelValue label="Codice utenza" value={avviso.codice_utenza} />
            <LabelValue label="Domicilio" value={avviso.domicilio_raw} />
            <LabelValue label="Residenza" value={avviso.residenza_raw} />
            {avviso.subject_id && (
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
            )}
          </dl>
        </div>

        {/* Importi */}
        <div className="grid gap-4 sm:grid-cols-4">
          {[
            { label: "Manutenzione (0648)", value: avviso.importo_totale_0648 },
            { label: "Irrigazione (0985)", value: avviso.importo_totale_0985 },
            { label: "Sistemazione (0668)", value: avviso.importo_totale_0668 },
            { label: "Totale (€)", value: avviso.importo_totale_euro },
          ].map(({ label, value }) => (
            <div key={label} className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
              <p className="text-xs text-gray-400">{label}</p>
              <p className="mt-1 text-lg font-semibold text-gray-800">{formatEuro(value)}</p>
            </div>
          ))}
        </div>

        {/* Partite */}
        <div>
          <h3 className="mb-3 text-sm font-medium uppercase tracking-wider text-gray-400">
            Partite ({avviso.partite.length})
          </h3>
          <div className="space-y-3">
            {avviso.partite.length === 0 ? (
              <p className="text-sm text-gray-400">Nessuna partita trovata.</p>
            ) : (
              avviso.partite.map((p) => <PartitaCard key={p.id} partita={p} />)
            )}
          </div>
        </div>
      </div>
    </RuoloModulePage>
  );
}
