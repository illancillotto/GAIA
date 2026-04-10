"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  OperazioniCollectionPanel,
  OperazioniList,
  OperazioniListLink,
} from "@/components/operazioni/collection-layout";
import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { OperazioniWorkspaceModal } from "@/components/operazioni/workspace-modal";
import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { EmptyState } from "@/components/ui/empty-state";
import { TruckIcon, RefreshIcon, AlertTriangleIcon, DocumentIcon, SearchIcon } from "@/components/ui/icons";
import { getVehicles, getActivities, getReports, getCases } from "@/features/operazioni/api/client";

const vehicleStatusTone: Record<string, string> = {
  available: "bg-emerald-50 text-emerald-700",
  assigned: "bg-sky-50 text-sky-700",
  in_use: "bg-amber-50 text-amber-700",
  maintenance: "bg-rose-50 text-rose-700",
  out_of_service: "bg-gray-100 text-gray-600",
};

const vehicleStatusLabels: Record<string, string> = {
  available: "Disponibile",
  assigned: "Assegnato",
  in_use: "In utilizzo",
  maintenance: "Manutenzione",
  out_of_service: "Fuori servizio",
};

const activityStatusTone: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600",
  in_progress: "bg-sky-50 text-sky-700",
  submitted: "bg-amber-50 text-amber-700",
  under_review: "bg-purple-50 text-purple-700",
  approved: "bg-emerald-50 text-emerald-700",
  rejected: "bg-rose-50 text-rose-700",
};

const activityStatusLabels: Record<string, string> = {
  draft: "Bozza",
  in_progress: "In corso",
  submitted: "Inviata",
  under_review: "In revisione",
  approved: "Approvata",
  rejected: "Respinta",
};

const caseStatusTone: Record<string, string> = {
  open: "bg-sky-50 text-sky-700",
  assigned: "bg-indigo-50 text-indigo-700",
  acknowledged: "bg-purple-50 text-purple-700",
  in_progress: "bg-amber-50 text-amber-700",
  resolved: "bg-emerald-50 text-emerald-700",
  closed: "bg-gray-100 text-gray-600",
  cancelled: "bg-rose-50 text-rose-700",
  reopened: "bg-orange-50 text-orange-700",
};

const caseStatusLabels: Record<string, string> = {
  open: "Aperta",
  assigned: "Assegnata",
  acknowledged: "Presa in carico",
  in_progress: "In lavorazione",
  resolved: "Risolto",
  closed: "Chiusa",
  cancelled: "Annullata",
  reopened: "Riaperta",
};

type WorkspaceModalState = {
  href: string;
  title: string;
  description: string;
} | null;

function DashboardContent() {
  const [workspaceModal, setWorkspaceModal] = useState<WorkspaceModalState>(null);
  const [vehicles, setVehicles] = useState<Record<string, unknown>[]>([]);
  const [activities, setActivities] = useState<Record<string, unknown>[]>([]);
  const [reports, setReports] = useState<Record<string, unknown>[]>([]);
  const [cases, setCases] = useState<Record<string, unknown>[]>([]);
  const [totals, setTotals] = useState({ vehicles: 0, activities: 0, reports: 0, cases: 0 });
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  function listTotal(payload: { items?: unknown[]; total?: number }): number {
    if (typeof payload.total === "number") {
      return payload.total;
    }
    return payload.items?.length ?? 0;
  }

  const loadData = useCallback(async () => {
    try {
      const [vData, aData, rData, cData] = await Promise.all([
        getVehicles({ page_size: "5" }),
        getActivities({ page_size: "5" }),
        getReports({ page_size: "5" }),
        getCases({ page_size: "5" }),
      ]);
      setVehicles(vData.items ?? []);
      setActivities(aData.items ?? []);
      setReports(rData.items ?? []);
      setCases(cData.items ?? []);
      setTotals({
        vehicles: listTotal(vData),
        activities: listTotal(aData),
        reports: listTotal(rData),
        cases: listTotal(cData),
      });
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore nel caricamento dati");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  return (
    <div className="page-stack">
      <ModuleWorkspaceHero
        badge={
          <>
            <TruckIcon className="h-3.5 w-3.5" />
            Workspace Operazioni
          </>
        }
        title="Console operativa per mezzi, attività sul campo, segnalazioni e pratiche interne."
        description="Qui restano concentrati elenchi recenti, accesso rapido alle mini-app e alle viste elenco complete del modulo."
        actions={
          <>
            {loadError ? (
              <ModuleWorkspaceNoticeCard title="Caricamento non riuscito" description={loadError} tone="danger" />
            ) : (
              <ModuleWorkspaceNoticeCard
                title="Dati di sintesi"
                description="I conteggi riflettono i totali restituiti dalle API; le tabelle sotto mostrano le ultime righe caricate."
              />
            )}
            <div className="flex flex-wrap gap-2">
              <Link className="btn-secondary" href="/operazioni/attivita">
                <RefreshIcon className="h-4 w-4" />
                Apri attività
              </Link>
              <Link className="btn-primary" href="/operazioni/mezzi">
                <TruckIcon className="h-4 w-4" />
                Apri mezzi
              </Link>
            </div>
          </>
        }
      >
        <ModuleWorkspaceKpiRow>
          <ModuleWorkspaceKpiTile label="Mezzi" variant="emerald" value={totals.vehicles} hint="registrati nel modulo" />
          <ModuleWorkspaceKpiTile label="Attività" value={totals.activities} hint="workflow operatori" />
          <ModuleWorkspaceKpiTile label="Segnalazioni" value={totals.reports} hint="dal campo" />
          <ModuleWorkspaceKpiTile label="Pratiche" variant="amber" value={totals.cases} hint="case nel modulo" />
        </ModuleWorkspaceKpiRow>
      </ModuleWorkspaceHero>

      <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
        <div className="border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(29,78,53,0.06),_rgba(255,255,255,0.92))] px-6 py-5">
          <div className="inline-flex items-center gap-2 rounded-full bg-[#e8f2ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
            <TruckIcon className="h-3.5 w-3.5" />
            Accesso rapido
          </div>
          <p className="mt-3 text-lg font-semibold text-gray-900">Strumenti per il personale sul campo</p>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-600">
            Mini-app mobile-first, monitoraggio quota storage e sincronizzazione bozze offline.
          </p>
        </div>
        <div className="p-6">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            <Link
              href="/operazioni/miniapp"
              className="group rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-left transition hover:border-[#c8d8ce] hover:bg-white"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white text-[#1D4E35] shadow-sm ring-1 ring-[#dfe8e2] transition group-hover:bg-[#edf5f0]">
                  <TruckIcon className="h-[18px] w-[18px]" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900">Mini-app operatori</p>
                  <p className="mt-0.5 line-clamp-2 text-xs leading-5 text-gray-500">Interfaccia mobile-first per avvio e chiusura attività sul campo.</p>
                </div>
              </div>
            </Link>
            <Link
              href="/operazioni/storage"
              className="group rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-left transition hover:border-[#c8d8ce] hover:bg-white"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white text-[#1D4E35] shadow-sm ring-1 ring-[#dfe8e2] transition group-hover:bg-[#edf5f0]">
                  <SearchIcon className="h-[18px] w-[18px]" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900">Storage allegati</p>
                  <p className="mt-0.5 line-clamp-2 text-xs leading-5 text-gray-500">Quota, utilizzo e alert sulle soglie di archiviazione.</p>
                </div>
              </div>
            </Link>
            <Link
              href="/operazioni/miniapp/bozze"
              className="group rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-left transition hover:border-[#c8d8ce] hover:bg-white"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white text-[#1D4E35] shadow-sm ring-1 ring-[#dfe8e2] transition group-hover:bg-[#edf5f0]">
                  <DocumentIcon className="h-[18px] w-[18px]" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900">Bozze locali</p>
                  <p className="mt-0.5 line-clamp-2 text-xs leading-5 text-gray-500">Sincronizzazione con il backend quando torna la connettività.</p>
                </div>
              </div>
            </Link>
          </div>
        </div>
      </article>

      <div className="grid gap-6 xl:grid-cols-2">
        <div
          className="panel-card group cursor-pointer transition hover:border-[#c8d8ce] hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1D4E35]/25"
          tabIndex={0}
          aria-label="Mezzi recenti: apri la gestione in modale"
          onClick={() =>
            setWorkspaceModal({
              href: "/operazioni/mezzi",
              title: "Gestione mezzi",
              description: "Anagrafica, filtri e collegamenti alle schede veicolo senza uscire dalla dashboard.",
            })
          }
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              setWorkspaceModal({
                href: "/operazioni/mezzi",
                title: "Gestione mezzi",
                description: "Anagrafica, filtri e collegamenti alle schede veicolo senza uscire dalla dashboard.",
              });
            }
          }}
        >
          <OperazioniCollectionPanel
            title="Mezzi recenti"
            description="Clic sulla scheda per la lista completa; clic su una riga per il dettaglio."
            count={vehicles.length}
          >
            {isLoading ? (
              <p className="text-sm text-gray-500">Caricamento mezzi in corso.</p>
            ) : vehicles.length === 0 ? (
              <EmptyState
                icon={TruckIcon}
                title="Nessun mezzo registrato"
                description="Nessun veicolo corrisponde ai filtri correnti."
              />
            ) : (
              <div className="max-h-[28rem] overflow-y-auto pr-1">
                <OperazioniList>
                  {vehicles.map((vehicle) => (
                    <OperazioniListLink
                      key={String(vehicle.id)}
                      onClick={() => {
                        setWorkspaceModal({
                          href: `/operazioni/mezzi/${String(vehicle.id)}`,
                          title: String(vehicle.name),
                          description: `Scheda veicolo · ${String(vehicle.code ?? vehicle.id)}${vehicle.plate_number ? ` · ${vehicle.plate_number}` : ""}`,
                        });
                      }}
                      title={String(vehicle.name)}
                      meta={`${String(vehicle.code ?? "")}${vehicle.plate_number ? ` · ${vehicle.plate_number}` : ""}`}
                      status={vehicleStatusLabels[String(vehicle.current_status)] || String(vehicle.current_status)}
                      statusTone={vehicleStatusTone[String(vehicle.current_status)] || "bg-gray-100 text-gray-600"}
                    />
                  ))}
                </OperazioniList>
              </div>
            )}
          </OperazioniCollectionPanel>
        </div>

        <div
          className="panel-card group cursor-pointer transition hover:border-[#c8d8ce] hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1D4E35]/25"
          tabIndex={0}
          aria-label="Attività recenti: apri la gestione in modale"
          onClick={() =>
            setWorkspaceModal({
              href: "/operazioni/attivita",
              title: "Attività operatori",
              description: "Elenco e avvio attività in modale, con contesto dashboard preservato.",
            })
          }
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              setWorkspaceModal({
                href: "/operazioni/attivita",
                title: "Attività operatori",
                description: "Elenco e avvio attività in modale, con contesto dashboard preservato.",
              });
            }
          }}
        >
          <OperazioniCollectionPanel
            title="Attività recenti"
            description="Clic sulla scheda per la lista completa; clic su una riga per il dettaglio."
            count={activities.length}
          >
            {isLoading ? (
              <p className="text-sm text-gray-500">Caricamento attività in corso.</p>
            ) : activities.length === 0 ? (
              <EmptyState
                icon={RefreshIcon}
                title="Nessuna attività registrata"
                description="Nessuna attività corrisponde ai filtri correnti."
              />
            ) : (
              <div className="max-h-[28rem] overflow-y-auto pr-1">
                <OperazioniList>
                  {activities.map((activity) => (
                    <OperazioniListLink
                      key={String(activity.id)}
                      onClick={() => {
                        setWorkspaceModal({
                          href: `/operazioni/attivita/${String(activity.id)}`,
                          title: `Attività ${String(activity.id).substring(0, 8)}…`,
                          description: "Dettaglio attività operatore in modale.",
                        });
                      }}
                      title={`Attività ${String(activity.id).substring(0, 8)}…`}
                      meta={`Operatore ID ${String(activity.operator_user_id ?? "—")}${activity.started_at ? ` · ${new Date(activity.started_at as string).toLocaleDateString("it-IT")}` : ""}`}
                      status={activityStatusLabels[String(activity.status)] || String(activity.status)}
                      statusTone={activityStatusTone[String(activity.status)] || "bg-gray-100 text-gray-600"}
                    />
                  ))}
                </OperazioniList>
              </div>
            )}
          </OperazioniCollectionPanel>
        </div>

        <div
          className="panel-card group cursor-pointer transition hover:border-[#c8d8ce] hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1D4E35]/25"
          tabIndex={0}
          aria-label="Segnalazioni recenti: apri la gestione in modale"
          onClick={() =>
            setWorkspaceModal({
              href: "/operazioni/segnalazioni",
              title: "Segnalazioni",
              description: "Segnalazioni dal campo e stato collegamento alle pratiche interne.",
            })
          }
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              setWorkspaceModal({
                href: "/operazioni/segnalazioni",
                title: "Segnalazioni",
                description: "Segnalazioni dal campo e stato collegamento alle pratiche interne.",
              });
            }
          }}
        >
          <OperazioniCollectionPanel
            title="Segnalazioni recenti"
            description="Clic sulla scheda per la lista completa; clic su una riga per il dettaglio."
            count={reports.length}
          >
            {isLoading ? (
              <p className="text-sm text-gray-500">Caricamento segnalazioni in corso.</p>
            ) : reports.length === 0 ? (
              <EmptyState
                icon={AlertTriangleIcon}
                title="Nessuna segnalazione"
                description="Non risultano segnalazioni registrate."
              />
            ) : (
              <div className="max-h-[28rem] overflow-y-auto pr-1">
                <OperazioniList>
                  {reports.map((report) => (
                    <OperazioniListLink
                      key={String(report.id)}
                      onClick={() => {
                        setWorkspaceModal({
                          href: `/operazioni/segnalazioni/${String(report.id)}`,
                          title: String(report.title ?? "Segnalazione"),
                          description: report.report_number
                            ? `Segnalazione ${String(report.report_number)}`
                            : "Dettaglio segnalazione in modale.",
                        });
                      }}
                      title={String(report.title ?? "Senza titolo")}
                      meta={`${String(report.report_number ?? "")}${report.created_at ? ` · ${new Date(report.created_at as string).toLocaleDateString("it-IT")}` : ""}`}
                      status={report.internal_case_id ? "Con pratica" : "Senza pratica"}
                      statusTone={report.internal_case_id ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}
                    />
                  ))}
                </OperazioniList>
              </div>
            )}
          </OperazioniCollectionPanel>
        </div>

        <div
          className="panel-card group cursor-pointer transition hover:border-[#c8d8ce] hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1D4E35]/25"
          tabIndex={0}
          aria-label="Pratiche recenti: apri la gestione in modale"
          onClick={() =>
            setWorkspaceModal({
              href: "/operazioni/pratiche",
              title: "Pratiche interne",
              description: "Workflow pratiche, stati e assegnazioni in vista modale.",
            })
          }
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              setWorkspaceModal({
                href: "/operazioni/pratiche",
                title: "Pratiche interne",
                description: "Workflow pratiche, stati e assegnazioni in vista modale.",
              });
            }
          }}
        >
          <OperazioniCollectionPanel
            title="Pratiche recenti"
            description="Clic sulla scheda per la lista completa; clic su una riga per il dettaglio."
            count={cases.length}
          >
            {isLoading ? (
              <p className="text-sm text-gray-500">Caricamento pratiche in corso.</p>
            ) : cases.length === 0 ? (
              <EmptyState
                icon={DocumentIcon}
                title="Nessuna pratica"
                description="Non risultano pratiche registrate."
              />
            ) : (
              <div className="max-h-[28rem] overflow-y-auto pr-1">
                <OperazioniList>
                  {cases.map((caseItem) => (
                    <OperazioniListLink
                      key={String(caseItem.id)}
                      onClick={() => {
                        setWorkspaceModal({
                          href: `/operazioni/pratiche/${String(caseItem.id)}`,
                          title: String(caseItem.title ?? "Pratica"),
                          description: caseItem.case_number
                            ? `Pratica ${String(caseItem.case_number)}`
                            : "Dettaglio pratica in modale.",
                        });
                      }}
                      title={String(caseItem.title ?? "Senza titolo")}
                      meta={`${String(caseItem.case_number ?? "")}${caseItem.created_at ? ` · ${new Date(caseItem.created_at as string).toLocaleDateString("it-IT")}` : ""}`}
                      status={caseStatusLabels[String(caseItem.status)] || String(caseItem.status)}
                      statusTone={caseStatusTone[String(caseItem.status)] || "bg-gray-100 text-gray-600"}
                    />
                  ))}
                </OperazioniList>
              </div>
            )}
          </OperazioniCollectionPanel>
        </div>
      </div>

      <OperazioniWorkspaceModal
        description={workspaceModal?.description}
        href={workspaceModal?.href ?? null}
        onClose={() => setWorkspaceModal(null)}
        open={workspaceModal != null}
        title={workspaceModal?.title ?? "Workspace"}
      />
    </div>
  );
}

export default function OperazioniDashboardPage() {
  return (
    <OperazioniModulePage
      title="Dashboard"
      description="Vista operativa di mezzi, attività, segnalazioni dal campo e pratiche interne."
    >
      {() => <DashboardContent />}
    </OperazioniModulePage>
  );
}
