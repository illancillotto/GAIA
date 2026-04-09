"use client";

import { useEffect, useState } from "react";

import {
  OperazioniCollectionHero,
  OperazioniCollectionPanel,
  OperazioniHeroNotice,
  OperazioniList,
  OperazioniListLink,
  OperazioniMetricStrip,
} from "@/components/operazioni/collection-layout";
import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { MetricCard } from "@/components/ui/metric-card";
import { AlertTriangleIcon, RefreshIcon, TruckIcon } from "@/components/ui/icons";

function MiniAppContent() {
  const [isOnline, setIsOnline] = useState(true);

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

  return (
    <div className="page-stack">
      <OperazioniCollectionHero
        eyebrow="Mobile operations"
        icon={<TruckIcon className="h-3.5 w-3.5" />}
        title="Mini-app per operatori sul campo con azioni rapide, bozzature locali e continuità offline."
        description="Questa superficie concentra i task principali dell'operatore e mantiene immediato l'accesso alle bozze locali quando la connettività non è stabile."
      >
        <OperazioniHeroNotice
          title={isOnline ? "Connessione disponibile" : "Modalita offline"}
          description={
            isOnline
              ? "Le nuove operazioni possono essere inviate subito al backend."
              : "Le nuove operazioni devono essere salvate in locale e sincronizzate piu tardi."
          }
          tone={isOnline ? "default" : "danger"}
        />
      </OperazioniCollectionHero>

      <OperazioniMetricStrip>
        <MetricCard label="Azioni rapide" value={4} sub="Ingressi principali per l'operatore" />
        <MetricCard label="Modalita" value={isOnline ? "Online" : "Offline"} sub="Stato connettivita browser" variant={isOnline ? "success" : "warning"} />
        <MetricCard label="Bozze locali" value="IDB" sub="Persistenza offline in IndexedDB" />
      </OperazioniMetricStrip>

      <OperazioniCollectionPanel
        title="Operazioni rapide"
        description="Ingressi principali per il lavoro sul campo, progettati per touch e consultazione rapida."
        count={4}
      >
        <OperazioniList>
          <OperazioniListLink
            href="/operazioni/miniapp/attivita/nuova"
            title="Avvia attività"
            meta="Seleziona e avvia una nuova attività operativa"
            status="Flusso rapido"
            statusTone="bg-sky-50 text-sky-700"
            aside={<RefreshIcon className="h-4 w-4 text-[#1D4E35]" />}
          />
          <OperazioniListLink
            href="/operazioni/miniapp/attivita/chiusura"
            title="Chiudi attività"
            meta="Registra la chiusura dell'attività in corso"
            status="Checklist finale"
            statusTone="bg-amber-50 text-amber-700"
            aside={<TruckIcon className="h-4 w-4 text-[#1D4E35]" />}
          />
          <OperazioniListLink
            href="/operazioni/miniapp/segnalazioni/nuova"
            title="Nuova segnalazione"
            meta="Crea una segnalazione direttamente dal campo"
            status="Report immediato"
            statusTone="bg-rose-50 text-rose-700"
            aside={<AlertTriangleIcon className="h-4 w-4 text-[#1D4E35]" />}
          />
          <OperazioniListLink
            href="/operazioni/miniapp/liste"
            title="Liste personali"
            meta="Attività aperte, segnalazioni inviate e pratiche assegnate"
            status="Workset"
            statusTone="bg-emerald-50 text-emerald-700"
            aside={<TruckIcon className="h-4 w-4 text-[#1D4E35]" />}
          />
        </OperazioniList>
      </OperazioniCollectionPanel>

      <OperazioniCollectionPanel
        title="Accesso rapido"
        description="Link di appoggio per bozze locali e rientro alla dashboard desktop."
        count={2}
      >
        <OperazioniList>
          <OperazioniListLink
            href="/operazioni/miniapp/bozze"
            title="Bozze locali"
            meta="Gestione salvataggi offline e sincronizzazione differita"
            status="Offline queue"
            statusTone="bg-amber-50 text-amber-700"
          />
          <OperazioniListLink
            href="/operazioni"
            title="Dashboard operazioni"
            meta="Torna alla console principale del modulo"
            status="Desktop"
            statusTone="bg-emerald-50 text-emerald-700"
          />
        </OperazioniList>
      </OperazioniCollectionPanel>
    </div>
  );
}

export default function MiniAppPage() {
  return (
    <OperazioniModulePage
      title="Mini-app"
      description="Interfaccia mobile-first per operatori sul campo."
      breadcrumb="Operatori"
    >
      {() => <MiniAppContent />}
    </OperazioniModulePage>
  );
}
