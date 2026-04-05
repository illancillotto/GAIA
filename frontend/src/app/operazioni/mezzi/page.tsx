"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { MetricCard } from "@/components/ui/metric-card";
import { EmptyState } from "@/components/ui/empty-state";
import { TruckIcon, ChevronRightIcon } from "@/components/ui/icons";
import { getVehicles } from "@/features/operazioni/api/client";

interface VehicleItem {
  id: string;
  code: string;
  name: string;
  vehicle_type: string;
  plate_number: string | null;
  current_status: string;
  has_gps_device: boolean;
  is_active: boolean;
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

function BadgeCount({ value }: { value: number }) {
  return (
    <span className="rounded-full bg-[#EAF3E8] px-2.5 py-1 text-xs font-semibold text-[#1D4E35]">
      {value}
    </span>
  );
}

function MezziContent({ token }: { token: string }) {
  const [vehicles, setVehicles] = useState<VehicleItem[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const loadData = useCallback(async () => {
    try {
      const params: Record<string, string> = { page_size: "50" };
      if (search.trim()) params.search = search.trim();
      if (statusFilter) params.status = statusFilter;
      const data = await getVehicles(params);
      setVehicles(data.items ?? []);
      setTotal(data.total ?? 0);
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore nel caricamento mezzi");
    } finally {
      setIsLoading(false);
    }
  }, [search, statusFilter]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const availableCount = vehicles.filter((v) => v.current_status === "available").length;
  const inUseCount = vehicles.filter((v) => v.current_status === "in_use").length;
  const maintenanceCount = vehicles.filter((v) => v.current_status === "maintenance").length;

  return (
    <div className="page-stack">
      <p className="text-sm text-gray-500">
        Gestione anagrafica mezzi, assegnazioni a operatori e squadre, sessioni utilizzo, carburante e manutenzioni.
      </p>

      {loadError ? (
        <article className="panel-card">
          <p className="text-sm font-medium text-red-700">Caricamento non riuscito</p>
          <p className="mt-2 text-sm text-gray-600">{loadError}</p>
        </article>
      ) : null}

      <div className="surface-grid">
        <MetricCard label="Mezzi totali" value={total} sub="Veicoli registrati nel sistema" />
        <MetricCard label="Disponibili" value={availableCount} sub="Mezzi pronti per l&apos;assegnazione" variant="success" />
        <MetricCard label="In utilizzo" value={inUseCount} sub="Mezzi attualmente in uso" variant="warning" />
        <MetricCard label="In manutenzione" value={maintenanceCount} sub="Mezzi fuori servizio per manutenzione" variant={maintenanceCount > 0 ? "danger" : "default"} />
      </div>

      <article className="panel-card">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <p className="section-title">Elenco mezzi</p>
            <p className="section-copy">Tutti i veicoli registrati con stato e dettagli.</p>
          </div>
          <BadgeCount value={vehicles.length} />
        </div>

        <div className="mb-4 flex flex-wrap gap-3">
          <input
            className="form-control flex-1 min-w-[200px]"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Cerca per nome, codice o targa"
          />
          <select
            className="form-control"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">Tutti gli stati</option>
            <option value="available">Disponibile</option>
            <option value="in_use">In utilizzo</option>
            <option value="maintenance">In manutenzione</option>
            <option value="out_of_service">Fuori servizio</option>
          </select>
        </div>

        {isLoading ? (
          <p className="text-sm text-gray-500">Caricamento mezzi in corso.</p>
        ) : vehicles.length === 0 ? (
          <EmptyState
            icon={TruckIcon}
            title="Nessun mezzo trovato"
            description="Non risultano veicoli con i filtri correnti."
          />
        ) : (
          <div className="max-h-[32rem] space-y-3 overflow-y-auto pr-1">
            {vehicles.map((vehicle) => (
              <Link
                key={vehicle.id}
                href={`/operazioni/mezzi/${vehicle.id}`}
                className="flex w-full items-center justify-between rounded-lg border border-gray-100 px-4 py-3 text-left transition hover:bg-gray-50"
              >
                <div>
                  <p className="text-sm font-medium text-gray-900">{vehicle.name}</p>
                  <p className="mt-1 text-xs text-gray-500">
                    {vehicle.code}{vehicle.plate_number ? ` · ${vehicle.plate_number}` : ""}{vehicle.has_gps_device ? " · GPS" : ""}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusTone[vehicle.current_status] || "bg-gray-100 text-gray-600"}`}>
                    {statusLabels[vehicle.current_status] || vehicle.current_status}
                  </span>
                  <ChevronRightIcon className="h-4 w-4 text-gray-300" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </article>
    </div>
  );
}

export default function MezziPage() {
  return (
    <OperazioniModulePage
      title="Mezzi"
      description="Anagrafica mezzi, assegnazioni, sessioni d’uso, carburante e manutenzioni."
      breadcrumb="Lista"
    >
      {({ token }) => <MezziContent token={token} />}
    </OperazioniModulePage>
  );
}
