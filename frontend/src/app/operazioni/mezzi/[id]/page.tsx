"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

import { ProtectedPage } from "@/components/app/protected-page";
import { TruckIcon, ChevronRightIcon } from "@/components/ui/icons";
import { getVehicle } from "@/features/operazioni/api/client";
import { getStoredAccessToken } from "@/lib/auth";

export default function MezzoDetailPage() {
  const params = useParams<{ id: string }>();
  const [vehicle, setVehicle] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadVehicle = useCallback(async () => {
    const token = getStoredAccessToken();
    if (!token || !params.id) return;
    try {
      const data = await getVehicle(params.id);
      setVehicle(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore caricamento mezzo");
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  useEffect(() => {
    void loadVehicle();
  }, [loadVehicle]);

  const statusColors: Record<string, string> = {
    available: "bg-green-100 text-green-800",
    assigned: "bg-blue-100 text-blue-800",
    in_use: "bg-amber-100 text-amber-800",
    maintenance: "bg-red-100 text-red-800",
    out_of_service: "bg-gray-100 text-gray-800",
  };

  const statusLabels: Record<string, string> = {
    available: "Disponibile",
    assigned: "Assegnato",
    in_use: "In utilizzo",
    maintenance: "In manutenzione",
    out_of_service: "Fuori servizio",
  };

  if (loading) {
    return (
      <ProtectedPage title="Dettaglio Mezzo" description="Caricamento..." breadcrumb="Mezzi" requiredModule="operazioni">
        <div className="py-8 text-center text-sm text-gray-500">Caricamento...</div>
      </ProtectedPage>
    );
  }

  if (error || !vehicle) {
    return (
      <ProtectedPage title="Dettaglio Mezzo" description="Errore" breadcrumb="Mezzi" requiredModule="operazioni">
        <div className="py-8 text-center text-sm text-red-600">{error || "Mezzo non trovato"}</div>
      </ProtectedPage>
    );
  }

  return (
    <ProtectedPage title={`Mezzo: ${vehicle.name as string}`} description="Dettaglio mezzo" breadcrumb="Mezzi" requiredModule="operazioni">
      <nav className="mb-4 flex items-center gap-1 text-sm text-gray-500">
        <Link href="/operazioni" className="hover:text-gray-700">Operazioni</Link>
        <ChevronRightIcon className="h-3 w-3" />
        <Link href="/operazioni/mezzi" className="hover:text-gray-700">Mezzi</Link>
        <ChevronRightIcon className="h-3 w-3" />
        <span className="text-gray-800">{vehicle.name as string}</span>
      </nav>

      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">{vehicle.name as string}</h2>
            <p className="mt-1 text-sm text-gray-500">{vehicle.code as string}</p>
          </div>
          <span className={`rounded-full px-3 py-1 text-xs font-medium ${statusColors[vehicle.current_status as string] || "bg-gray-100 text-gray-800"}`}>
            {statusLabels[vehicle.current_status as string] || vehicle.current_status}
          </span>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
          <div>
            <p className="text-gray-500">Targa</p>
            <p className="font-medium text-gray-900">{(vehicle.plate_number as string) || "—"}</p>
          </div>
          <div>
            <p className="text-gray-500">Tipo</p>
            <p className="font-medium text-gray-900">{vehicle.vehicle_type as string}</p>
          </div>
          <div>
            <p className="text-gray-500">Marca/Modello</p>
            <p className="font-medium text-gray-900">{[vehicle.brand, vehicle.model].filter(Boolean).join(" ") || "—"}</p>
          </div>
          <div>
            <p className="text-gray-500">Carburante</p>
            <p className="font-medium text-gray-900">{(vehicle.fuel_type as string) || "—"}</p>
          </div>
          <div>
            <p className="text-gray-500">GPS</p>
            <p className="font-medium text-gray-900">{vehicle.has_gps_device ? "Sì" : "No"}</p>
          </div>
          <div>
            <p className="text-gray-500">Ultimo aggiornamento</p>
            <p className="font-medium text-gray-900">{vehicle.updated_at ? new Date(vehicle.updated_at as string).toLocaleDateString("it-IT") : "—"}</p>
          </div>
        </div>
      </div>

      <div className="mt-6 grid gap-6 sm:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h3 className="text-sm font-semibold text-gray-700">Assegnazioni</h3>
          <p className="mt-2 text-sm text-gray-500">Storico assegnazioni in implementazione.</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h3 className="text-sm font-semibold text-gray-700">Utilizzi recenti</h3>
          <p className="mt-2 text-sm text-gray-500">Lista utilizzi in implementazione.</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h3 className="text-sm font-semibold text-gray-700">Manutenzioni</h3>
          <p className="mt-2 text-sm text-gray-500">Storico manutenzioni in implementazione.</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h3 className="text-sm font-semibold text-gray-700">Carburante</h3>
          <p className="mt-2 text-sm text-gray-500">Storico rifornimenti in implementazione.</p>
        </div>
      </div>
    </ProtectedPage>
  );
}
