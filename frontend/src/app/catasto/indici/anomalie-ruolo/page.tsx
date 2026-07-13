"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";

import { CatastoPage } from "@/components/catasto/catasto-page";
import {
  catastoAssignIndiciRuoloEsclusoDistretto,
  catastoGetIndiciRuoloEsclusi,
  catastoListDistretti,
} from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatDistretto, CatIndiceRuoloExcludedParticella } from "@/types/catasto";

const REASON_OPTIONS = [
  { key: "all", label: "Tutte" },
  { key: "senza_distretto", label: "Particelle correnti senza distretto" },
  { key: "swapped_arborea_terralba", label: "Swap Arborea/Terralba" },
  { key: "non_collegata", label: "Ruolo non collegato" },
  { key: "catasto_non_corrente_o_assente", label: "Aggancio non corrente" },
] as const;

function formatInteger(value: number): string {
  return new Intl.NumberFormat("it-IT").format(value);
}

function formatEuro(value: string): string {
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(Number(value));
}

function formatHa(value: string): string {
  return new Intl.NumberFormat("it-IT", { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(Number(value));
}

function workflowDescription(reasonKey: string): { title: string; description: string; tone: string } {
  if (reasonKey === "senza_distretto") {
    return {
      title: "Correzione diretta disponibile",
      description: "La particella esiste in cat_particelle, è corrente, ma non ha num_distretto. L'operatore può verificare il distretto e assegnarlo.",
      tone: "border-emerald-200 bg-emerald-50 text-emerald-800",
    };
  }
  if (reasonKey === "non_collegata") {
    return {
      title: "Serve aggancio catastale",
      description: "La riga ruolo non ha cat_particella_id: va cercata nel catasto corrente o verificata con visura/storico prima di poterla attribuire agli indici.",
      tone: "border-amber-200 bg-amber-50 text-amber-800",
    };
  }
  if (reasonKey === "swapped_arborea_terralba") {
    return {
      title: "Caso storico Arborea/Terralba",
      description:
        "La particella è stata agganciata usando la regola storica di scambio Arborea/Terralba. Se manca il distretto, serve verifica catastale/storica prima di una correzione sugli indici.",
      tone: "border-orange-200 bg-orange-50 text-orange-800",
    };
  }
  return {
    title: "Serve verifica storico/catasto",
    description: "Il collegamento punta a una particella non corrente o non disponibile: prima di correggere serve capire se esiste una particella originata/variata corrente.",
    tone: "border-sky-200 bg-sky-50 text-sky-800",
  };
}

export default function CatastoIndiciAnomalieRuoloPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-slate-500">Caricamento anomalie ruolo...</div>}>
      <CatastoIndiciAnomalieRuoloContent />
    </Suspense>
  );
}

function CatastoIndiciAnomalieRuoloContent() {
  const searchParams = useSearchParams();
  const requestedAnno = Number(searchParams.get("anno") ?? "");
  const anno = Number.isFinite(requestedAnno) && requestedAnno > 0 ? requestedAnno : undefined;
  const [rows, setRows] = useState<CatIndiceRuoloExcludedParticella[]>([]);
  const [distretti, setDistretti] = useState<CatDistretto[]>([]);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [reasonFilter, setReasonFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [distrettoId, setDistrettoId] = useState("");
  const [note, setNote] = useState("Correzione distretto da gestione anomalie ruolo escluse");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadData(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile: effettua nuovamente l'accesso.");
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const [excludedPayload, distrettiPayload] = await Promise.all([
        catastoGetIndiciRuoloEsclusi(token, anno),
        catastoListDistretti(token),
      ]);
      setRows(excludedPayload.items);
      setDistretti(distrettiPayload.filter((item) => item.attivo));
      setSelectedKey((current) => current ?? excludedPayload.items[0]?.key ?? null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento anomalie ruolo.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, [anno]);

  const filteredRows = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return rows.filter((row) => {
      if (reasonFilter !== "all" && row.reason_key !== reasonFilter) {
        return false;
      }
      if (!normalizedQuery) {
        return true;
      }
      return [
        row.comune_nome,
        row.foglio,
        row.particella,
        row.subalterno,
        row.reason_label,
        ...row.avvisi,
        ...row.nominativi,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(normalizedQuery);
    });
  }, [query, reasonFilter, rows]);

  const selected = rows.find((row) => row.key === selectedKey) ?? filteredRows[0] ?? null;
  const selectedWorkflow = selected ? workflowDescription(selected.reason_key) : null;
  const fixableSelected = selected?.reason_key === "senza_distretto" && selected.cat_particella_id != null;

  async function assignDistretto(): Promise<void> {
    if (!selected?.cat_particella_id || !distrettoId) {
      setError("Seleziona una particella correggibile e un distretto.");
      return;
    }
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile: effettua nuovamente l'accesso.");
      return;
    }
    setIsSaving(true);
    setError(null);
    setMessage(null);
    try {
      const response = await catastoAssignIndiciRuoloEsclusoDistretto(token, {
        cat_particella_id: selected.cat_particella_id,
        distretto_id: distrettoId,
        note,
      });
      setMessage(
        response.updated
          ? `Distretto assegnato: ${response.num_distretto} · ${response.nome_distretto ?? "Distretto"}`
          : "La particella era già allineata al distretto selezionato.",
      );
      setDistrettoId("");
      await loadData();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Errore salvataggio distretto.");
    } finally {
      setIsSaving(false);
    }
  }

  const counts = rows.reduce<Record<string, number>>((acc, row) => {
    acc[row.reason_key] = (acc[row.reason_key] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <CatastoPage
      title="Anomalie ruolo escluse dagli indici"
      description="Gestione operativa delle particelle ruolo non attribuite ad Alta/Bassa/Canaletta."
    >
      <div className="space-y-5">
        <div className="rounded-[2rem] border border-[#d7e4da] bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5f7d68]">Workflow anomalie ruolo</p>
              <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">Particelle fuori quadro indici</h1>
              <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600">
                La pagina parte dagli stessi dati della riconciliazione in `/catasto/indici`. Le correzioni dirette aggiornano `cat_particelle`,
                non il ruolo: il ruolo resta sorgente contabile, mentre il catasto corrente riceve il distretto operativo verificato.
              </p>
            </div>
            <Link className="rounded-full border border-[#d7e4da] bg-[#f7fbf8] px-4 py-2 text-sm font-semibold text-[#1d4e35]" href="/catasto/indici">
              Torna agli indici
            </Link>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-5">
            <div className="rounded-3xl border border-[#d7e4da] bg-[#f7fbf8] p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#5f7d68]">Totale anomalie</p>
              <p className="mt-2 text-2xl font-semibold text-slate-950">{formatInteger(rows.length)}</p>
            </div>
            {REASON_OPTIONS.filter((item) => item.key !== "all").map((item) => (
              <div key={item.key} className="rounded-3xl border border-[#d7e4da] bg-white p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#5f7d68]">{item.label}</p>
                <p className="mt-2 text-2xl font-semibold text-slate-950">{formatInteger(counts[item.key] ?? 0)}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.25fr)_minmax(420px,0.75fr)]">
          <section className="rounded-[2rem] border border-[#d7e4da] bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-950">Casi da lavorare</h2>
                <p className="text-sm text-slate-500">{formatInteger(filteredRows.length)} casi filtrati</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <input
                  className="rounded-full border border-[#d7e4da] px-4 py-2 text-sm"
                  placeholder="Cerca comune, avviso, soggetto..."
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
                <select className="rounded-full border border-[#d7e4da] px-4 py-2 text-sm" value={reasonFilter} onChange={(event) => setReasonFilter(event.target.value)}>
                  {REASON_OPTIONS.map((item) => (
                    <option key={item.key} value={item.key}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {isLoading ? (
              <p className="mt-5 rounded-3xl border border-dashed border-[#d7e4da] bg-[#f7fbf8] px-5 py-10 text-center text-sm text-slate-500">
                Caricamento anomalie ruolo...
              </p>
            ) : (
              <div className="mt-5 max-h-[640px] overflow-auto rounded-3xl border border-[#d7e4da]">
                <table className="w-full min-w-[980px] text-sm">
                  <thead className="sticky top-0 bg-[#f7fbf8] text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-[#5f7d68]">
                    <tr>
                      <th className="px-3 py-3">Motivo</th>
                      <th className="px-3 py-3">Chiave</th>
                      <th className="px-3 py-3 text-right">Ha</th>
                      <th className="px-3 py-3 text-right">Importo</th>
                      <th className="px-3 py-3">Avviso</th>
                      <th className="px-3 py-3">Soggetto</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRows.map((row) => {
                      const isSelected = selected?.key === row.key;
                      return (
                        <tr
                          key={row.key}
                          className={`cursor-pointer border-t border-[#eef4ef] ${isSelected ? "bg-[#eef6f0]" : "bg-white hover:bg-[#fbfdfb]"}`}
                          onClick={() => {
                            setSelectedKey(row.key);
                            setMessage(null);
                            setError(null);
                          }}
                        >
                          <td className="px-3 py-2.5">
                            <span className="rounded-full bg-[#fff8e9] px-2.5 py-1 text-[11px] font-semibold text-[#8a4f00]">{row.reason_label}</span>
                          </td>
                          <td className="px-3 py-2.5 font-mono text-xs text-slate-700">
                            {row.comune_nome ?? "—"} · F{row.foglio} · P{row.particella} · S{row.subalterno || "—"}
                          </td>
                          <td className="px-3 py-2.5 text-right tabular-nums">{formatHa(row.superficie_irrigata_ha)}</td>
                          <td className="px-3 py-2.5 text-right font-semibold tabular-nums text-[#1d4e35]">{formatEuro(row.importo_ruolo)}</td>
                          <td className="px-3 py-2.5 text-xs text-slate-600">{row.avvisi[0] ?? "—"}</td>
                          <td className="max-w-[280px] truncate px-3 py-2.5 text-xs text-slate-600">{row.nominativi[0] ?? "—"}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <aside className="rounded-[2rem] border border-[#d7e4da] bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-950">Dettaglio e azioni</h2>
            {error ? <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
            {selected && selectedWorkflow ? (
              <div className="mt-4 space-y-4">
                <div className={`rounded-3xl border p-4 ${selectedWorkflow.tone}`}>
                  <p className="text-sm font-semibold">{selectedWorkflow.title}</p>
                  <p className="mt-2 text-sm leading-6">{selectedWorkflow.description}</p>
                </div>

                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <div className="rounded-2xl bg-[#f7fbf8] p-3">
                    <dt className="text-xs text-slate-500">Comune</dt>
                    <dd className="font-semibold text-slate-900">{selected.comune_nome ?? "—"}</dd>
                  </div>
                  <div className="rounded-2xl bg-[#f7fbf8] p-3">
                    <dt className="text-xs text-slate-500">Foglio / particella / sub</dt>
                    <dd className="font-mono font-semibold text-slate-900">{selected.foglio} / {selected.particella} / {selected.subalterno || "—"}</dd>
                  </div>
                  <div className="rounded-2xl bg-[#f7fbf8] p-3">
                    <dt className="text-xs text-slate-500">ID cat_particella</dt>
                    <dd className="break-all font-mono text-xs text-slate-900">{selected.cat_particella_id ?? "Assente"}</dd>
                  </div>
                  <div className="rounded-2xl bg-[#f7fbf8] p-3">
                    <dt className="text-xs text-slate-500">Distretto catasto</dt>
                    <dd className="font-semibold text-slate-900">{selected.catasto_num_distretto ?? "Mancante"}</dd>
                  </div>
                </dl>

                {fixableSelected ? (
                  <div className="rounded-3xl border border-[#d7e4da] bg-[#fbfdfb] p-4">
                    <p className="text-sm font-semibold text-slate-900">Assegna distretto verificato</p>
                    <label className="mt-3 block text-xs font-semibold uppercase tracking-[0.14em] text-[#5f7d68]">
                      Distretto
                      <select className="mt-1 w-full rounded-2xl border border-[#d7e4da] px-3 py-2 text-sm normal-case tracking-normal" value={distrettoId} onChange={(event) => setDistrettoId(event.target.value)}>
                        <option value="">Seleziona distretto...</option>
                        {distretti.map((distretto) => (
                          <option key={distretto.id} value={distretto.id}>
                            {distretto.num_distretto} · {distretto.nome_distretto ?? "Distretto"}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="mt-3 block text-xs font-semibold uppercase tracking-[0.14em] text-[#5f7d68]">
                      Nota operatore
                      <textarea className="mt-1 min-h-20 w-full rounded-2xl border border-[#d7e4da] px-3 py-2 text-sm normal-case tracking-normal" value={note} onChange={(event) => setNote(event.target.value)} />
                    </label>
                    <button
                      type="button"
                      className="mt-3 rounded-full bg-[#1d4e35] px-4 py-2 text-sm font-semibold text-white shadow-sm disabled:cursor-not-allowed disabled:opacity-50"
                      disabled={isSaving}
                      onClick={() => void assignDistretto()}
                    >
                      {isSaving ? "Salvataggio..." : "Salva distretto"}
                    </button>
                  </div>
                ) : (
                  <div className="rounded-3xl border border-dashed border-[#d7e4da] bg-[#f7fbf8] p-4 text-sm leading-6 text-slate-600">
                    Questa anomalia non è correggibile con assegnazione diretta del distretto. Usa la chiave catastale e l&apos;avviso per verificare
                    storico AdE, eventuale particella originata o necessità di nuovo aggancio.
                  </div>
                )}

                {message ? <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{message}</div> : null}
              </div>
            ) : (
              <p className="mt-4 rounded-3xl border border-dashed border-[#d7e4da] bg-[#f7fbf8] px-5 py-10 text-center text-sm text-slate-500">
                Seleziona un caso dall&apos;elenco.
              </p>
            )}
          </aside>
        </div>
      </div>
    </CatastoPage>
  );
}
