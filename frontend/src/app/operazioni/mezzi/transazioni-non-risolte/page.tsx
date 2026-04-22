"use client";

import { useCallback, useEffect, useState } from "react";

import {
  OperazioniBreadcrumb,
  OperazioniCollectionPanel,
} from "@/components/operazioni/collection-layout";
import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import {
  type PersistedUnresolvedRow,
  type UnresolvedAnomalies,
  getUnresolvedTransactions,
  getUnresolvedAnomalies,
  skipUnresolvedTransaction,
} from "@/features/operazioni/api/client";
import { cn } from "@/lib/cn";

// ─── Resolve modal (inline) ────────────────────────────────────────────────

function ResolveModal({
  row,
  onClose,
  onResolved,
}: {
  row: PersistedUnresolvedRow;
  onClose: () => void;
  onResolved: () => void;
}) {
  const [vehicleSearch, setVehicleSearch] = useState("");
  const [vehicleResults, setVehicleResults] = useState<{ id: string; name: string; code: string; plate_number: string | null }[]>([]);
  const [selectedVehicle, setSelectedVehicle] = useState<{ id: string; name: string } | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = useCallback(async (q: string) => {
    if (q.length < 2) { setVehicleResults([]); return; }
    try {
      const res = await fetch(`/api/operazioni/vehicles?search=${encodeURIComponent(q)}&page_size=10`);
      const data = await res.json();
      setVehicleResults(data.items ?? []);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => void search(vehicleSearch), 300);
    return () => clearTimeout(t);
  }, [vehicleSearch, search]);

  async function handleResolve() {
    if (!selectedVehicle || !row.fueled_at_iso || !row.liters) return;
    setSaving(true);
    setError(null);
    try {
      const res = await fetch("/api/operazioni/vehicles/fuel-logs/resolve-fleet-transactions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify([{
          vehicle_id: selectedVehicle.id,
          fueled_at_iso: row.fueled_at_iso,
          liters: row.liters,
          total_cost: row.total_cost,
          odometer_km: row.odometer_km,
          card_code: row.card_code,
          station_name: row.station_name,
          notes_extra: row.notes_extra,
          unresolved_id: row.id,
        }]),
      });
      if (!res.ok) throw new Error(await res.text());
      onResolved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div className="w-full max-w-lg rounded-[20px] bg-white shadow-xl">
        <div className="border-b border-[#e8ede7] px-6 py-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-500">Risolvi transazione</p>
          <p className="mt-0.5 text-sm font-medium text-gray-900">
            {row.targa} · {row.fueled_at_iso?.slice(0, 10)} · {row.liters} L
          </p>
        </div>
        <div className="space-y-4 px-6 py-5">
          <div className="rounded-[12px] bg-amber-50 px-3 py-2.5 text-xs text-amber-700">
            {row.reason_detail}
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.15em] text-gray-500">
              Cerca mezzo
            </label>
            <input
              className="mt-1.5 w-full rounded-[10px] border border-[#d8dfd8] px-3 py-2 text-sm focus:border-[#4a7c59] focus:outline-none"
              placeholder="Targa, codice o nome..."
              value={vehicleSearch}
              onChange={(e) => setVehicleSearch(e.target.value)}
            />
            {vehicleResults.length > 0 && (
              <ul className="mt-1 rounded-[10px] border border-[#e4e8e2] bg-white shadow-sm">
                {vehicleResults.map((v) => (
                  <li key={v.id}>
                    <button
                      onClick={() => { setSelectedVehicle({ id: v.id, name: v.name }); setVehicleResults([]); setVehicleSearch(v.name); }}
                      className="w-full px-3 py-2 text-left text-sm hover:bg-[#f4f7f3]"
                    >
                      <span className="font-medium">{v.name}</span>
                      <span className="ml-2 text-gray-400">{v.plate_number ?? v.code}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {selectedVehicle && (
              <p className="mt-1.5 text-xs text-emerald-700">
                Selezionato: <strong>{selectedVehicle.name}</strong>
              </p>
            )}
          </div>

          {error && <p className="text-xs text-red-600">{error}</p>}
        </div>
        <div className="flex justify-end gap-2 border-t border-[#e8ede7] px-6 py-4">
          <button onClick={onClose} className="btn-secondary text-sm">Annulla</button>
          <button
            onClick={handleResolve}
            disabled={!selectedVehicle || saving}
            className="btn-primary text-sm disabled:opacity-40"
          >
            {saving ? "Salvataggio..." : "Registra"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Anomalie panel ────────────────────────────────────────────────────────

function fmtL(n: number) { return `${n.toLocaleString("it-IT", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} L`; }
function fmtEur(n: number) { return `€ ${n.toLocaleString("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`; }

function AnomaliePanel() {
  const [data, setData] = useState<UnresolvedAnomalies | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>("high_volume");

  useEffect(() => {
    getUnresolvedAnomalies({ liters_threshold: 150, same_day_min: 3 })
      .then(setData).catch(() => null).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="h-24 animate-pulse rounded-2xl border border-[#e4e8e2] bg-white" />;
  if (!data) return null;

  const hasAny = data.high_volume.length > 0 || data.same_day_multiple.length > 0 || data.no_operator_cards.length > 0;
  if (!hasAny) return null;

  type Section = { id: string; label: string; count: number; severity: "high" | "medium" | "low"; content: React.ReactNode };

  const sections: Section[] = [
    {
      id: "high_volume",
      label: "Volumi anomali",
      count: data.high_volume.length,
      severity: "high",
      content: (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[#e6ebe5] bg-[#f9faf8]">
                {["Tessera", "Targa", "Operatore", "Data", "Litri", "Costo", "Stazione"].map(h => (
                  <th key={h} className="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-[0.15em] text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f0f3ef]">
              {data.high_volume.map(r => (
                <tr key={r.id} className="bg-white hover:bg-rose-50">
                  <td className="px-3 py-2 font-mono text-gray-700">{r.card_code ?? "—"}</td>
                  <td className="px-3 py-2 font-mono text-gray-500">{r.targa ?? "—"}</td>
                  <td className="px-3 py-2 text-gray-700">{r.operator_name ?? <span className="italic text-gray-400">N/D</span>}</td>
                  <td className="px-3 py-2 text-gray-500 whitespace-nowrap">{r.fueled_at_iso?.slice(0, 16) ?? "—"}</td>
                  <td className="px-3 py-2 font-mono font-semibold text-rose-700">{fmtL(r.liters)}</td>
                  <td className="px-3 py-2 font-mono text-gray-700">{fmtEur(r.total_cost)}</td>
                  <td className="px-3 py-2 max-w-[180px] truncate text-gray-400">{r.station_name ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ),
    },
    {
      id: "same_day",
      label: "Stessa tessera, stesso giorno",
      count: data.same_day_multiple.length,
      severity: "medium",
      content: (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[#e6ebe5] bg-[#f9faf8]">
                {["Tessera", "Operatore", "Giorno", "N rifornimenti", "Litri totali"].map(h => (
                  <th key={h} className="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-[0.15em] text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f0f3ef]">
              {data.same_day_multiple.map((r, i) => (
                <tr key={i} className="bg-white hover:bg-amber-50">
                  <td className="px-3 py-2 font-mono text-gray-700">{r.card_code ?? "—"}</td>
                  <td className="px-3 py-2 text-gray-700">{r.operator_name ?? <span className="italic text-gray-400">N/D</span>}</td>
                  <td className="px-3 py-2 text-gray-500 whitespace-nowrap">{r.day}</td>
                  <td className="px-3 py-2 text-center font-semibold text-amber-700">{r.count}</td>
                  <td className="px-3 py-2 font-mono font-semibold text-gray-900">{fmtL(r.tot_liters)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ),
    },
    {
      id: "no_operator",
      label: "Tessere senza operatore",
      count: data.no_operator_cards.length,
      severity: "low",
      content: (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[#e6ebe5] bg-[#f9faf8]">
                {["Tessera", "N transazioni", "Litri totali"].map(h => (
                  <th key={h} className="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-[0.15em] text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f0f3ef]">
              {data.no_operator_cards.map((r, i) => (
                <tr key={i} className="bg-white hover:bg-sky-50">
                  <td className="px-3 py-2 font-mono text-gray-700">{r.card_code ?? "—"}</td>
                  <td className="px-3 py-2 text-gray-700">{r.count}</td>
                  <td className="px-3 py-2 font-mono text-gray-700">{fmtL(r.tot_liters)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ),
    },
  ];

  const sevBg: Record<string, string> = { high: "bg-rose-50 border-rose-200", medium: "bg-amber-50 border-amber-200", low: "bg-sky-50 border-sky-200" };
  const sevText: Record<string, string> = { high: "text-rose-700", medium: "text-amber-700", low: "text-sky-700" };
  const sevBadge: Record<string, string> = { high: "bg-rose-100 text-rose-700", medium: "bg-amber-100 text-amber-700", low: "bg-sky-100 text-sky-700" };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-400">Anomalie rilevate</span>
        <span className="rounded-full bg-rose-100 px-2 py-0.5 text-[10px] font-semibold text-rose-700">
          {data.high_volume.length + data.same_day_multiple.length + data.no_operator_cards.length}
        </span>
      </div>

      {sections.filter(s => s.count > 0).map(s => (
        <div key={s.id} className={cn("rounded-2xl border", sevBg[s.severity])}>
          <button
            onClick={() => setExpanded(expanded === s.id ? null : s.id)}
            className="flex w-full items-center justify-between px-4 py-3"
          >
            <div className="flex items-center gap-2">
              <span className={cn("text-sm font-semibold", sevText[s.severity])}>{s.label}</span>
              <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-semibold", sevBadge[s.severity])}>{s.count}</span>
            </div>
            <svg className={cn("h-4 w-4 transition-transform", sevText[s.severity], expanded === s.id && "rotate-180")} viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
          {expanded === s.id && (
            <div className="border-t border-current border-opacity-10 px-1 pb-2">
              {s.content}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ─── Status badge ──────────────────────────────────────────────────────────

const statusTone: Record<string, string> = {
  pending: "bg-amber-50 text-amber-700",
  resolved: "bg-emerald-50 text-emerald-700",
  skipped: "bg-gray-100 text-gray-500",
};
const statusLabel: Record<string, string> = {
  pending: "In attesa",
  resolved: "Risolto",
  skipped: "Ignorato",
};

function fmtDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("it-IT", { day: "2-digit", month: "2-digit", year: "numeric" });
}

// ─── Main content ──────────────────────────────────────────────────────────

function TransazioniNonRisolteContent() {
  const [statusFilter, setStatusFilter] = useState<"pending" | "all">("pending");
  const [items, setItems] = useState<PersistedUnresolvedRow[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [resolveTarget, setResolveTarget] = useState<PersistedUnresolvedRow | null>(null);
  const [skipping, setSkipping] = useState<string | null>(null);

  const load = useCallback(async (p: number, sf: string) => {
    setLoading(true);
    try {
      const data = await getUnresolvedTransactions({ status_filter: sf, page: p, page_size: 50 });
      setItems(data.items);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(page, statusFilter); }, [load, page, statusFilter]);

  async function handleSkip(id: string) {
    setSkipping(id);
    try {
      await skipUnresolvedTransaction(id);
      void load(page, statusFilter);
    } catch { /* ignore */ } finally {
      setSkipping(null);
    }
  }

  return (
    <div className="page-stack">
      <OperazioniBreadcrumb
        items={[
          { label: "Operazioni", href: "/operazioni" },
          { label: "Mezzi", href: "/operazioni/mezzi" },
          { label: "Transazioni non risolte" },
        ]}
      />

      <AnomaliePanel />

      <OperazioniCollectionPanel
        title="Transazioni non risolte"
        description="Righe importate per cui non è stato possibile identificare automaticamente il mezzo. Assegna manualmente il mezzo o ignora la riga."
        count={total}
      >
        {/* Filter tabs */}
        <div className="mb-4 flex gap-2">
          {(["pending", "all"] as const).map((f) => (
            <button
              key={f}
              onClick={() => { setStatusFilter(f); setPage(1); }}
              className={cn(
                "rounded-full px-3 py-1 text-xs font-semibold",
                statusFilter === f
                  ? "bg-[#4a7c59] text-white"
                  : "border border-[#d8dfd8] text-gray-600 hover:bg-gray-50",
              )}
            >
              {f === "pending" ? "In attesa" : "Tutti"}
            </button>
          ))}
        </div>

        {loading ? (
          <p className="text-sm text-gray-500">Caricamento...</p>
        ) : items.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-[#d8dfd8] bg-[#f8faf8] p-6 text-sm text-gray-500">
            {statusFilter === "pending" ? "Nessuna transazione in attesa." : "Nessuna transazione trovata."}
          </div>
        ) : (
          <div className="space-y-3">
            <div className="overflow-x-auto rounded-[16px] border border-[#e6ebe5]">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[#e6ebe5] bg-[#f9faf8]">
                    {["Stato", "Data import", "Targa", "Data", "Litri", "Motivo", ""].map((h) => (
                      <th key={h} className="px-3 py-2.5 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#f0f3ef]">
                  {items.map((row) => (
                    <tr key={row.id} className="bg-white hover:bg-[#f9faf8]">
                      <td className="px-3 py-2.5">
                        <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-semibold", statusTone[row.status] ?? "bg-gray-100 text-gray-600")}>
                          {statusLabel[row.status] ?? row.status}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-gray-500 whitespace-nowrap">{fmtDate(row.created_at)}</td>
                      <td className="px-3 py-2.5 font-mono text-xs text-gray-700">{row.targa ?? "—"}</td>
                      <td className="px-3 py-2.5 text-gray-500 whitespace-nowrap">{fmtDate(row.fueled_at_iso)}</td>
                      <td className="px-3 py-2.5 font-mono text-gray-900">{row.liters ? `${row.liters} L` : "—"}</td>
                      <td className="px-3 py-2.5 max-w-[240px]">
                        <p className="truncate text-xs text-gray-500">{row.reason_detail}</p>
                      </td>
                      <td className="px-3 py-2.5">
                        {row.status === "pending" && (
                          <div className="flex gap-2">
                            <button
                              onClick={() => setResolveTarget(row)}
                              className="rounded-full bg-[#4a7c59] px-2.5 py-1 text-[10px] font-semibold text-white hover:bg-[#3d6b4a]"
                            >
                              Risolvi
                            </button>
                            <button
                              onClick={() => void handleSkip(row.id)}
                              disabled={skipping === row.id}
                              className="rounded-full border border-[#d8dfd8] px-2.5 py-1 text-[10px] font-semibold text-gray-500 hover:bg-gray-50 disabled:opacity-40"
                            >
                              Ignora
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-between gap-3 text-xs text-gray-500">
                <span>Pagina {page} di {totalPages} · {total} righe totali</span>
                <div className="flex gap-2">
                  <button
                    disabled={page <= 1}
                    onClick={() => setPage((p) => p - 1)}
                    className="rounded-full border border-[#e4e8e2] px-3 py-1 disabled:opacity-40 hover:bg-gray-50"
                  >← Prec</button>
                  <button
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => p + 1)}
                    className="rounded-full border border-[#e4e8e2] px-3 py-1 disabled:opacity-40 hover:bg-gray-50"
                  >Succ →</button>
                </div>
              </div>
            )}
          </div>
        )}
      </OperazioniCollectionPanel>

      {resolveTarget && (
        <ResolveModal
          row={resolveTarget}
          onClose={() => setResolveTarget(null)}
          onResolved={() => { setResolveTarget(null); void load(page, statusFilter); }}
        />
      )}
    </div>
  );
}

export default function TransazioniNonRisoltePage() {
  return (
    <OperazioniModulePage
      title="Transazioni non risolte"
      description="Revisione e assegnazione manuale delle righe di importazione non abbinate."
      breadcrumb="Transazioni non risolte"
    >
      {() => <TransazioniNonRisolteContent />}
    </OperazioniModulePage>
  );
}
