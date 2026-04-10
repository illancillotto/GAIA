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
        <OperazioniCollectionPanel title="Carburante" description="Storico rifornimenti registrati." count={0}>
          <div className="rounded-2xl border border-dashed border-[#d8dfd8] bg-[#f8faf8] p-6 text-sm text-gray-500">Storico carburante in implementazione.</div>
        </OperazioniCollectionPanel>
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
