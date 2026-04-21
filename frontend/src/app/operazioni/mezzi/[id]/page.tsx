"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";

import {
  OperazioniBreadcrumb,
  OperazioniCollectionPanel,
  OperazioniDetailHero,
  OperazioniHeroNotice,
  OperazioniInfoGrid,
} from "@/components/operazioni/collection-layout";
import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { getVehicle, getVehicleFuelLogs, type VehicleFuelLogItem } from "@/features/operazioni/api/client";
import { cn } from "@/lib/cn";

interface VehicleDetail {
  id: string;
  code: string;
  name: string;
  vehicle_type: string;
  plate_number: string | null;
  brand: string | null;
  model: string | null;
  fuel_type: string | null;
  current_status: string;
  has_gps_device: boolean;
  gps_provider_code: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

const statusLabels: Record<string, string> = {
  available: "Disponibile",
  assigned: "Assegnato",
  in_use: "In utilizzo",
  maintenance: "In manutenzione",
  out_of_service: "Fuori servizio",
};

const statusTone: Record<string, string> = {
  available: "bg-emerald-50 text-emerald-700",
  assigned: "bg-sky-50 text-sky-700",
  in_use: "bg-amber-50 text-amber-700",
  maintenance: "bg-rose-50 text-rose-700",
  out_of_service: "bg-gray-100 text-gray-600",
};

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("it-IT", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function fmtNum(val: string | null, decimals = 2) {
  if (val === null || val === undefined) return "—";
  return Number(val).toLocaleString("it-IT", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function isStorno(log: VehicleFuelLogItem) {
  return Number(log.liters) < 0;
}

// ─── Fuel log panel ────────────────────────────────────────────────────────

function FuelLogsPanel({ vehicleId }: { vehicleId: string }) {
  const [items, setItems] = useState<VehicleFuelLogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (p: number) => {
    setLoading(true);
    try {
      const data = await getVehicleFuelLogs(vehicleId, { page: String(p), page_size: "25" });
      setItems(data.items);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [vehicleId]);

  useEffect(() => { void load(page); }, [load, page]);

  // Summary stats
  const storni = items.filter(isStorno);
  const rifornimenti = items.filter((l) => !isStorno(l));
  const totLiters = items.reduce((s, l) => s + Number(l.liters), 0);
  const totCost = items.reduce((s, l) => s + Number(l.total_cost ?? 0), 0);

  return (
    <OperazioniCollectionPanel
      title="Carburante"
      description="Storico rifornimenti e storni registrati."
      count={total}
    >
      {loading ? (
        <p className="text-sm text-gray-500">Caricamento...</p>
      ) : items.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-[#d8dfd8] bg-[#f8faf8] p-6 text-sm text-gray-500">
          Nessun rifornimento registrato per questo mezzo.
        </div>
      ) : (
        <div className="space-y-4">
          {/* summary strip */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { label: "Litri netti", value: `${fmtNum(String(totLiters))} L` },
              { label: "Costo netto", value: `€ ${fmtNum(String(totCost))}` },
              { label: "Rifornimenti", value: String(rifornimenti.length) },
              { label: "Storni", value: String(storni.length), tone: storni.length > 0 ? "text-amber-700" : "text-gray-900" },
            ].map(({ label, value, tone }) => (
              <div key={label} className="rounded-[16px] border border-[#e4e8e2] bg-white px-3 py-2.5">
                <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500">{label}</p>
                <p className={cn("mt-1.5 text-lg font-semibold", tone ?? "text-gray-900")}>{value}</p>
              </div>
            ))}
          </div>

          {/* log table */}
          <div className="overflow-x-auto rounded-[16px] border border-[#e6ebe5]">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#e6ebe5] bg-[#f9faf8]">
                  {["Data", "Litri", "Costo", "Km", "Stazione", ""].map((h) => (
                    <th key={h} className="px-3 py-2.5 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#f0f3ef]">
                {items.map((log) => {
                  const storno = isStorno(log);
                  return (
                    <tr key={log.id} className={cn("bg-white hover:bg-[#f9faf8]", storno && "bg-amber-50 hover:bg-amber-50")}>
                      <td className="px-3 py-2.5 text-gray-700 whitespace-nowrap">{fmtDate(log.fueled_at)}</td>
                      <td className={cn("px-3 py-2.5 font-mono font-semibold", storno ? "text-amber-700" : "text-gray-900")}>
                        {fmtNum(log.liters)} L
                      </td>
                      <td className={cn("px-3 py-2.5 font-mono", storno ? "text-amber-700" : "text-gray-700")}>
                        {log.total_cost ? `€ ${fmtNum(log.total_cost)}` : "—"}
                      </td>
                      <td className="px-3 py-2.5 text-gray-500">{log.odometer_km ? `${fmtNum(log.odometer_km, 0)} km` : "—"}</td>
                      <td className="px-3 py-2.5 text-gray-500 max-w-[140px] truncate">{log.station_name ?? "—"}</td>
                      <td className="px-3 py-2.5">
                        {storno && (
                          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-700">
                            Storno
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* pagination */}
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
  );
}

// ─── Main content ──────────────────────────────────────────────────────────

function MezzoDetailContent({ vehicleId }: { vehicleId: string }) {
  const [vehicle, setVehicle] = useState<VehicleDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadVehicle = useCallback(async () => {
    try {
      const data = await getVehicle(vehicleId);
      setVehicle(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore caricamento mezzo");
    } finally {
      setLoading(false);
    }
  }, [vehicleId]);

  useEffect(() => { void loadVehicle(); }, [loadVehicle]);

  if (loading) return <p className="text-sm text-gray-500">Caricamento mezzo in corso...</p>;

  if (error || !vehicle) {
    return (
      <article className="panel-card">
        <p className="text-sm font-medium text-red-700">{error || "Mezzo non trovato"}</p>
      </article>
    );
  }

  return (
    <div className="page-stack">
      <OperazioniBreadcrumb
        items={[
          { label: "Operazioni", href: "/operazioni" },
          { label: "Mezzi", href: "/operazioni/mezzi" },
          { label: vehicle.name },
        ]}
      />

      <OperazioniDetailHero
        eyebrow="Fleet detail"
        title={vehicle.name}
        description={`${vehicle.code}${vehicle.plate_number ? ` · ${vehicle.plate_number}` : ""}${vehicle.gps_provider_code ? ` · GPS ${vehicle.gps_provider_code}` : ""}`}
        status={statusLabels[vehicle.current_status] || vehicle.current_status}
        statusTone={statusTone[vehicle.current_status] || "bg-gray-100 text-gray-600"}
      >
        <OperazioniHeroNotice
          title="Dotazione"
          description={vehicle.has_gps_device ? "Il mezzo risulta dotato di dispositivo GPS." : "Il mezzo non risulta dotato di dispositivo GPS."}
        />
      </OperazioniDetailHero>

      <OperazioniCollectionPanel
        title="Scheda mezzo"
        description="Dati anagrafici essenziali del veicolo per consultazione rapida."
        count={5}
      >
        <OperazioniInfoGrid
          items={[
            { label: "Tipo", value: vehicle.vehicle_type },
            { label: "Marca / Modello", value: [vehicle.brand, vehicle.model].filter(Boolean).join(" ") || "—" },
            { label: "Carburante", value: vehicle.fuel_type || "—" },
            { label: "GPS", value: vehicle.has_gps_device ? "Si" : "No" },
            { label: "Ultimo aggiornamento", value: new Date(vehicle.updated_at).toLocaleDateString("it-IT") },
          ]}
        />
      </OperazioniCollectionPanel>

      <div className="grid gap-6 xl:grid-cols-2">
        <OperazioniCollectionPanel title="Assegnazioni" description="Storico assegnazioni del mezzo." count={0}>
          <div className="rounded-2xl border border-dashed border-[#d8dfd8] bg-[#f8faf8] p-6 text-sm text-gray-500">Storico assegnazioni in implementazione.</div>
        </OperazioniCollectionPanel>
        <OperazioniCollectionPanel title="Utilizzi recenti" description="Ultime sessioni di utilizzo." count={0}>
          <div className="rounded-2xl border border-dashed border-[#d8dfd8] bg-[#f8faf8] p-6 text-sm text-gray-500">Lista utilizzi in implementazione.</div>
        </OperazioniCollectionPanel>
        <OperazioniCollectionPanel title="Manutenzioni" description="Storico manutenzioni programmate e completate." count={0}>
          <div className="rounded-2xl border border-dashed border-[#d8dfd8] bg-[#f8faf8] p-6 text-sm text-gray-500">Storico manutenzioni in implementazione.</div>
        </OperazioniCollectionPanel>
        <FuelLogsPanel vehicleId={vehicleId} />
      </div>

      <Link href="/operazioni/mezzi" className="btn-secondary">
        Torna alla lista mezzi
      </Link>
    </div>
  );
}

export default function MezzoDetailPage() {
  const params = useParams<{ id: string }>();
  return (
    <OperazioniModulePage
      title="Dettaglio mezzo"
      description="Scheda e storico del veicolo."
      breadcrumb={`ID ${params.id}`}
    >
      {() => <MezzoDetailContent vehicleId={params.id} />}
    </OperazioniModulePage>
  );
}
