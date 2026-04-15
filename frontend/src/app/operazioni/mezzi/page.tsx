"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ImportFleetTransactionsModal } from "@/components/operazioni/import-fleet-transactions-modal";
import {
  OperazioniCollectionHero,
  OperazioniCollectionPanel,
  OperazioniHeroNotice,
  OperazioniMetricStrip,
  OperazioniToolbar,
} from "@/components/operazioni/collection-layout";
import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { MetricCard } from "@/components/ui/metric-card";
import { EmptyState } from "@/components/ui/empty-state";
import { ChevronRightIcon, TruckIcon } from "@/components/ui/icons";
import { cn } from "@/lib/cn";
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
  notes?: string | null;
  brand?: string | null;
  model?: string | null;
}

const statusLabels: Record<string, string> = {
  available: "Disponibile",
  assigned: "Assegnato",
  in_use: "In uso",
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

const vehicleTypeLabels: Record<string, string> = {
  auto: "Automezzo",
  truck: "Autocarro",
  van: "Furgone",
  equipment: "Attrezzatura",
};

function normalizeSearch(value: string): string {
  return value.trim();
}

function titleCaseStatus(value: string): string {
  return statusLabels[value] ?? value.replaceAll("_", " ");
}

function vehicleTypeLabel(value: string): string {
  return vehicleTypeLabels[value] ?? value.replaceAll("_", " ");
}

function initialsForVehicle(vehicle: VehicleItem): string {
  const source = vehicle.name.trim() || vehicle.code.trim() || "M";
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }
  return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();
}

function compactLabel(vehicle: VehicleItem): string {
  const parts = [vehicle.code, vehicle.plate_number].filter(Boolean);
  return parts.join(" · ");
}

function vehicleVisualTone(vehicle: VehicleItem): string {
  if (vehicle.current_status === "maintenance") return "from-rose-50 via-white to-white";
  if (vehicle.current_status === "in_use") return "from-amber-50 via-white to-white";
  if (vehicle.current_status === "assigned") return "from-sky-50 via-white to-white";
  if (vehicle.current_status === "out_of_service") return "from-gray-50 via-white to-white";
  return "from-emerald-50 via-white to-white";
}

function DesktopVehicleCard({ vehicle }: { vehicle: VehicleItem }) {
  return (
    <Link
      href={`/operazioni/mezzi/${vehicle.id}`}
      className="group overflow-hidden rounded-[28px] border border-[#e6ebe5] bg-white shadow-panel transition hover:-translate-y-1 hover:border-[#c9d6cd] hover:shadow-lg"
    >
      <div className={cn("relative h-44 overflow-hidden bg-gradient-to-br", vehicleVisualTone(vehicle))}>
        <div className="absolute inset-x-0 top-0 flex items-center justify-between p-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-[20px] border border-white/80 bg-white/90 text-lg font-semibold text-[#1D4E35] shadow-sm">
            {initialsForVehicle(vehicle)}
          </div>
          <span className={cn("rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em]", statusTone[vehicle.current_status] ?? "bg-gray-100 text-gray-600")}>
            {titleCaseStatus(vehicle.current_status)}
          </span>
        </div>
        <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-black/5 to-transparent" />
      </div>
      <div className="px-5 pb-5 pt-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-[1.05rem] font-semibold uppercase tracking-tight text-gray-900">{vehicle.name}</p>
            <p className="mt-1 text-sm text-gray-600">
              {[vehicle.brand, vehicle.model, vehicleTypeLabel(vehicle.vehicle_type)].filter(Boolean).join(" · ") || vehicleTypeLabel(vehicle.vehicle_type)}
            </p>
          </div>
          <span className="text-lg text-gray-300 transition group-hover:text-[#1D4E35]">⋮</span>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="inline-flex rounded-full border border-[#e2e6e1] bg-[#f6f7f4] px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-[#5d695f]">
            {compactLabel(vehicle) || "Senza riferimenti"}
          </span>
          <span className="inline-flex rounded-full border border-[#e2e6e1] bg-white px-3 py-1 text-xs font-semibold text-gray-700">
            {vehicle.has_gps_device ? "GPS" : "No GPS"}
          </span>
        </div>
        <div className="mt-5 border-t border-dashed border-[#edf1eb] pt-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#667267]">Dettagli operativi</p>
          <div className="mt-3 flex items-center justify-between gap-3 text-sm text-gray-600">
            <div>
              <p className="font-medium text-gray-900">{vehicle.has_gps_device ? "GPS attivo" : "GPS non presente"}</p>
              <p className="mt-1 text-xs text-gray-500">{vehicle.is_active ? "Mezzo visibile in flotta" : "Mezzo disattivato"}</p>
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-full border border-[#e6ebe5] bg-white text-[#1D4E35]">
              <ChevronRightIcon className="h-4 w-4" />
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
}

function MobileVehicleCard({ vehicle }: { vehicle: VehicleItem }) {
  return (
    <Link
      href={`/operazioni/mezzi/${vehicle.id}`}
      className="flex items-center gap-3 rounded-[22px] border border-[#e6ebe5] bg-[linear-gradient(180deg,_#ffffff,_#fbfcfa)] px-3 py-3 shadow-panel transition active:scale-[0.995]"
    >
      <div className={cn("relative flex h-[60px] w-[60px] shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-gradient-to-br text-sm font-semibold text-[#1D4E35]", vehicleVisualTone(vehicle))}>
        <span className="absolute inset-0 bg-white/25" />
        <span className="relative">{initialsForVehicle(vehicle)}</span>
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">{vehicleTypeLabel(vehicle.vehicle_type)}</p>
            <p className="truncate text-[1rem] font-semibold leading-tight text-gray-900">{vehicle.name}</p>
          </div>
          <span className={cn("shrink-0 rounded-full px-2.5 py-1 text-[11px] font-semibold", statusTone[vehicle.current_status] ?? "bg-gray-100 text-gray-600")}>
            {titleCaseStatus(vehicle.current_status)}
          </span>
        </div>
        <p className="mt-1 text-xs text-gray-600">{compactLabel(vehicle) || vehicleTypeLabel(vehicle.vehicle_type)}</p>
        <div className="mt-3 flex items-center justify-between gap-3">
          <p className="truncate text-xs text-gray-500">
            {vehicle.has_gps_device ? "GPS attivo" : "Senza GPS"}
            {vehicle.notes ? ` · ${vehicle.notes}` : ""}
          </p>
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-[#f6f7f4] text-gray-500">
            <ChevronRightIcon className="h-3.5 w-3.5" />
          </div>
        </div>
      </div>
    </Link>
  );
}

function MezziContent() {
  const [vehicles, setVehicles] = useState<VehicleItem[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const params: Record<string, string> = { page_size: "24" };
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

  const metrics = useMemo(() => {
    const available = vehicles.filter((vehicle) => vehicle.current_status === "available").length;
    const inUse = vehicles.filter((vehicle) => vehicle.current_status === "in_use").length;
    const maintenance = vehicles.filter((vehicle) => vehicle.current_status === "maintenance").length;
    const assigned = vehicles.filter((vehicle) => vehicle.current_status === "assigned").length;
    return {
      available,
      inUse,
      maintenance,
      assigned,
    };
  }, [vehicles]);

  return (
    <div className="page-stack">
      <OperazioniCollectionHero
        eyebrow="Fleet registry"
        icon={<TruckIcon className="h-3.5 w-3.5" />}
        title="Mezzi operativi con stato di disponibilità, assegnazione e manutenzione sempre in evidenza."
        description="Vista allineata al workspace Operazioni: filtri rapidi e lista leggibile per codice/targa, tipologia e stato corrente."
      >
        {loadError ? (
          <OperazioniHeroNotice title="Caricamento non riuscito" description={loadError} tone="danger" />
        ) : (
          <OperazioniHeroNotice
            title="Sintesi flotta"
            description={`${metrics.available} disponibili, ${metrics.assigned} assegnati, ${metrics.inUse} in uso, ${metrics.maintenance} in manutenzione.`}
          />
        )}
        <div className="rounded-2xl border border-white/80 bg-white/75 px-4 py-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Filtro attivo</p>
          <p className="mt-2 text-sm font-medium text-gray-900">{statusFilter ? titleCaseStatus(statusFilter) : "Tutti gli stati"}</p>
          <p className="mt-1 text-sm text-gray-600">
            {normalizeSearch(search) ? `Ricerca: ${normalizeSearch(search)}` : "Nessuna ricerca testuale applicata."}
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button className="btn-primary" type="button" onClick={() => setIsImportModalOpen(true)}>
            Importa transazioni flotte
          </button>
        </div>
      </OperazioniCollectionHero>

      <OperazioniMetricStrip>
        <MetricCard label="Mezzi totali" value={total} sub="Veicoli registrati" />
        <MetricCard label="Disponibili" value={metrics.available} sub="Pronti all'uso" variant="success" />
        <MetricCard label="Assegnati" value={metrics.assigned} sub="In carico a operatori" variant="info" />
        <MetricCard label="In manutenzione" value={metrics.maintenance} sub="Fuori servizio" variant="danger" />
      </OperazioniMetricStrip>

      <OperazioniCollectionPanel
        title="Parco mezzi"
        description="Ricerca per codice, targa o nome e filtro per stato operativo."
        count={vehicles.length}
      >
        <OperazioniToolbar
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Cerca per nome, codice o targa"
          filterValue={statusFilter}
          onFilterChange={setStatusFilter}
          filterOptions={[
            { value: "", label: "Tutti gli stati" },
            { value: "available", label: "Disponibile" },
            { value: "assigned", label: "Assegnato" },
            { value: "in_use", label: "In uso" },
            { value: "maintenance", label: "In manutenzione" },
            { value: "out_of_service", label: "Fuori servizio" },
          ]}
        />

        <div className="mt-4">
          {isLoading ? (
            <p className="text-sm text-gray-500">Caricamento mezzi in corso.</p>
          ) : vehicles.length === 0 ? (
            <EmptyState icon={TruckIcon} title="Nessun mezzo trovato" description="Non risultano veicoli con i filtri correnti." />
          ) : (
            <>
              <div className="hidden gap-5 lg:grid xl:grid-cols-3">
                {vehicles.map((vehicle) => (
                  <DesktopVehicleCard key={vehicle.id} vehicle={vehicle} />
                ))}
              </div>
              <div className="space-y-3 lg:hidden">
                {vehicles.map((vehicle) => (
                  <MobileVehicleCard key={vehicle.id} vehicle={vehicle} />
                ))}
              </div>
            </>
          )}
        </div>
      </OperazioniCollectionPanel>

      <ImportFleetTransactionsModal
        open={isImportModalOpen}
        onClose={() => {
          setIsImportModalOpen(false);
        }}
      />
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
      {() => <MezziContent />}
    </OperazioniModulePage>
  );
}
