"use client";

import { useState, type ChangeEvent } from "react";
import { ProtectedPage } from "@/components/app/protected-page";
import { ElaborazioneHero } from "@/components/elaborazioni/module-chrome";
import { SyncServiceCard } from "@/components/elaborazioni/sync-service-card";
import { SyncDashboardDialog, type SyncDialogTarget } from "@/components/elaborazioni/sync-dashboard-dialog";
import { useSyncDashboard } from "@/components/elaborazioni/use-sync-dashboard";
import { SYNC_SERVICES } from "@/lib/sync-dashboard-services";
import { matchesSyncFilter, syncCounts, type SyncFilter } from "@/lib/sync-dashboard-model";

export default function ElaborazioniPage() {
  const { states, refreshing, refresh } = useSyncDashboard();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<SyncFilter>("all");
  const [target, setTarget] = useState<SyncDialogTarget | null>(null);
  const counts = syncCounts(states);
  const services = SYNC_SERVICES.filter((service) =>
    `${service.title} ${service.description}`.toLocaleLowerCase("it").includes(query.trim().toLocaleLowerCase("it")) && matchesSyncFilter(states[service.id], filter));
  const filters = [{ id: "all", label: "Tutti i servizi", count: SYNC_SERVICES.length },
    { id: "attention", label: "Da verificare", count: counts.attention },
    { id: "active", label: "In corso / in coda", count: counts.active }] as const;
  function openWorkspace(href: string, title: string) { setTarget({ kind: "workspace", href, title }); }
  function handleSearch(event: ChangeEvent<HTMLInputElement>) { setQuery(event.target.value); }
  return (
    <ProtectedPage title="GAIA Elaborazioni" description="Sincronizzazioni, risultati e pianificazioni in un unico posto." breadcrumb="Elaborazioni" requiredModule="catasto">
      <ElaborazioneHero badge="Centro sincronizzazioni" title="Cosa vuoi controllare?"
        description="Scegli un servizio, controlla il risultato e apri il monitor per intervenire. Tutto senza uscire da questa pagina."
        actions={<button type="button" className="btn-secondary" disabled={refreshing} onClick={() => void refresh()}>{refreshing ? "Aggiornamento..." : "Aggiorna ora"}</button>}>
        <div className="flex flex-wrap gap-3">
          <button type="button" className="btn-secondary" aria-haspopup="dialog" onClick={() => setTarget({ kind: "schedules", title: "Pianificazioni automatiche" })}>Pianificazioni automatiche</button>
          <button type="button" className="btn-secondary" aria-haspopup="dialog" onClick={() => openWorkspace("/elaborazioni/settings", "Credenziali e impostazioni")}>Credenziali e impostazioni</button>
          <button type="button" className="btn-secondary" aria-haspopup="dialog" onClick={() => openWorkspace("/elaborazioni/sister", "Richieste e documenti")}>Richieste e documenti</button>
        </div>
      </ElaborazioneHero>
      <section aria-label="Servizi di sincronizzazione" className="space-y-5">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div><h2 className="text-2xl font-semibold text-[#163524]">Servizi di sincronizzazione</h2><p className="mt-1 text-sm text-stone-600">Lo stato si aggiorna ogni 30 secondi. I dettagli mostrano i risultati di ogni flusso.</p></div>
          <label className="w-full text-sm font-medium text-stone-700 sm:w-80">Cerca un servizio
            <input type="search" value={query} onChange={handleSearch} placeholder="Es. presenze, inCass, anagrafiche..." className="mt-2 w-full rounded-xl border border-stone-300 bg-white px-4 py-3 focus:border-[#1D4E35] focus:outline-none focus:ring-2 focus:ring-[#1D4E35]/20" />
          </label>
        </div>
        <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Filtra per stato">
          {filters.map((item) => <button key={item.id} type="button" aria-pressed={filter === item.id} onClick={() => setFilter(item.id)}
            className={`rounded-full border px-4 py-2 text-sm font-semibold transition-colors ${filter === item.id ? "border-[#1D4E35] bg-[#1D4E35] text-white" : "border-stone-200 bg-white text-stone-600 hover:border-[#1D4E35]"}`}>
            {item.label} <span className="ml-2 opacity-80">{item.count}</span>
          </button>)}
          <p role="status" className="text-sm text-stone-500 sm:ml-auto">{services.length} servizi visualizzati</p>
        </div>
        <div className="grid auto-rows-fr items-stretch gap-4 md:grid-cols-2 xl:grid-cols-3">
          {services.map((service) => <SyncServiceCard key={service.id} service={service} state={states[service.id]}
            onDetails={() => setTarget({ kind: "details", title: service.title, service })} onOpen={() => openWorkspace(service.href, service.title)} />)}
        </div>
        {services.length === 0 ? <div className="rounded-2xl border border-dashed border-stone-300 bg-white p-8 text-center">
          <p className="font-semibold text-stone-700">Nessun servizio corrisponde alla ricerca.</p>
          <p className="mt-2 text-sm text-stone-500">Prova un altro nome oppure torna alla panoramica completa.</p>
          <button type="button" className="btn-secondary mt-4" onClick={() => { setQuery(""); setFilter("all"); }}>Mostra tutti i servizi</button>
        </div> : null}
      </section>
      {target ? <SyncDashboardDialog target={target} states={states} onClose={() => setTarget(null)} onOpen={openWorkspace} /> : null}
    </ProtectedPage>
  );
}
