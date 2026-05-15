"use client";

import { useEffect, useState } from "react";

import { AlertBanner } from "@/components/ui/alert-banner";
import { catastoGetMeterReading, catastoListMeterReadings } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatMeterReading, CatMeterReadingListResponse } from "@/types/catasto";

import { MeterReadingDetailDrawer } from "./meter-reading-detail-drawer";

export function MeterReadingsTable({ subjectId }: { subjectId?: string }) {
  const [data, setData] = useState<CatMeterReadingListResponse | null>(null);
  const [anno, setAnno] = useState(String(new Date().getFullYear()));
  const [puntoConsegna, setPuntoConsegna] = useState("");
  const [codiceFiscale, setCodiceFiscale] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<CatMeterReading | null>(null);

  async function load() {
    const token = getStoredAccessToken();
    if (!token) return;
    try {
      setLoading(true);
      setError(null);
      const result = await catastoListMeterReadings(token, {
        anno: anno ? Number(anno) : undefined,
        puntoConsegna: puntoConsegna || undefined,
        codiceFiscale: codiceFiscale || undefined,
        subjectId: subjectId || undefined,
        pageSize: subjectId ? 200 : 50,
      });
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Caricamento letture fallito");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [anno, puntoConsegna, codiceFiscale, subjectId]);

  async function openDetail(id: string) {
    const token = getStoredAccessToken();
    if (!token) return;
    try {
      setDetail(await catastoGetMeterReading(token, id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Dettaglio lettura non disponibile");
    }
  }

  return (
    <div className="space-y-4">
      {!subjectId ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-4">
            <p className="section-title">Filtri</p>
            <p className="section-copy">Riduci il perimetro per anno, punto consegna o codice fiscale.</p>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <label className="block text-sm font-medium text-slate-700">
              Anno
              <input className="form-control mt-1" value={anno} onChange={(event) => setAnno(event.target.value)} />
            </label>
            <label className="block text-sm font-medium text-slate-700">
              Punto consegna
              <input className="form-control mt-1" value={puntoConsegna} onChange={(event) => setPuntoConsegna(event.target.value)} />
            </label>
            <label className="block text-sm font-medium text-slate-700">
              Codice fiscale
              <input className="form-control mt-1" value={codiceFiscale} onChange={(event) => setCodiceFiscale(event.target.value)} />
            </label>
          </div>
        </div>
      ) : null}

      {error ? (
        <AlertBanner variant="danger" title="Errore caricamento">
          {error}
        </AlertBanner>
      ) : null}

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-5 py-4">
          <p className="section-title">{subjectId ? "Letture collegate al soggetto" : "Registro letture contatori"}</p>
          <p className="section-copy">
            {loading ? "Caricamento..." : `${data?.total ?? 0} letture disponibili`}
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-600">
              <tr>
                <th className="px-4 py-3 font-medium">Anno</th>
                <th className="px-4 py-3 font-medium">Punto consegna</th>
                <th className="px-4 py-3 font-medium">Matricola</th>
                <th className="px-4 py-3 font-medium">Soggetto</th>
                <th className="px-4 py-3 font-medium">Consumo</th>
                <th className="px-4 py-3 font-medium">Stato</th>
              </tr>
            </thead>
            <tbody>
              {(data?.items ?? []).map((item) => (
                <tr
                  key={item.id}
                  className="cursor-pointer border-t border-slate-100 transition hover:bg-slate-50"
                  onClick={() => void openDetail(item.id)}
                >
                  <td className="px-4 py-3">{item.anno}</td>
                  <td className="px-4 py-3 font-medium text-slate-900">{item.punto_consegna}</td>
                  <td className="px-4 py-3">{item.matricola ?? "—"}</td>
                  <td className="px-4 py-3">{item.subject_display_name ?? item.codice_fiscale_normalizzato ?? "Non collegato"}</td>
                  <td className="px-4 py-3">{item.consumo_mc ?? "—"}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                        item.validation_status === "warning"
                          ? "bg-amber-100 text-amber-800"
                          : item.validation_status === "error"
                            ? "bg-rose-100 text-rose-800"
                            : "bg-emerald-100 text-emerald-800"
                      }`}
                    >
                      {item.validation_status}
                    </span>
                  </td>
                </tr>
              ))}
              {!loading && (data?.items.length ?? 0) === 0 ? (
                <tr>
                  <td className="px-4 py-6 text-slate-500" colSpan={6}>
                    Nessuna lettura trovata.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>

      <MeterReadingDetailDrawer reading={detail} onClose={() => setDetail(null)} />
    </div>
  );
}
