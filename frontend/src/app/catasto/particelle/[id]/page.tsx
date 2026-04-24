"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { CatastoPage } from "@/components/catasto/catasto-page";
import { AlertBanner } from "@/components/ui/alert-banner";
import { MetricCard } from "@/components/ui/metric-card";
import { DataTable } from "@/components/table/data-table";
import type { ColumnDef } from "@tanstack/react-table";
import { AnomaliaStatusBadge } from "@/components/catasto/AnomaliaStatusBadge";
import { AnomaliaStatusPill } from "@/components/catasto/AnomaliaStatusPill";
import {
  catastoGetParticella,
  catastoGetParticellaAnomalie,
  catastoGetParticellaConsorzio,
  catastoGetParticellaHistory,
  catastoGetParticellaUtenze,
  catastoUpdateAnomalia,
} from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatAnomalia, CatParticellaConsorzio, CatParticellaDetail, CatParticellaHistory, CatUtenzaIrrigua } from "@/types/catasto";

function formatHaFromMq(value: string | number): string {
  const mq = typeof value === "number" ? value : Number(value);
  const ha = (Number.isFinite(mq) ? mq : 0) / 10_000;
  return new Intl.NumberFormat("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(ha);
}

function renderResolutionLabel(mode: string | null | undefined): string {
  switch (mode) {
    case "swapped_arborea_terralba":
      return "Comune corretto da GAIA (Arborea/Terralba)";
    case "source_match":
      return "Comune sorgente confermato";
    case "resolved_from_particella":
      return "Comune risolto dalla particella GAIA";
    case "source_only":
      return "Solo sorgente Capacitas";
    default:
      return mode ?? "—";
  }
}

export default function CatastoParticellaDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const particellaId = params.id;
  const isEmbedded = searchParams.get("embedded") === "1";

  const [item, setItem] = useState<CatParticellaDetail | null>(null);
  const [consorzio, setConsorzio] = useState<CatParticellaConsorzio | null>(null);
  const [history, setHistory] = useState<CatParticellaHistory[]>([]);
  const [anno, setAnno] = useState<number>(new Date().getFullYear());
  const [utenze, setUtenze] = useState<CatUtenzaIrrigua[]>([]);
  const [anomalie, setAnomalie] = useState<CatAnomalia[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load(): Promise<void> {
      const token = getStoredAccessToken();
      if (!token) return;

      setIsLoading(true);
      try {
        const [p, c, h, u, a] = await Promise.all([
          catastoGetParticella(token, particellaId),
          catastoGetParticellaConsorzio(token, particellaId),
          catastoGetParticellaHistory(token, particellaId),
          catastoGetParticellaUtenze(token, particellaId, { anno }),
          catastoGetParticellaAnomalie(token, particellaId, { anno }),
        ]);

        // Se l'anno corrente non ha dati, prova a selezionare automaticamente
        // l'ultimo anno precedente che abbia almeno un record.
        const currentYear = new Date().getFullYear();
        if (anno === currentYear && u.length === 0 && a.length === 0) {
          const [uAll, aAll] = await Promise.all([
            catastoGetParticellaUtenze(token, particellaId),
            catastoGetParticellaAnomalie(token, particellaId),
          ]);
          const fallbackYear = Math.max(
            ...(uAll.map((x) => x.anno_campagna).filter((x): x is number => typeof x === "number" && Number.isFinite(x)) || []),
            ...(aAll.map((x) => x.anno_campagna).filter((x): x is number => typeof x === "number" && Number.isFinite(x)) || []),
            -Infinity,
          );
          if (Number.isFinite(fallbackYear) && fallbackYear !== anno) {
            setAnno(fallbackYear);
            return;
          }
        }

        setItem(p);
        setConsorzio(c);
        setHistory(h);
        setUtenze(u);
        setAnomalie(a);
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Errore caricamento particella");
      } finally {
        setIsLoading(false);
      }
    }
    void load();
  }, [anno, particellaId]);

  const columns = useMemo<ColumnDef<CatParticellaHistory>[]>(
    () => [
      {
        header: "Validità",
        id: "valid",
        cell: ({ row }) => (
          <span className="text-sm text-gray-700">
            {row.original.valid_from} → {row.original.valid_to}
          </span>
        ),
      },
      { header: "Distretto", accessorKey: "num_distretto", cell: ({ row }) => <span className="text-sm text-gray-700">{row.original.num_distretto ?? "—"}</span> },
      {
        header: "Sup. catastale (ha)",
        id: "supCatastale",
        cell: ({ row }) => <span className="text-sm text-gray-700">{row.original.superficie_mq ? `${formatHaFromMq(row.original.superficie_mq)} ha` : "—"}</span>,
      },
      {
        header: "Sup. grafica (ha)",
        id: "supGrafica",
        cell: ({ row }) => <span className="text-sm text-gray-700">{row.original.superficie_grafica_mq ? `${formatHaFromMq(row.original.superficie_grafica_mq)} ha` : "—"}</span>,
      },
      { header: "Reason", accessorKey: "change_reason", cell: ({ row }) => <span className="text-sm text-gray-600">{row.original.change_reason ?? "—"}</span> },
    ],
    [],
  );

  const utenzeColumns = useMemo<ColumnDef<CatUtenzaIrrigua>[]>(
    () => [
      { header: "Anno", accessorKey: "anno_campagna", cell: ({ row }) => <span className="text-sm text-gray-700">{row.original.anno_campagna}</span> },
      { header: "CCO", accessorKey: "cco", cell: ({ row }) => <span className="text-sm text-gray-700">{row.original.cco ?? "—"}</span> },
      { header: "CF", accessorKey: "codice_fiscale", cell: ({ row }) => <span className="text-sm text-gray-700">{row.original.codice_fiscale ?? "—"}</span> },
      {
        header: "0648 (€)",
        id: "i0648",
        cell: ({ row }) => <span className="text-sm text-gray-700">{row.original.importo_0648 ?? "—"}</span>,
      },
      {
        header: "0985 (€)",
        id: "i0985",
        cell: ({ row }) => <span className="text-sm text-gray-700">{row.original.importo_0985 ?? "—"}</span>,
      },
    ],
    [],
  );

  const anomalieColumns = useMemo<ColumnDef<CatAnomalia>[]>(
    () => [
      { header: "Sev", accessorKey: "severita", cell: ({ row }) => <AnomaliaStatusBadge severita={row.original.severita} /> },
      { header: "Tipo", accessorKey: "tipo", cell: ({ row }) => <span className="text-sm font-medium text-gray-900">{row.original.tipo}</span> },
      { header: "Stato", accessorKey: "status", cell: ({ row }) => <AnomaliaStatusPill status={row.original.status} /> },
      { header: "Descrizione", accessorKey: "descrizione", cell: ({ row }) => <span className="text-sm text-gray-600">{row.original.descrizione ?? "—"}</span> },
      {
        header: "Azioni",
        id: "actions",
        cell: ({ row }) => (
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-secondary !px-2 !py-1 text-xs"
              onClick={async () => {
                const token = getStoredAccessToken();
                if (!token) return;
                await catastoUpdateAnomalia(token, row.original.id, { status: "chiusa" });
                const refreshed = await catastoGetParticellaAnomalie(token, particellaId, { anno });
                setAnomalie(refreshed);
              }}
            >
              Chiudi
            </button>
            <button
              type="button"
              className="btn-secondary !px-2 !py-1 text-xs"
              onClick={async () => {
                const token = getStoredAccessToken();
                if (!token) return;
                await catastoUpdateAnomalia(token, row.original.id, { status: "ignora" });
                const refreshed = await catastoGetParticellaAnomalie(token, particellaId, { anno });
                setAnomalie(refreshed);
              }}
            >
              Ignora
            </button>
            <button
              type="button"
              className="btn-secondary !px-2 !py-1 text-xs"
              onClick={async () => {
                const token = getStoredAccessToken();
                if (!token) return;
                await catastoUpdateAnomalia(token, row.original.id, { status: "aperta" });
                const refreshed = await catastoGetParticellaAnomalie(token, particellaId, { anno });
                setAnomalie(refreshed);
              }}
            >
              Riapri
            </button>
          </div>
        ),
      },
    ],
    [anno, particellaId],
  );

  const consorzioOccupancyColumns = useMemo<ColumnDef<NonNullable<CatParticellaConsorzio["units"][number]["occupancies"]>[number]>[]>(
    () => [
      { header: "Relazione", accessorKey: "relationship_type", cell: ({ row }) => <span className="text-sm text-gray-700">{row.original.relationship_type}</span> },
      { header: "CCO", accessorKey: "cco", cell: ({ row }) => <span className="text-sm text-gray-700">{row.original.cco ?? "—"}</span> },
      { header: "Sorgente", accessorKey: "source_type", cell: ({ row }) => <span className="text-sm text-gray-700">{row.original.source_type}</span> },
      {
        header: "Periodo",
        id: "periodo",
        cell: ({ row }) => (
          <span className="text-sm text-gray-700">
            {row.original.valid_from ?? "—"} → {row.original.valid_to ?? "—"}
          </span>
        ),
      },
      {
        header: "Stato",
        id: "current",
        cell: ({ row }) => (
          <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${row.original.is_current ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>
            {row.original.is_current ? "Corrente" : "Storico"}
          </span>
        ),
      },
    ],
    [],
  );

  const reference = item ? `Fg.${item.foglio} Part.${item.particella}${item.subalterno ? ` Sub.${item.subalterno}` : ""}` : "Particella";

  return (
    <CatastoPage
      title={reference}
      description="Scheda particella con dati catastali, anagrafica collegata e storico SCD2."
      breadcrumb="Catasto / Particelle / Dettaglio"
      requiredModule="catasto"
    >
      <div className="page-stack">
        {isEmbedded ? (
          <div className="flex justify-start">
            <button type="button" className="btn-secondary" onClick={() => router.back()}>
              Indietro
            </button>
          </div>
        ) : null}

        {error ? (
          <AlertBanner variant="danger" title="Errore caricamento">
            {error}
          </AlertBanner>
        ) : null}

        <article className="panel-card">
          {isLoading && !item ? (
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-500">Caricamento…</div>
          ) : !item ? (
            <AlertBanner variant="warning" title="Particella non trovata">
              Non risultano dati per l’ID richiesto.
            </AlertBanner>
          ) : (
            <>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0">
                  <p className="text-lg font-semibold text-gray-900">{reference}</p>
                  <p className="mt-1 text-sm text-gray-500">
                    Comune: <span className="font-medium text-gray-800">{item.nome_comune ?? item.cod_comune_capacitas}</span> · Distretto:{" "}
                    <span className="font-medium text-gray-800">{item.num_distretto ?? "—"}</span>
                    {item.fuori_distretto ? <span className="ml-2 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">Fuori distretto</span> : null}
                  </p>
                </div>
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-4">
                <MetricCard label="Sup. catastale (ha)" value={item.superficie_mq ? `${formatHaFromMq(item.superficie_mq)} ha` : "—"} />
                <MetricCard label="Sup. grafica (ha)" value={item.superficie_grafica_mq ? `${formatHaFromMq(item.superficie_grafica_mq)} ha` : "—"} />
                <MetricCard label="Valid from" value={item.valid_from} />
                <MetricCard label="Source" value={item.source_type} />
                <MetricCard label="Current" value={item.is_current ? "Sì" : "No"} variant={item.is_current ? "success" : "warning"} />
              </div>
            </>
          )}
        </article>

        <article className="panel-card">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-gray-900">Catasto consortile</p>
              <p className="mt-1 text-sm text-gray-500">Vista operativa del Consorzio: distingue utilizzatore/pagatore annuale e intestatari proprietari rilevati in Capacitas.</p>
            </div>
            <p className="text-sm text-gray-500">{isLoading ? "Caricamento…" : `${consorzio?.units.length ?? 0} unità`}</p>
          </div>

          {isLoading && !consorzio ? (
            <div className="mt-4 rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-500">Caricamento…</div>
          ) : !consorzio || consorzio.units.length === 0 ? (
            <div className="mt-4 rounded-xl border border-dashed border-gray-200 bg-gray-50 p-4 text-sm text-gray-500">
              Nessun dato consortile ancora consolidato per questa particella.
            </div>
          ) : (
            <div className="mt-4 space-y-4">
              {consorzio.units.map((unit) => (
                <div key={unit.id} className="rounded-2xl border border-[#e5ebe2] bg-[#fbfcfb] p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-gray-900">
                        Unità {unit.foglio ?? "—"}/{unit.particella ?? "—"}{unit.subalterno ? `/${unit.subalterno}` : ""}
                      </p>
                      <p className="mt-1 text-sm text-gray-600">
                        Comune reale: <span className="font-medium text-gray-800">{unit.comune_label ?? unit.cod_comune_capacitas ?? "—"}</span>
                        {" · "}
                        Comune sorgente Capacitas:{" "}
                        <span className="font-medium text-gray-800">
                          {unit.source_comune_resolved_label ?? unit.source_comune_label ?? unit.source_cod_comune_capacitas ?? "—"}
                        </span>
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <span className="rounded-full bg-[#eef5f1] px-2.5 py-1 text-xs font-medium text-[#1D4E35]">
                        {renderResolutionLabel(unit.comune_resolution_mode)}
                      </span>
                      {unit.source_codice_catastale ? (
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                          Belfiore sorgente {unit.source_codice_catastale}
                        </span>
                      ) : null}
                    </div>
                  </div>

                  <div className="mt-4 grid gap-3 md:grid-cols-4">
                    <MetricCard label="Ultimo rilevamento" value={unit.source_last_seen ?? "—"} />
                    <MetricCard label="Primo rilevamento" value={unit.source_first_seen ?? "—"} />
                    <MetricCard label="Occupazioni" value={String(unit.occupancies.length)} />
                    <MetricCard label="Attiva" value={unit.is_active ? "Sì" : "No"} variant={unit.is_active ? "success" : "warning"} />
                  </div>

                  <div className="mt-4 rounded-xl border border-white bg-white p-3">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-sm font-medium text-gray-900">Intestatari proprietari</p>
                        <p className="mt-1 text-sm text-gray-500">Proprietari / aventi titolo rilevati in Capacitas. Non coincidono necessariamente con chi usa o paga l’acqua nell’annualità.</p>
                      </div>
                      <p className="text-sm text-gray-500">{unit.intestatari_proprietari.length} righe</p>
                    </div>
                    {unit.intestatari_proprietari.length === 0 ? (
                      <p className="mt-3 text-sm text-gray-500">Nessun intestatario strutturato ancora disponibile per questa unità.</p>
                    ) : (
                      <div className="mt-3 space-y-2">
                        {unit.intestatari_proprietari.map((owner) => (
                          <div key={owner.id} className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2">
                            <p className="text-sm font-medium text-gray-900">
                              {owner.denominazione ?? "—"}
                              {owner.deceduto ? <span className="ml-2 rounded-full bg-rose-50 px-2 py-0.5 text-xs font-medium text-rose-700">Deceduto</span> : null}
                            </p>
                            <p className="mt-1 text-xs text-gray-500">
                              CF: <span className="font-medium text-gray-700">{owner.codice_fiscale ?? "—"}</span>
                              {" · "}Titolo: <span className="font-medium text-gray-700">{owner.titoli ?? "—"}</span>
                            </p>
                            <p className="mt-1 text-xs text-gray-500">
                              Nascita: <span className="font-medium text-gray-700">{owner.data_nascita ?? "—"}</span>
                              {owner.luogo_nascita ? ` · ${owner.luogo_nascita}` : ""}
                            </p>
                            <p className="mt-1 text-xs text-gray-500">
                              Residenza: <span className="font-medium text-gray-700">{owner.residenza ?? owner.comune_residenza ?? "—"}</span>
                            </p>
                            {owner.person ? (
                              <div className="mt-2 rounded-md border border-emerald-100 bg-emerald-50 px-2 py-1.5">
                                <p className="text-xs font-medium text-emerald-800">Anagrafica GAIA corrente</p>
                                <p className="mt-1 text-xs text-emerald-700">
                                  {owner.person.cognome} {owner.person.nome} · {owner.person.codice_fiscale}
                                </p>
                                <p className="mt-1 text-xs text-emerald-700">
                                  Residenza corrente: {owner.person.indirizzo ?? owner.person.comune_residenza ?? "—"}
                                </p>
                                <p className="mt-1 text-xs text-emerald-700">
                                  Storico anagrafica: {owner.person_snapshots.length} snapshot
                                </p>
                              </div>
                            ) : null}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="mt-4">
                    <DataTable
                      data={unit.occupancies}
                      columns={consorzioOccupancyColumns}
                      initialPageSize={6}
                      emptyTitle="Nessuna occupancy"
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </article>

        <article className="panel-card">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-gray-900">Utilizzatore / pagatore annualità</p>
              <p className="mt-1 text-sm text-gray-500">Righe `cat_utenze_irrigue` per anno campagna: soggetto operativo che usa l’acqua o paga il ruolo.</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Anno campagna</p>
              <select className="form-control mt-1 w-[160px]" value={String(anno)} onChange={(e) => setAnno(Number(e.target.value))}>
                {[new Date().getFullYear() + 1, new Date().getFullYear(), new Date().getFullYear() - 1, new Date().getFullYear() - 2].map((y) => (
                  <option key={y} value={String(y)}>
                    {y}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="mt-4">
            <DataTable data={utenze} columns={utenzeColumns} initialPageSize={8} emptyTitle={isLoading ? "Caricamento…" : "Nessuna utenza"} />
          </div>
        </article>

        <article className="panel-card">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-gray-900">Anomalie</p>
              <p className="mt-1 text-sm text-gray-500">Anomalie collegate alle utenze della particella (per anno).</p>
            </div>
            <p className="text-sm text-gray-500">{isLoading ? "Caricamento…" : `${anomalie.length} righe`}</p>
          </div>
          <div className="mt-4">
            <DataTable data={anomalie} columns={anomalieColumns} initialPageSize={8} emptyTitle={isLoading ? "Caricamento…" : "Nessuna anomalia"} />
          </div>
        </article>

        <article className="panel-card">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-gray-900">Storico</p>
              <p className="mt-1 text-sm text-gray-500">Versioni precedenti della particella (SCD Type 2).</p>
            </div>
            <p className="text-sm text-gray-500">{isLoading ? "Caricamento…" : `${history.length} righe`}</p>
          </div>
          <div className="mt-4">
            <DataTable data={history} columns={columns} initialPageSize={10} />
          </div>
        </article>
      </div>
    </CatastoPage>
  );
}
