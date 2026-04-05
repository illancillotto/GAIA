"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { ChevronRightIcon } from "@/components/ui/icons";
import { getVehicle } from "@/features/operazioni/api/client";

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

function MezzoDetailContent({ token, vehicleId }: { token: string; vehicleId: string }) {
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

  useEffect(() => {
    void loadVehicle();
  }, [loadVehicle]);

  if (loading) {
    return <p className="text-sm text-gray-500">Caricamento mezzo in corso...</p>;
  }

  if (error || !vehicle) {
    return (
      <article className="panel-card">
        <p className="text-sm font-medium text-red-700">{error || "Mezzo non trovato"}</p>
      </article>
    );
  }

  return (
    <div className="page-stack">
      <nav className="flex items-center gap-1 text-sm text-gray-500">
        <Link href="/operazioni" className="hover:text-[#1D4E35]">Operazioni</Link>
        <ChevronRightIcon className="h-3 w-3" />
        <Link href="/operazioni/mezzi" className="hover:text-[#1D4E35]">Mezzi</Link>
        <ChevronRightIcon className="h-3 w-3" />
        <span className="text-gray-800">{vehicle.name}</span>
      </nav>

      <article className="panel-card">
        <div className="flex items-start justify-between">
          <div>
            <p className="section-title">{vehicle.name}</p>
            <p className="mt-1 text-sm text-gray-500">{vehicle.code}{vehicle.plate_number ? ` · ${vehicle.plate_number}` : ""}</p>
          </div>
          <span className={`rounded-full px-3 py-1 text-xs font-medium ${statusTone[vehicle.current_status] || "bg-gray-100 text-gray-600"}`}>
            {statusLabels[vehicle.current_status] || vehicle.current_status}
          </span>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
          <div>
            <p className="text-xs uppercase tracking-widest text-gray-400">Tipo</p>
            <p className="mt-1 font-medium text-gray-900">{vehicle.vehicle_type}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-widest text-gray-400">Marca / Modello</p>
            <p className="mt-1 font-medium text-gray-900">{[vehicle.brand, vehicle.model].filter(Boolean).join(" ") || "—"}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-widest text-gray-400">Carburante</p>
            <p className="mt-1 font-medium text-gray-900">{vehicle.fuel_type || "—"}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-widest text-gray-400">GPS</p>
            <p className="mt-1 font-medium text-gray-900">{vehicle.has_gps_device ? "Sì" : "No"}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-widest text-gray-400">Ultimo aggiornamento</p>
            <p className="mt-1 font-medium text-gray-900">{new Date(vehicle.updated_at).toLocaleDateString("it-IT")}</p>
          </div>
        </div>
      </article>

      <div className="grid gap-6 xl:grid-cols-2">
        <article className="panel-card">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <p className="section-title">Assegnazioni</p>
              <p className="section-copy">Storico assegnazioni del mezzo.</p>
            </div>
          </div>
          <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 p-6 text-center">
            <p className="text-sm font-medium text-gray-900">Assegnazioni</p>
            <p className="mt-1 text-sm text-gray-500">Storico assegnazioni in implementazione.</p>
          </div>
        </article>

        <article className="panel-card">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <p className="section-title">Utilizzi recenti</p>
              <p className="section-copy">Ultime sessioni di utilizzo.</p>
            </div>
          </div>
          <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 p-6 text-center">
            <p className="text-sm font-medium text-gray-900">Sessioni utilizzo</p>
            <p className="mt-1 text-sm text-gray-500">Lista utilizzi in implementazione.</p>
          </div>
        </article>

        <article className="panel-card">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <p className="section-title">Manutenzioni</p>
              <p className="section-copy">Storico manutenzioni programmate e completate.</p>
            </div>
          </div>
          <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 p-6 text-center">
            <p className="text-sm font-medium text-gray-900">Manutenzioni</p>
            <p className="mt-1 text-sm text-gray-500">Storico manutenzioni in implementazione.</p>
          </div>
        </article>

        <article className="panel-card">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <p className="section-title">Carburante</p>
              <p className="section-copy">Storico rifornimenti registrati.</p>
            </div>
          </div>
          <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 p-6 text-center">
            <p className="text-sm font-medium text-gray-900">Rifornimenti</p>
            <p className="mt-1 text-sm text-gray-500">Storico carburante in implementazione.</p>
          </div>
        </article>
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
      {({ token }) => <MezzoDetailContent token={token} vehicleId={params.id} />}
    </OperazioniModulePage>
  );
}
