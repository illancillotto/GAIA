"use client";

import { useCallback, useEffect, useState } from "react";

import {
  OperazioniCollectionHero,
  OperazioniCollectionPanel,
  OperazioniHeroNotice,
  OperazioniList,
  OperazioniListLink,
  OperazioniMetricStrip,
  OperazioniToolbar,
} from "@/components/operazioni/collection-layout";
import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { MetricCard } from "@/components/ui/metric-card";
import { EmptyState } from "@/components/ui/empty-state";
import { TruckIcon } from "@/components/ui/icons";
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

function MezziContent() {
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
      <OperazioniCollectionHero
        eyebrow="Fleet registry"
        icon={<TruckIcon className="h-3.5 w-3.5" />}
        title="Gestione mezzi per disponibilità, utilizzo, manutenzioni e dotazioni operative."
        description="Vista unica per leggere la flotta, isolare rapidamente i mezzi critici e aprire le schede veicolo senza perdere il contesto di lavoro."
      >
        {loadError ? (
          <OperazioniHeroNotice title="Caricamento non riuscito" description={loadError} tone="danger" />
        ) : (
          <OperazioniHeroNotice
            title="Quadro di presidio"
            description={`${total} mezzi censiti. Usa ricerca e stato per convergere subito sui veicoli operativi o da fermo.`}
          />
        )}
        <div className="rounded-2xl border border-white/80 bg-white/75 px-4 py-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Filtro attivo</p>
          <p className="mt-2 text-sm font-medium text-gray-900">{statusFilter ? statusLabels[statusFilter] ?? statusFilter : "Nessuno stato selezionato"}</p>
          <p className="mt-1 text-sm text-gray-600">{search.trim() ? `Ricerca: ${search.trim()}` : "Nessuna ricerca testuale applicata."}</p>
        </div>
      </OperazioniCollectionHero>

      <OperazioniMetricStrip>
        <MetricCard label="Mezzi totali" value={total} sub="Veicoli registrati nel sistema" />
        <MetricCard label="Disponibili" value={availableCount} sub="Mezzi pronti per l&apos;assegnazione" variant="success" />
        <MetricCard label="In utilizzo" value={inUseCount} sub="Mezzi attualmente in uso" variant="warning" />
        <MetricCard label="In manutenzione" value={maintenanceCount} sub="Mezzi fuori servizio per manutenzione" variant={maintenanceCount > 0 ? "danger" : "default"} />
      </OperazioniMetricStrip>

      <OperazioniCollectionPanel
        title="Parco mezzi"
        description="Lista compatta ad alta densità per nome, codice, targa, GPS e stato attuale."
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
            { value: "in_use", label: "In utilizzo" },
            { value: "maintenance", label: "In manutenzione" },
            { value: "out_of_service", label: "Fuori servizio" },
          ]}
        />

        <div className="mt-4">
          {isLoading ? (
            <p className="text-sm text-gray-500">Caricamento mezzi in corso.</p>
          ) : vehicles.length === 0 ? (
            <EmptyState
              icon={TruckIcon}
              title="Nessun mezzo trovato"
              description="Non risultano veicoli con i filtri correnti."
            />
          ) : (
            <OperazioniList>
              {vehicles.map((vehicle) => (
                <OperazioniListLink
                  key={vehicle.id}
                  href={`/operazioni/mezzi/${vehicle.id}`}
                  title={vehicle.name}
                  meta={`${vehicle.code}${vehicle.plate_number ? ` · ${vehicle.plate_number}` : ""}${vehicle.has_gps_device ? " · GPS" : " · senza GPS"}`}
                  status={statusLabels[vehicle.current_status] || vehicle.current_status}
                  statusTone={statusTone[vehicle.current_status] || "bg-gray-100 text-gray-600"}
                  aside={
                    <span className="rounded-full border border-[#dbe6de] bg-[#f6faf7] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#476151]">
                      {vehicle.vehicle_type}
                    </span>
                  }
                />
              ))}
            </OperazioniList>
          )}
        </div>
      </OperazioniCollectionPanel>
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
