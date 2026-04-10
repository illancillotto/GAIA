"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  OperazioniBreadcrumb,
  OperazioniCollectionPanel,
  OperazioniDetailHero,
  OperazioniHeroNotice,
} from "@/components/operazioni/collection-layout";
import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { createReport, getReportCategories, getReportSeverities, getTeams, getVehicles } from "@/features/operazioni/api/client";
import { generateDraftId, markDraftPending, saveDraft } from "@/features/operazioni/utils/offline-drafts";

type LookupItem = { id: string; code?: string; name?: string };

function NuovaSegnalazioneContent() {
  const [categories, setCategories] = useState<LookupItem[]>([]);
  const [severities, setSeverities] = useState<LookupItem[]>([]);
  const [teams, setTeams] = useState<LookupItem[]>([]);
  const [vehicles, setVehicles] = useState<LookupItem[]>([]);
  const [categoryId, setCategoryId] = useState("");
  const [severityId, setSeverityId] = useState("");
  const [teamId, setTeamId] = useState("");
  const [vehicleId, setVehicleId] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
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
        const [categoryData, severityData, teamsData, vehiclesData] = await Promise.all([
          getReportCategories(),
          getReportSeverities(),
          getTeams().catch(() => []),
          getVehicles({ page_size: "100" }).catch(() => ({ items: [] })),
        ]);
        setCategories(Array.isArray(categoryData) ? (categoryData as LookupItem[]) : []);
        setSeverities(Array.isArray(severityData) ? (severityData as LookupItem[]) : []);
        setTeams(Array.isArray(teamsData) ? (teamsData as LookupItem[]) : []);
        setVehicles(Array.isArray((vehiclesData as { items?: LookupItem[] }).items) ? ((vehiclesData as { items: LookupItem[] }).items) : []);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento lookup");
      }
    }
    void loadLookups();
  }, []);

  async function saveOfflineDraft() {
    const draftId = generateDraftId();
    await saveDraft({
      id: draftId,
      type: "report",
      data: { category_id: categoryId, severity_id: severityId, team_id: teamId || null, vehicle_id: vehicleId || null, title, description: description || null },
    });
    await markDraftPending(draftId);
    setFeedback("Segnalazione salvata in bozza locale e marcata per sincronizzazione.");
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setFeedback(null);
    if (!categoryId || !severityId || !title.trim()) {
      setError("Compila categoria, gravità e titolo.");
      return;
    }
    if (!isOnline) {
      await saveOfflineDraft();
      return;
    }
    try {
      setIsSubmitting(true);
      const response = await createReport({ category_id: categoryId, severity_id: severityId, team_id: teamId || null, vehicle_id: vehicleId || null, title: title.trim(), description: description.trim() || null });
      const reportNumber = String(((response as { report?: { report_number?: string } }).report?.report_number) ?? "");
      setFeedback(`Segnalazione creata ${reportNumber}.`);
      setCategoryId("");
      setSeverityId("");
      setTeamId("");
      setVehicleId("");
      setTitle("");
      setDescription("");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Errore creazione segnalazione");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="page-stack">
      <OperazioniBreadcrumb items={[{ label: "Operazioni", href: "/operazioni" }, { label: "Mini-app", href: "/operazioni/miniapp" }, { label: "Nuova segnalazione" }]} />
      <OperazioniDetailHero eyebrow="Field report" title="Nuova segnalazione dal campo" description="Crea una segnalazione con il minimo set di metadati per generare subito la pratica interna o salvarla offline." status={isOnline ? "Online" : "Offline"} statusTone={isOnline ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}>
        <OperazioniHeroNotice title="Esito atteso" description={isOnline ? "La segnalazione genera subito la pratica interna correlata." : "La segnalazione verra salvata come bozza locale in attesa di sincronizzazione."} />
      </OperazioniDetailHero>
      <OperazioniCollectionPanel title="Nuova segnalazione" description="Categoria, gravità, contesto operativo e descrizione sintetica del problema." count={categories.length}>
        <form className="grid gap-4" onSubmit={(event) => void handleSubmit(event)}>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block">
              <span className="label-caption">Categoria</span>
              <select className="form-control mt-2" value={categoryId} onChange={(event) => setCategoryId(event.target.value)}>
                <option value="">Seleziona categoria</option>
                {categories.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name ?? item.code ?? item.id}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="label-caption">Gravità</span>
              <select className="form-control mt-2" value={severityId} onChange={(event) => setSeverityId(event.target.value)}>
                <option value="">Seleziona gravità</option>
                {severities.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name ?? item.code ?? item.id}
                  </option>
                ))}
              </select>
            </label>
          </div>
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
            <span className="label-caption">Titolo</span>
            <input className="form-control mt-2" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Titolo segnalazione" />
          </label>
          <label className="block">
            <span className="label-caption">Descrizione</span>
            <textarea className="form-control mt-2 min-h-32" value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Descrivi il problema rilevato sul campo" />
          </label>
          {error ? <p className="text-sm text-red-700">{error}</p> : null}
          {feedback ? <p className="text-sm text-emerald-700">{feedback}</p> : null}
          <div className="flex flex-wrap gap-3">
            <button type="submit" className="btn-primary" disabled={isSubmitting}>
              {isSubmitting ? "Invio..." : isOnline ? "Invia segnalazione" : "Salva bozza offline"}
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

export default function MiniAppNuovaSegnalazionePage() {
  return (
    <OperazioniModulePage title="Nuova segnalazione" description="Creazione rapida di una segnalazione dal campo." breadcrumb="Mini-app">
      {() => <NuovaSegnalazioneContent />}
    </OperazioniModulePage>
  );
}
