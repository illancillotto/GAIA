"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { EmptyState } from "@/components/ui/empty-state";
import {
  AlertTriangleIcon,
  CheckIcon,
  ChevronRightIcon,
  RefreshIcon,
  SearchIcon,
  TruckIcon,
} from "@/components/ui/icons";
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

const desktopStatusTone: Record<string, string> = {
  available: "bg-emerald-100 text-emerald-700",
  assigned: "bg-sky-100 text-sky-700",
  in_use: "bg-amber-100 text-amber-700",
  maintenance: "bg-rose-100 text-rose-700",
  out_of_service: "bg-slate-200 text-slate-600",
};

const mobileStatusTone: Record<string, string> = {
  available: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100",
  assigned: "bg-sky-50 text-sky-700 ring-1 ring-sky-100",
  in_use: "bg-indigo-50 text-indigo-700 ring-1 ring-indigo-100",
  maintenance: "bg-rose-50 text-rose-700 ring-1 ring-rose-100",
  out_of_service: "bg-slate-100 text-slate-600 ring-1 ring-slate-200",
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
  if (vehicle.current_status === "maintenance") {
    return "from-[#fff0ea] via-[#fff9f5] to-white";
  }
  if (vehicle.current_status === "in_use") {
    return "from-[#eef4ff] via-[#f9fbff] to-white";
  }
  if (vehicle.current_status === "assigned") {
    return "from-[#edf7ff] via-[#fbfeff] to-white";
  }
  return "from-[#eef7f1] via-[#f7fbf8] to-white";
}

function desktopMetricTone(variant: "dark" | "success" | "warning" | "danger"): string {
  if (variant === "dark") {
    return "border-[#204f39] bg-[#204f39] text-white shadow-[0_24px_50px_rgba(29,78,53,0.24)]";
  }
  if (variant === "success") {
    return "border-[#e6f3ea] bg-white text-[#1a2d24]";
  }
  if (variant === "warning") {
    return "border-[#ece8dd] bg-white text-[#1a2d24]";
  }
  return "border-[#f4e3de] bg-white text-[#1a2d24]";
}

function mobileMetricTone(variant: "dark" | "success" | "warning" | "danger"): string {
  if (variant === "dark") {
    return "border-[#204f39] bg-[#204f39] text-white shadow-[0_20px_35px_rgba(29,78,53,0.22)]";
  }
  if (variant === "success") {
    return "border-[#e7f3ea] bg-white text-[#1a2d24]";
  }
  if (variant === "warning") {
    return "border-[#ece8dd] bg-white text-[#1a2d24]";
  }
  return "border-[#f4e3de] bg-white text-[#1a2d24]";
}

function MetricTile({
  label,
  value,
  hint,
  icon,
  variant,
  desktopDelta,
}: {
  label: string;
  value: number;
  hint: string;
  icon: React.ReactNode;
  variant: "dark" | "success" | "warning" | "danger";
  desktopDelta?: string;
}) {
  return (
    <>
      <article
        className={cn(
          "hidden min-h-[132px] rounded-[26px] border px-5 py-4 lg:flex lg:flex-col",
          desktopMetricTone(variant),
        )}
      >
        <div className="flex items-center justify-between">
          <div
            className={cn(
              "flex h-11 w-11 items-center justify-center rounded-2xl",
              variant === "dark" ? "bg-white/12 text-white" : "bg-[#eef5f0] text-[#1D4E35]",
            )}
          >
            {icon}
          </div>
          {desktopDelta ? (
            <span
              className={cn(
                "rounded-full px-2.5 py-1 text-[11px] font-semibold",
                variant === "danger"
                  ? "bg-rose-50 text-rose-600"
                  : variant === "dark"
                    ? "bg-white/12 text-white/85"
                    : "bg-emerald-50 text-emerald-600",
              )}
            >
              {desktopDelta}
            </span>
          ) : null}
        </div>
        <div className="mt-auto">
          <p className="text-[2rem] font-semibold tracking-tight">{value}</p>
          <p className={cn("mt-1 text-[11px] font-semibold uppercase tracking-[0.18em]", variant === "dark" ? "text-white/70" : "text-[#7b897f]")}>
            {label}
          </p>
          <p className={cn("mt-1 text-xs", variant === "dark" ? "text-white/68" : "text-[#7a867d]")}>{hint}</p>
        </div>
      </article>

      <article
        className={cn(
          "rounded-[22px] border px-4 py-4 lg:hidden",
          mobileMetricTone(variant),
        )}
      >
        <div className="flex items-center justify-between">
          <p className={cn("text-[10px] font-semibold uppercase tracking-[0.2em]", variant === "dark" ? "text-white/70" : "text-[#7b897f]")}>
            {label}
          </p>
          <div
            className={cn(
              "flex h-8 w-8 items-center justify-center rounded-xl",
              variant === "dark" ? "bg-white/12 text-white" : "bg-[#f6f8f5] text-[#1D4E35]",
            )}
          >
            {icon}
          </div>
        </div>
        <p className="mt-3 text-[2rem] font-semibold leading-none tracking-tight">{value}</p>
        <p className={cn("mt-1 text-xs", variant === "dark" ? "text-white/68" : "text-[#7a867d]")}>{hint}</p>
      </article>
    </>
  );
}

function DesktopVehicleCard({ vehicle }: { vehicle: VehicleItem }) {
  return (
    <Link
      href={`/operazioni/mezzi/${vehicle.id}`}
      className="group overflow-hidden rounded-[28px] border border-[#e6ece7] bg-white shadow-[0_16px_36px_rgba(15,23,42,0.06)] transition hover:-translate-y-1 hover:border-[#ccd9d0] hover:shadow-[0_24px_44px_rgba(15,23,42,0.09)]"
    >
      <div className={cn("relative h-44 overflow-hidden bg-gradient-to-br", vehicleVisualTone(vehicle))}>
        <div className="absolute inset-x-0 top-0 flex items-center justify-between p-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-[20px] border border-white/80 bg-white/90 text-lg font-semibold text-[#1D4E35] shadow-sm">
            {initialsForVehicle(vehicle)}
          </div>
          <span className={cn("rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em]", desktopStatusTone[vehicle.current_status] ?? "bg-slate-200 text-slate-600")}>
            {titleCaseStatus(vehicle.current_status)}
          </span>
        </div>
        <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-black/6 to-transparent" />
      </div>
      <div className="px-5 pb-5 pt-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-[1.05rem] font-semibold uppercase tracking-tight text-[#1d2b24]">{vehicle.name}</p>
            <p className="mt-1 text-sm text-[#7a867d]">
              {[vehicle.brand, vehicle.model, vehicleTypeLabel(vehicle.vehicle_type)].filter(Boolean).join(" · ") || vehicleTypeLabel(vehicle.vehicle_type)}
            </p>
          </div>
          <span className="text-lg text-[#a7b0a8] transition group-hover:text-[#1D4E35]">⋮</span>
        </div>
        <div className="mt-4">
          <span className="inline-flex rounded-full bg-[#f2f5f1] px-3 py-1 text-xs font-semibold text-[#839085]">
            {compactLabel(vehicle) || "Senza riferimenti"}
          </span>
        </div>
        <div className="mt-5 border-t border-dashed border-[#e6ece7] pt-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#96a198]">Dettagli operativi</p>
          <div className="mt-3 flex items-center justify-between gap-3 text-sm text-[#58655d]">
            <div>
              <p className="font-medium text-[#30433a]">{vehicle.has_gps_device ? "GPS attivo" : "GPS non presente"}</p>
              <p className="mt-1 text-xs text-[#8a958d]">{vehicle.is_active ? "Mezzo visibile in flotta" : "Mezzo disattivato"}</p>
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-full border border-[#e1e8e2] bg-white text-[#1D4E35]">
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
      className="flex items-center gap-3 rounded-[22px] border border-[#e6ece7] bg-white px-3 py-3 shadow-[0_10px_24px_rgba(15,23,42,0.05)] transition active:scale-[0.995]"
    >
      <div className={cn("relative flex h-[60px] w-[60px] shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-gradient-to-br text-sm font-semibold text-[#1D4E35]", vehicleVisualTone(vehicle))}>
        <span className="absolute inset-0 bg-white/20" />
        <span className="relative">{initialsForVehicle(vehicle)}</span>
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-[11px] font-semibold uppercase tracking-[0.18em] text-[#9aa49d]">{vehicleTypeLabel(vehicle.vehicle_type)}</p>
            <p className="truncate text-[1rem] font-semibold leading-tight text-[#213229]">{vehicle.name}</p>
          </div>
          <span className={cn("shrink-0 rounded-full px-2.5 py-1 text-[11px] font-semibold", mobileStatusTone[vehicle.current_status] ?? "bg-slate-100 text-slate-600 ring-1 ring-slate-200")}>
            {titleCaseStatus(vehicle.current_status)}
          </span>
        </div>
        <p className="mt-1 text-xs text-[#819087]">{compactLabel(vehicle) || vehicleTypeLabel(vehicle.vehicle_type)}</p>
        <div className="mt-3 flex items-center justify-between gap-3">
          <p className="truncate text-xs text-[#8b9690]">{vehicle.has_gps_device ? "GPS attivo" : "Senza GPS"}{vehicle.notes ? ` · ${vehicle.notes}` : ""}</p>
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-[#f4f7f5] text-[#7b877f]">
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
    return {
      available,
      inUse,
      maintenance,
    };
  }, [vehicles]);

  return (
    <div className="page-stack">
      <section className="overflow-hidden rounded-[32px] border border-[#e1e8e2] bg-[radial-gradient(circle_at_top_left,_rgba(238,245,239,0.95),_rgba(255,255,255,0.98)_58%,_rgba(249,247,240,0.92)_100%)] px-4 py-5 shadow-[0_28px_70px_rgba(15,23,42,0.08)] sm:px-6 sm:py-6 lg:px-8 lg:py-8">
        <div className="hidden items-start justify-between gap-6 lg:flex">
          <div className="max-w-3xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#93a098]">Fleet Registry</p>
            <h1 className="mt-2 text-[2.4rem] font-semibold tracking-tight text-[#1b2a22]">Mezzi</h1>
            <p className="mt-3 max-w-2xl text-base leading-7 text-[#66746c]">
              Gestione centralizzata della flotta aziendale. Monitoraggio in tempo reale di disponibilità,
              manutenzione e assegnazioni.
            </p>
          </div>
          <div className="rounded-[24px] border border-white/80 bg-white/80 px-5 py-4 shadow-sm">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#93a098]">Filtro attivo</p>
            <p className="mt-2 text-sm font-medium text-[#23342b]">
              {statusFilter ? titleCaseStatus(statusFilter) : "Tutti gli stati"}
            </p>
            <p className="mt-1 text-sm text-[#7a867d]">
              {normalizeSearch(search) ? `Ricerca: ${normalizeSearch(search)}` : "Nessuna ricerca testuale applicata."}
            </p>
          </div>
        </div>

        <div className="lg:hidden">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-[#1D4E35]">
              <button type="button" className="rounded-xl border border-[#dfe8e2] bg-white/90 p-2 text-[#5f6c64]">
                <RefreshIcon className="h-4 w-4" />
              </button>
              <span className="text-lg font-semibold tracking-tight">GAIA</span>
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-full border border-[#dfe8e2] bg-white/90 text-[#4e5f55]">
              <AlertTriangleIcon className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-5">
            <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-[#9ba79e]">Gestione apparati info</p>
            <h1 className="mt-1 text-[2rem] font-semibold tracking-tight text-[#1b2a22]">Mezzi</h1>
            <p className="mt-2 text-sm leading-6 text-[#738178]">
              Anagrafica mezzi, assegnazioni, sessioni d&apos;uso, carburante e manutenzioni.
            </p>
          </div>
        </div>

        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:mt-8 lg:grid-cols-4 lg:gap-4">
          <MetricTile
            label="Mezzi totali"
            value={total}
            hint="Veicoli registrati"
            icon={<TruckIcon className="h-5 w-5" />}
            variant="dark"
            desktopDelta="+4.2%"
          />
          <MetricTile
            label="Disponibili"
            value={metrics.available}
            hint="Pronti all'uso"
            icon={<CheckIcon className="h-5 w-5" />}
            variant="success"
          />
          <MetricTile
            label="In utilizzo"
            value={metrics.inUse}
            hint="Attualmente attivi"
            icon={<TruckIcon className="h-5 w-5" />}
            variant="warning"
          />
          <MetricTile
            label="In manutenzione"
            value={metrics.maintenance}
            hint="Fuori servizio"
            icon={<AlertTriangleIcon className="h-5 w-5" />}
            variant="danger"
          />
        </div>

        <div className="mt-6 hidden items-center gap-3 lg:flex">
          <label className="min-w-0 flex-1">
            <span className="sr-only">Ricerca mezzi</span>
            <div className="flex items-center gap-3 rounded-2xl border border-[#e2e8e3] bg-white/92 px-4 py-3 shadow-sm">
              <SearchIcon className="h-4 w-4 text-[#9aa49d]" />
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Filtra per modello, targa o operatore..."
                className="w-full border-0 bg-transparent text-sm text-[#213229] outline-none placeholder:text-[#9aa49d]"
              />
            </div>
          </label>
          <label className="shrink-0">
            <span className="sr-only">Filtro stato</span>
            <div className="flex items-center gap-2 rounded-2xl border border-[#e2e8e3] bg-white/92 px-4 py-3 shadow-sm">
              <span className="text-sm text-[#7d8a82]">↕</span>
              <select
                className="border-0 bg-transparent text-sm font-medium text-[#213229] outline-none"
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
              >
                <option value="">Stato</option>
                <option value="available">Disponibile</option>
                <option value="assigned">Assegnato</option>
                <option value="in_use">In uso</option>
                <option value="maintenance">In manutenzione</option>
                <option value="out_of_service">Fuori servizio</option>
              </select>
            </div>
          </label>
          <button
            type="button"
            disabled
            className="rounded-2xl bg-[#204f39] px-5 py-3 text-sm font-semibold text-white opacity-90 disabled:cursor-not-allowed disabled:opacity-70"
            title="Creazione mezzo non ancora disponibile in UI"
          >
            + Nuovo Mezzo
          </button>
        </div>

        <div className="mt-5 space-y-3 lg:hidden">
          <label className="block">
            <span className="sr-only">Ricerca mezzi</span>
            <div className="flex items-center gap-3 rounded-2xl border border-[#e2e8e3] bg-white/92 px-4 py-3 shadow-sm">
              <SearchIcon className="h-4 w-4 text-[#9aa49d]" />
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Cerca per nome, codice o targa"
                className="w-full border-0 bg-transparent text-sm text-[#213229] outline-none placeholder:text-[#9aa49d]"
              />
            </div>
          </label>
          <div className="flex items-center justify-between">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#9aa49d]">Vista elenco</p>
            <label className="flex items-center gap-2 text-sm font-medium text-[#5c6b62]">
              <span>Filtra</span>
              <select
                className="border-0 bg-transparent text-sm font-medium text-[#213229] outline-none"
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
              >
                <option value="">Tutti</option>
                <option value="available">Disponibile</option>
                <option value="assigned">Assegnato</option>
                <option value="in_use">In uso</option>
                <option value="maintenance">In manutenzione</option>
                <option value="out_of_service">Fuori servizio</option>
              </select>
            </label>
          </div>
        </div>
      </section>

      {loadError ? (
        <article className="rounded-[28px] border border-red-100 bg-red-50 px-5 py-4 text-sm text-red-700 shadow-sm">
          {loadError}
        </article>
      ) : null}

      <section className="hidden lg:block">
        <div className="mb-4 flex items-center justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#9aa49d]">Lista operativa</p>
            <h2 className="mt-1 text-2xl font-semibold tracking-tight text-[#1b2a22]">Parco mezzi</h2>
          </div>
          <p className="text-sm text-[#7d8a82]">{vehicles.length} card in evidenza</p>
        </div>
        {isLoading ? (
          <article className="rounded-[28px] border border-[#e2e8e3] bg-white px-6 py-10 text-sm text-[#7d8a82] shadow-sm">
            Caricamento mezzi in corso.
          </article>
        ) : vehicles.length === 0 ? (
          <EmptyState
            icon={TruckIcon}
            title="Nessun mezzo trovato"
            description="Non risultano veicoli con i filtri correnti."
          />
        ) : (
          <div className="grid gap-5 xl:grid-cols-3">
            {vehicles.map((vehicle) => (
              <DesktopVehicleCard key={vehicle.id} vehicle={vehicle} />
            ))}
          </div>
        )}
      </section>

      <section className="lg:hidden">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#9aa49d]">Vista elenco</p>
            <h2 className="mt-1 text-[1.35rem] font-semibold tracking-tight text-[#1b2a22]">Parco mezzi</h2>
          </div>
          <p className="text-xs text-[#7d8a82]">{vehicles.length} risultati</p>
        </div>
        {isLoading ? (
          <article className="rounded-[24px] border border-[#e2e8e3] bg-white px-4 py-8 text-sm text-[#7d8a82] shadow-sm">
            Caricamento mezzi in corso.
          </article>
        ) : vehicles.length === 0 ? (
          <EmptyState
            icon={TruckIcon}
            title="Nessun mezzo trovato"
            description="Non risultano veicoli con i filtri correnti."
          />
        ) : (
          <div className="space-y-3">
            {vehicles.map((vehicle) => (
              <MobileVehicleCard key={vehicle.id} vehicle={vehicle} />
            ))}
          </div>
        )}

        <button
          type="button"
          disabled
          className="fixed bottom-24 right-5 flex h-14 w-14 items-center justify-center rounded-full bg-[#204f39] text-3xl leading-none text-white shadow-[0_18px_40px_rgba(29,78,53,0.28)] disabled:cursor-not-allowed disabled:opacity-80"
          title="Creazione mezzo non ancora disponibile in UI"
        >
          +
        </button>
      </section>
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
