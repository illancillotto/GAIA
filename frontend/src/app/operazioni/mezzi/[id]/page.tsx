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
import { getVehicle, getVehicleFuelLogs, queueSingleVehicleAutodocSync, updateVehicle, type VehicleFuelLogItem } from "@/features/operazioni/api/client";
import { cn } from "@/lib/cn";

interface VehicleDetail {
  id: string;
  code: string;
  name: string;
  vehicle_type: string;
  plate_number: string | null;
  asset_tag: string | null;
  brand: string | null;
  model: string | null;
  fuel_type: string | null;
  current_status: string;
  has_gps_device: boolean;
  gps_provider_code: string | null;
  autodoc_url: string | null;
  autodoc_title: string | null;
  autodoc_data: Record<string, string> | null;
  autodoc_synced_at: string | null;
  autodoc_sync_error: string | null;
  is_active: boolean;
  current_assignment: {
    assignment_target_type?: string | null;
    operator_user_id?: number | null;
    team_id?: string | null;
    start_at?: string | null;
  } | null;
  last_odometer_km: number | null;
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

function fmtNullable(value: string | null | undefined) {
  if (!value || !String(value).trim()) return "—";
  return value;
}

function normalizeAutodocUrl(value: string) {
  return value.trim();
}

function isAutodocUrl(value: string) {
  try {
    const url = new URL(value);
    return /(^|\.)auto-doc\.it$/i.test(url.hostname);
  } catch {
    return false;
  }
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

function AutodocPanel({
  vehicle,
  onSaved,
}: {
  vehicle: VehicleDetail;
  onSaved: (vehicle: VehicleDetail) => void;
}) {
  const [url, setUrl] = useState(vehicle.autodoc_url ?? "");
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setUrl(vehicle.autodoc_url ?? "");
  }, [vehicle.autodoc_url]);

  async function handleSave(): Promise<void> {
    const normalized = normalizeAutodocUrl(url);
    if (!normalized) {
      setError("Inserisci un link AUTODOC valido.");
      setMessage(null);
      return;
    }
    if (!isAutodocUrl(normalized)) {
      setError("Il link deve puntare a auto-doc.it.");
      setMessage(null);
      return;
    }

    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await updateVehicle(vehicle.id, { autodoc_url: normalized });
      onSaved(updated as VehicleDetail);
      setMessage("Link AUTODOC salvato.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore salvataggio link AUTODOC");
    } finally {
      setSaving(false);
    }
  }

  async function handleSync(): Promise<void> {
    if (!vehicle.autodoc_url) {
      setError("Salva prima il link AUTODOC del mezzo.");
      setMessage(null);
      return;
    }
    setSyncing(true);
    setError(null);
    setMessage(null);
    try {
      const response = await queueSingleVehicleAutodocSync(vehicle.id);
      setMessage(`Sync AUTODOC accodata. Job ${response.job.job_id.slice(0, 8)} in stato ${response.job.status}.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore accodamento sync AUTODOC");
    } finally {
      setSyncing(false);
    }
  }

  return (
    <OperazioniCollectionPanel
      title="AUTODOC"
      description="Collegamento rapido alla scheda tecnica del mezzo su AUTODOC e sync asincrona tramite worker browser dedicato."
      count={vehicle.autodoc_data ? Object.keys(vehicle.autodoc_data).length : 0}
    >
      <div className="space-y-4">
        <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_auto_auto]">
          <input
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            placeholder="https://www.auto-doc.it/ricambi-auto/..."
            className="min-w-0 rounded-2xl border border-[#d8dfd8] bg-white px-4 py-3 text-sm text-gray-900 outline-none transition focus:border-[#1D4E35]"
          />
          <button type="button" className="btn-primary" disabled={saving} onClick={() => void handleSave()}>
            {saving ? "Salvataggio..." : "Salva link"}
          </button>
          {vehicle.autodoc_url ? (
            <a href={vehicle.autodoc_url} target="_blank" rel="noreferrer" className="btn-secondary text-center">
              Apri AUTODOC
            </a>
          ) : (
            <button type="button" className="btn-secondary" disabled>
              Apri AUTODOC
            </button>
          )}
        </div>

        <div className="flex flex-wrap gap-3">
          <button type="button" className="btn-primary" disabled={syncing || !vehicle.autodoc_url} onClick={() => void handleSync()}>
            {syncing ? "Accodamento..." : "Sincronizza dettagli automezzo"}
          </button>
        </div>

        <div className="rounded-2xl border border-[#e6ebe5] bg-[#f8faf8] p-4 text-sm text-gray-600">
          <p className="font-medium text-gray-900">Nota tecnica</p>
          <p className="mt-1">
            La sincronizzazione passa da un worker browser Playwright dedicato, perché le richieste server-to-server dirette verso AUTODOC vengono bloccate da Cloudflare con pagina
            {" "}
            <span className="font-medium">Just a moment…</span>.
            In questa prima versione il worker sincronizza i mezzi che hanno gia un link AUTODOC salvato.
          </p>
          {vehicle.autodoc_synced_at ? (
            <p className="mt-2 text-xs text-gray-500">Ultimo tentativo sync: {fmtDate(vehicle.autodoc_synced_at)}</p>
          ) : null}
          {vehicle.autodoc_sync_error ? <p className="mt-2 text-xs text-amber-700">{vehicle.autodoc_sync_error}</p> : null}
        </div>

        {vehicle.autodoc_title || vehicle.autodoc_data ? (
          <div className="rounded-2xl border border-[#e6ebe5] bg-white p-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">Dati AUTODOC salvati</p>
            {vehicle.autodoc_title ? <p className="mt-2 text-sm font-semibold text-gray-900">{vehicle.autodoc_title}</p> : null}
            {vehicle.autodoc_data && Object.keys(vehicle.autodoc_data).length > 0 ? (
              <dl className="mt-3 grid gap-3 sm:grid-cols-2">
                {Object.entries(vehicle.autodoc_data).map(([label, value]) => (
                  <div key={label} className="rounded-xl border border-[#edf1ec] bg-[#fbfcfa] px-3 py-2">
                    <dt className="text-[10px] font-semibold uppercase tracking-[0.16em] text-gray-500">{label}</dt>
                    <dd className="mt-1 text-sm text-gray-900">{value}</dd>
                  </div>
                ))}
              </dl>
            ) : null}
          </div>
        ) : null}

        {message ? <p className="text-sm text-[#1D4E35]">{message}</p> : null}
        {error ? <p className="text-sm text-red-700">{error}</p> : null}
      </div>
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
      <div className="flex items-center justify-start">
        <Link href="/operazioni/mezzi" className="btn-secondary">
          <span className="material-symbols-outlined text-base">arrow_back</span>
          Torna ai mezzi
        </Link>
      </div>

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
        description="Dati anagrafici e operativi del veicolo recuperati dal catalogo mezzi."
        count={11}
      >
        <OperazioniInfoGrid
          items={[
            { label: "Codice", value: vehicle.code },
            { label: "Targa", value: fmtNullable(vehicle.plate_number) },
            { label: "Asset tag", value: fmtNullable(vehicle.asset_tag) },
            { label: "Tipo", value: vehicle.vehicle_type },
            { label: "Marca / Modello", value: [vehicle.brand, vehicle.model].filter(Boolean).join(" ") || "—" },
            { label: "Carburante", value: fmtNullable(vehicle.fuel_type) },
            { label: "Stato", value: statusLabels[vehicle.current_status] || vehicle.current_status },
            { label: "Attivo", value: vehicle.is_active ? "Si" : "No" },
            { label: "GPS", value: vehicle.has_gps_device ? "Si" : "No" },
            { label: "Codice GPS", value: fmtNullable(vehicle.gps_provider_code) },
            {
              label: "Ultimo contachilometri",
              value: vehicle.last_odometer_km != null ? `${fmtNum(String(vehicle.last_odometer_km), 0)} km` : "—",
            },
            {
              label: "Assegnazione corrente",
              value: vehicle.current_assignment
                ? `${vehicle.current_assignment.assignment_target_type === "team" ? "Team" : "Operatore"} · dal ${vehicle.current_assignment.start_at ? fmtDate(vehicle.current_assignment.start_at) : "—"}`
                : "Nessuna",
            },
            { label: "Creato il", value: fmtDate(vehicle.created_at) },
            { label: "Ultimo aggiornamento", value: fmtDate(vehicle.updated_at) },
          ]}
        />
      </OperazioniCollectionPanel>

      <AutodocPanel vehicle={vehicle} onSaved={setVehicle} />

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
