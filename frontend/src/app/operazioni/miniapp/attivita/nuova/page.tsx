"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  OperazioniBreadcrumb,
  OperazioniCollectionPanel,
  OperazioniDetailHero,
  OperazioniHeroNotice,
} from "@/components/operazioni/collection-layout";
import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { getActivityCatalog, getTeams, getVehicles, startActivity } from "@/features/operazioni/api/client";
import { generateDraftId, markDraftPending, saveDraft } from "@/features/operazioni/utils/offline-drafts";

type CatalogItem = {
  id: string;
  code: string;
  name: string;
  category: string | null;
  requires_vehicle: boolean;
  requires_note: boolean;
};

type LookupItem = { id: string; code?: string; name?: string };

function NuovaAttivitaContent({ currentUserId }: { currentUserId: number }) {
  const [catalog, setCatalog] = useState<CatalogItem[]>([]);
  const [teams, setTeams] = useState<LookupItem[]>([]);
  const [vehicles, setVehicles] = useState<LookupItem[]>([]);
  const [activityCatalogId, setActivityCatalogId] = useState("");
  const [teamId, setTeamId] = useState("");
  const [vehicleId, setVehicleId] = useState("");
  const [textNote, setTextNote] = useState("");
  const [isOnline, setIsOnline] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const syncStatus = () => setIsOnline(window.navigator.onLine);
    syncStatus();
    window.addEventListener("online", syncStatus);
    window.addEventListener("offline", syncStatus);
    return () => {
      window.removeEventListener("online", syncStatus);
      window.removeEventListener("offline", syncStatus);
    };
  }, []);

  useEffect(() => {
    async function loadLookups() {
      try {
        const [catalogData, teamsData, vehiclesData] = await Promise.all([
          getActivityCatalog(),
          getTeams().catch(() => []),
          getVehicles({ page_size: "100" }).catch(() => ({ items: [] })),
        ]);
        setCatalog(Array.isArray(catalogData) ? (catalogData as CatalogItem[]) : []);
        setTeams(Array.isArray(teamsData) ? (teamsData as LookupItem[]) : []);
        setVehicles(Array.isArray((vehiclesData as { items?: LookupItem[] }).items) ? ((vehiclesData as { items: LookupItem[] }).items) : []);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento lookup");
      }
    }
    void loadLookups();
  }, []);

  const selectedCatalog = useMemo(() => catalog.find((item) => item.id === activityCatalogId) ?? null, [activityCatalogId, catalog]);

  async function saveOfflineDraft() {
    const draftId = generateDraftId();
    await saveDraft({
      id: draftId,
      type: "activity",
      data: {
        activity_catalog_id: activityCatalogId,
        operator_user_id: currentUserId,
        team_id: teamId || null,
        vehicle_id: vehicleId || null,
        text_note: textNote || null,
        started_at: new Date().toISOString(),
      },
    });
    await markDraftPending(draftId);
    setFeedback("Attività salvata in bozza locale e marcata per sincronizzazione.");
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setFeedback(null);

    if (!activityCatalogId) {
      setError("Seleziona un'attività.");
      return;
    }
    if (selectedCatalog?.requires_vehicle && !vehicleId) {
      setError("Questa attività richiede un mezzo.");
      return;
    }
    if (selectedCatalog?.requires_note && !textNote.trim()) {
      setError("Questa attività richiede una nota.");
      return;
    }

    if (!isOnline) {
      await saveOfflineDraft();
      return;
    }

    try {
      setIsSubmitting(true);
      const response = await startActivity({
        activity_catalog_id: activityCatalogId,
        operator_user_id: currentUserId,
        team_id: teamId || null,
        vehicle_id: vehicleId || null,
        text_note: textNote || null,
        started_at: new Date().toISOString(),
      });
      setFeedback(`Attività avviata con ID ${String((response as { id?: string }).id ?? "")}.`);
      setActivityCatalogId("");
      setTeamId("");
      setVehicleId("");
      setTextNote("");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Errore avvio attività");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="page-stack">
      <OperazioniBreadcrumb
        items={[
          { label: "Operazioni", href: "/operazioni" },
          { label: "Mini-app", href: "/operazioni/miniapp" },
          { label: "Avvia attività" },
        ]}
      />
      <OperazioniDetailHero
        eyebrow="Quick start"
        title="Avvio attività dal campo"
        description="Compila il minimo necessario per aprire una nuova attività o salvarla in locale quando sei offline."
        status={isOnline ? "Online" : "Offline"}
        statusTone={isOnline ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}
      >
        <OperazioniHeroNotice
          title="Comportamento invio"
          description={isOnline ? "L'attività viene inviata subito al backend." : "L'attività verra salvata come bozza locale in attesa di sincronizzazione."}
        />
      </OperazioniDetailHero>
      <OperazioniCollectionPanel title="Nuova attività" description="Catalogo, team, mezzo e nota iniziale in un form adatto all'uso operativo." count={catalog.length}>
        <form className="grid gap-4" onSubmit={(event) => void handleSubmit(event)}>
          <label className="block">
            <span className="label-caption">Attività</span>
            <select className="form-control mt-2" value={activityCatalogId} onChange={(event) => setActivityCatalogId(event.target.value)}>
              <option value="">Seleziona attività</option>
              {catalog.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}{item.category ? ` · ${item.category}` : ""}
                </option>
              ))}
            </select>
          </label>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block">
              <span className="label-caption">Team</span>
              <select className="form-control mt-2" value={teamId} onChange={(event) => setTeamId(event.target.value)}>
                <option value="">Nessun team</option>
                {teams.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name ?? item.code ?? item.id}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="label-caption">Mezzo</span>
              <select className="form-control mt-2" value={vehicleId} onChange={(event) => setVehicleId(event.target.value)}>
                <option value="">Nessun mezzo</option>
                {vehicles.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name ?? item.code ?? item.id}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label className="block">
            <span className="label-caption">Nota iniziale</span>
            <textarea className="form-control mt-2 min-h-28" value={textNote} onChange={(event) => setTextNote(event.target.value)} placeholder="Descrivi il contesto iniziale dell'attività" />
          </label>
          {error ? <p className="text-sm text-red-700">{error}</p> : null}
          {feedback ? <p className="text-sm text-emerald-700">{feedback}</p> : null}
          <div className="flex flex-wrap gap-3">
            <button type="submit" className="btn-primary" disabled={isSubmitting}>
              {isSubmitting ? "Invio..." : isOnline ? "Avvia attività" : "Salva bozza offline"}
            </button>
            <Link href="/operazioni/miniapp/bozze" className="btn-secondary">
              Apri bozze locali
            </Link>
          </div>
        </form>
      </OperazioniCollectionPanel>
    </div>
  );
}

export default function MiniAppNuovaAttivitaPage() {
  return (
    <OperazioniModulePage title="Avvia attività" description="Creazione rapida di una nuova attività operativa da mini-app." breadcrumb="Mini-app">
      {({ currentUser }) => <NuovaAttivitaContent currentUserId={currentUser.id} />}
    </OperazioniModulePage>
  );
}
