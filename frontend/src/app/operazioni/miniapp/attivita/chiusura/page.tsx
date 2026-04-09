"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  OperazioniBreadcrumb,
  OperazioniCollectionPanel,
  OperazioniDetailHero,
  OperazioniHeroNotice,
  OperazioniList,
  OperazioniListLink,
} from "@/components/operazioni/collection-layout";
import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { RefreshIcon } from "@/components/ui/icons";
import { getActivities, stopActivity } from "@/features/operazioni/api/client";
import { generateDraftId, markDraftPending, saveDraft } from "@/features/operazioni/utils/offline-drafts";

type ActivityItem = {
  id: string;
  started_at: string | null;
};

function ChiudiAttivitaContent({ currentUserId }: { currentUserId: number }) {
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [textNote, setTextNote] = useState("");
  const [submitForReview, setSubmitForReview] = useState(true);
  const [isOnline, setIsOnline] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
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
    async function loadActivities() {
      try {
        const data = await getActivities({ page_size: "50", status: "in_progress", operator_user_id: String(currentUserId) });
        const items = Array.isArray((data as { items?: ActivityItem[] }).items) ? ((data as { items: ActivityItem[] }).items) : [];
        setActivities(items);
        if (items[0]) setSelectedId(items[0].id);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento attività in corso");
      } finally {
        setIsLoading(false);
      }
    }
    void loadActivities();
  }, [currentUserId]);

  async function saveOfflineDraft() {
    const draftId = generateDraftId();
    await saveDraft({
      id: draftId,
      type: "activity",
      data: { activity_id: selectedId, ended_at: new Date().toISOString(), text_note: textNote || null, submit_for_review: submitForReview, action: "stop" },
    });
    await markDraftPending(draftId);
    setFeedback("Chiusura attività salvata come bozza locale.");
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setFeedback(null);
    if (!selectedId) {
      setError("Seleziona un'attività da chiudere.");
      return;
    }
    if (!isOnline) {
      await saveOfflineDraft();
      return;
    }
    try {
      setIsSubmitting(true);
      await stopActivity(selectedId, { ended_at: new Date().toISOString(), text_note: textNote || null, submit_for_review: submitForReview });
      setFeedback("Attività chiusa correttamente.");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Errore chiusura attività");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="page-stack">
      <OperazioniBreadcrumb items={[{ label: "Operazioni", href: "/operazioni" }, { label: "Mini-app", href: "/operazioni/miniapp" }, { label: "Chiudi attività" }]} />
      <OperazioniDetailHero eyebrow="Quick stop" title="Chiusura attività in corso" description="Seleziona una delle attività ancora aperte e registra la chiusura con nota finale e invio in revisione." status={isOnline ? "Online" : "Offline"} statusTone={isOnline ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}>
        <OperazioniHeroNotice title="Stato coda" description={isOnline ? "La chiusura verrà inviata subito al backend." : "La chiusura verrà salvata come bozza locale in attesa di sincronizzazione."} />
      </OperazioniDetailHero>
      <OperazioniCollectionPanel title="Attività aperte" description="Elenco delle attività in corso filtrate per operatore corrente." count={activities.length}>
        {isLoading ? (
          <p className="text-sm text-gray-500">Caricamento attività in corso.</p>
        ) : activities.length === 0 ? (
          <EmptyState icon={RefreshIcon} title="Nessuna attività in corso" description="Non risultano attività aperte da chiudere per questo operatore." />
        ) : (
          <OperazioniList>
            {activities.map((activity) => (
              <OperazioniListLink
                key={activity.id}
                onClick={() => setSelectedId(activity.id)}
                title={`Attività ${activity.id.slice(0, 8)}…`}
                meta={activity.started_at ? `Avviata il ${new Date(activity.started_at).toLocaleString("it-IT")}` : "Data avvio non disponibile"}
                status={selectedId === activity.id ? "Selezionata" : "Disponibile"}
                statusTone={selectedId === activity.id ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-600"}
              />
            ))}
          </OperazioniList>
        )}
      </OperazioniCollectionPanel>
      <OperazioniCollectionPanel title="Conferma chiusura" description="Nota finale e scelta di invio in revisione o salvataggio come bozza." count={selectedId ? 1 : 0}>
        <form className="grid gap-4" onSubmit={(event) => void handleSubmit(event)}>
          <label className="block">
            <span className="label-caption">Nota finale</span>
            <textarea className="form-control mt-2 min-h-28" value={textNote} onChange={(event) => setTextNote(event.target.value)} placeholder="Descrivi l'esito dell'attività" />
          </label>
          <label className="flex items-center gap-3 rounded-2xl border border-[#e6ebe5] bg-[#fbfcfa] px-4 py-3 text-sm text-gray-700">
            <input type="checkbox" checked={submitForReview} onChange={(event) => setSubmitForReview(event.target.checked)} />
            Invia per revisione al termine della chiusura
          </label>
          {error ? <p className="text-sm text-red-700">{error}</p> : null}
          {feedback ? <p className="text-sm text-emerald-700">{feedback}</p> : null}
          <div className="flex flex-wrap gap-3">
            <button type="submit" className="btn-primary" disabled={isSubmitting || !selectedId}>
              {isSubmitting ? "Invio..." : isOnline ? "Chiudi attività" : "Salva bozza offline"}
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

export default function MiniAppChiudiAttivitaPage() {
  return (
    <OperazioniModulePage title="Chiudi attività" description="Chiusura rapida delle attività in corso dalla mini-app." breadcrumb="Mini-app">
      {({ currentUser }) => <ChiudiAttivitaContent currentUserId={currentUser.id} />}
    </OperazioniModulePage>
  );
}
