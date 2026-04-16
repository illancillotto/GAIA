"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

import { RuoloModulePage } from "@/components/ruolo/module-page";
import { getStoredAccessToken } from "@/lib/auth";
import { buildExportCsvUrl, listAvvisi } from "@/lib/ruolo-api";
import type { RuoloAvvisoListItemResponse } from "@/types/ruolo";

function formatEuro(value: number | null): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(value);
}

const PAGE_SIZE = 25;

export default function RuoloAvvisiPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [token, setToken] = useState<string | null>(null);
  const [avvisi, setAvvisi] = useState<RuoloAvvisoListItemResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters from URL
  const anno = searchParams.get("anno") ? Number(searchParams.get("anno")) : undefined;
  const codice_fiscale = searchParams.get("cf") ?? undefined;
  const comune = searchParams.get("comune") ?? undefined;
  const codice_utenza = searchParams.get("utenza") ?? undefined;
  const unlinked = searchParams.get("unlinked") === "true";
  const page = Math.max(1, Number(searchParams.get("page") ?? 1));

  // Local filter state (controlled inputs)
  const [filterAnno, setFilterAnno] = useState(anno?.toString() ?? "");
  const [filterCf, setFilterCf] = useState(codice_fiscale ?? "");
  const [filterComune, setFilterComune] = useState(comune ?? "");
  const [filterUtenza, setFilterUtenza] = useState(codice_utenza ?? "");
  const [filterUnlinked, setFilterUnlinked] = useState(unlinked);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    setError(null);
    listAvvisi(token, {
      anno,
      codice_fiscale,
      comune,
      codice_utenza,
      unlinked,
      page,
      page_size: PAGE_SIZE,
    })
      .then((r) => {
        setAvvisi(r.items);
        setTotal(r.total);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Errore"))
      .finally(() => setLoading(false));
  }, [token, anno, codice_fiscale, comune, codice_utenza, unlinked, page]);

  function applyFilters(e: React.FormEvent) {
    e.preventDefault();
    const qs = new URLSearchParams();
    if (filterAnno) qs.set("anno", filterAnno);
    if (filterCf) qs.set("cf", filterCf);
    if (filterComune) qs.set("comune", filterComune);
    if (filterUtenza) qs.set("utenza", filterUtenza);
    if (filterUnlinked) qs.set("unlinked", "true");
    qs.set("page", "1");
    router.push(`/ruolo/avvisi?${qs}`);
  }

  function setPage(p: number) {
    const qs = new URLSearchParams(searchParams.toString());
    qs.set("page", String(p));
    router.push(`/ruolo/avvisi?${qs}`);
  }

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const exportUrl = buildExportCsvUrl({ anno, codice_fiscale, comune, codice_utenza, unlinked });

  return (
    <RuoloModulePage
      title="Avvisi Ruolo"
      description="Elenco degli avvisi consortili importati dal Ruolo."
      breadcrumb="Avvisi"
      requiredSection="ruolo.avvisi"
      topbarActions={
        token ? (
          <a
            href={`${exportUrl}&token=${token}`}
            className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 transition hover:bg-gray-50"
            download="avvisi_ruolo.csv"
          >
            Esporta CSV
          </a>
        ) : undefined
      }
    >
      <div className="space-y-6">
        {/* Filters */}
        <form onSubmit={applyFilters} className="flex flex-wrap gap-3 rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
          <input
            type="number"
            placeholder="Anno"
            value={filterAnno}
            onChange={(e) => setFilterAnno(e.target.value)}
            className="w-24 rounded-lg border border-gray-200 px-3 py-1.5 text-sm focus:border-[#1D4E35] focus:outline-none"
          />
          <input
            type="text"
            placeholder="CF / PIVA"
            value={filterCf}
            onChange={(e) => setFilterCf(e.target.value)}
            className="w-40 rounded-lg border border-gray-200 px-3 py-1.5 text-sm focus:border-[#1D4E35] focus:outline-none"
          />
          <input
            type="text"
            placeholder="Comune"
            value={filterComune}
            onChange={(e) => setFilterComune(e.target.value)}
            className="w-36 rounded-lg border border-gray-200 px-3 py-1.5 text-sm focus:border-[#1D4E35] focus:outline-none"
          />
          <input
            type="text"
            placeholder="Cod. utenza"
            value={filterUtenza}
            onChange={(e) => setFilterUtenza(e.target.value)}
            className="w-36 rounded-lg border border-gray-200 px-3 py-1.5 text-sm focus:border-[#1D4E35] focus:outline-none"
          />
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={filterUnlinked}
              onChange={(e) => setFilterUnlinked(e.target.checked)}
              className="rounded border-gray-300"
            />
            Solo non collegati
          </label>
          <button
            type="submit"
            className="rounded-lg bg-[#1D4E35] px-4 py-1.5 text-sm font-medium text-white hover:bg-[#163d29]"
          >
            Filtra
          </button>
        </form>

        {/* Table */}
        <div>
          <div className="mb-2 flex items-center justify-between">
            <p className="text-sm text-gray-500">
              {loading ? "Caricamento..." : `${total} avvisi trovati`}
            </p>
          </div>

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {!loading && !error && (
            <div className="overflow-hidden rounded-xl border border-gray-100 bg-white shadow-sm">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-left text-xs font-medium uppercase tracking-wider text-gray-400">
                    <th className="px-4 py-3">Anno</th>
                    <th className="px-4 py-3">CF / PIVA</th>
                    <th className="px-4 py-3">Nominativo</th>
                    <th className="px-4 py-3">Cod. CNC</th>
                    <th className="px-4 py-3">Cod. Utenza</th>
                    <th className="px-4 py-3 text-right">Totale €</th>
                    <th className="px-4 py-3">Soggetto</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {avvisi.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-4 py-8 text-center text-sm text-gray-400">
                        Nessun avviso trovato.
                      </td>
                    </tr>
                  ) : (
                    avvisi.map((a) => (
                      <tr key={a.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium text-gray-800">{a.anno_tributario}</td>
                        <td className="px-4 py-3 font-mono text-xs text-gray-600">{a.codice_fiscale_raw ?? "—"}</td>
                        <td className="max-w-[180px] truncate px-4 py-3 text-gray-700" title={a.nominativo_raw ?? ""}>
                          {a.display_name ?? a.nominativo_raw ?? "—"}
                        </td>
                        <td className="px-4 py-3 font-mono text-xs text-gray-500">{a.codice_cnc}</td>
                        <td className="px-4 py-3 text-gray-500">{a.codice_utenza ?? "—"}</td>
                        <td className="px-4 py-3 text-right font-medium text-gray-800">
                          {formatEuro(a.importo_totale_euro)}
                        </td>
                        <td className="px-4 py-3">
                          {a.is_linked ? (
                            <span className="inline-flex rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                              Collegato
                            </span>
                          ) : (
                            <span className="inline-flex rounded-full bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-600">
                              Orfano
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <Link
                            href={`/ruolo/avvisi/${a.id}`}
                            className="text-xs font-medium text-[#1D4E35] hover:underline"
                          >
                            Dettaglio →
                          </Link>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-center gap-2">
              <button
                type="button"
                onClick={() => setPage(page - 1)}
                disabled={page <= 1}
                className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-600 disabled:opacity-40 hover:bg-gray-50"
              >
                ← Precedente
              </button>
              <span className="text-sm text-gray-500">
                Pagina {page} di {totalPages}
              </span>
              <button
                type="button"
                onClick={() => setPage(page + 1)}
                disabled={page >= totalPages}
                className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-600 disabled:opacity-40 hover:bg-gray-50"
              >
                Successiva →
              </button>
            </div>
          )}
        </div>
      </div>
    </RuoloModulePage>
  );
}
