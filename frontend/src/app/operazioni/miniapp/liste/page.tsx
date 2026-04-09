"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  OperazioniBreadcrumb,
  OperazioniCollectionPanel,
  OperazioniDetailHero,
  OperazioniHeroNotice,
  OperazioniList,
  OperazioniListLink,
  OperazioniMetricStrip,
  OperazioniToolbar,
} from "@/components/operazioni/collection-layout";
import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertTriangleIcon, DocumentIcon, RefreshIcon } from "@/components/ui/icons";
import { MetricCard } from "@/components/ui/metric-card";
import { getActivities, getCases, getReports } from "@/features/operazioni/api/client";

type ActivityItem = {
  id: string;
  status?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
};

type ReportItem = {
  id: string;
  title?: string | null;
  report_number?: string | null;
  status?: string | null;
  created_at?: string | null;
};

type CaseItem = {
  id: string;
  case_number?: string | null;
  title?: string | null;
  status?: string | null;
  created_at?: string | null;
};

const activityStatusLabels: Record<string, string> = {
  in_progress: "In corso",
  submitted: "In revisione",
  approved: "Approvata",
  rejected: "Respinta",
};

const caseStatusLabels: Record<string, string> = {
  open: "Aperta",
  assigned: "Assegnata",
  acknowledged: "Presa in carico",
  in_progress: "In lavorazione",
  resolved: "Risolta",
  closed: "Chiusa",
};

function ListePersonaliContent({ currentUserId }: { currentUserId: number }) {
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [isOnline, setIsOnline] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [focus, setFocus] = useState("");

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

  const loadData = useCallback(async () => {
    try {
      setError(null);
      const [activitiesData, reportsData, casesData] = await Promise.all([
        getActivities({ page_size: "6", operator_user_id: String(currentUserId), status: "in_progress" }),
        getReports({ page_size: "6", reporter_user_id: String(currentUserId) }),
        getCases({ page_size: "6", assigned_to_user_id: String(currentUserId) }),
      ]);
      setActivities(Array.isArray((activitiesData as { items?: ActivityItem[] }).items) ? (activitiesData as { items: ActivityItem[] }).items : []);
      setReports(Array.isArray((reportsData as { items?: ReportItem[] }).items) ? (reportsData as { items: ReportItem[] }).items : []);
      setCases(Array.isArray((casesData as { items?: CaseItem[] }).items) ? (casesData as { items: CaseItem[] }).items : []);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento liste personali");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [currentUserId]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const normalizedSearch = search.trim().toLowerCase();

  const filteredActivities = useMemo(() => {
    if (!normalizedSearch) {
      return activities;
    }
    return activities.filter((activity) =>
      [activity.id, activity.status, activity.started_at]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(normalizedSearch)),
    );
  }, [activities, normalizedSearch]);

  const filteredReports = useMemo(() => {
    if (!normalizedSearch) {
      return reports;
    }
    return reports.filter((report) =>
      [report.id, report.title, report.report_number, report.status]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(normalizedSearch)),
    );
  }, [reports, normalizedSearch]);

  const filteredCases = useMemo(() => {
    if (!normalizedSearch) {
      return cases;
    }
    return cases.filter((item) =>
      [item.id, item.title, item.case_number, item.status]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(normalizedSearch)),
    );
  }, [cases, normalizedSearch]);

  const showActivities = focus === "" || focus === "activities";
  const showReports = focus === "" || focus === "reports";
  const showCases = focus === "" || focus === "cases";

  return (
    <div className="page-stack">
      <OperazioniBreadcrumb
        items={[
          { label: "Operazioni", href: "/operazioni" },
          { label: "Mini-app", href: "/operazioni/miniapp" },
          { label: "Liste personali" },
        ]}
      />

      <OperazioniDetailHero
        eyebrow="My workset"
        title="Attività, segnalazioni e pratiche direttamente legate all'operatore corrente."
        description="Vista compatta per leggere subito cosa è in corso, cosa è stato segnalato e quali pratiche risultano assegnate."
        status={isOnline ? "Online" : "Offline"}
        statusTone={isOnline ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}
      >
        <OperazioniHeroNotice
          title="Perimetro dati"
          description="Le liste usano solo filtri utente già esposti dal backend: attività dell'operatore, segnalazioni inviate e pratiche assegnate."
          tone="default"
        />
      </OperazioniDetailHero>

      <OperazioniMetricStrip>
        <MetricCard label="Attività aperte" value={filteredActivities.length} sub="In corso per operatore" variant={filteredActivities.length > 0 ? "warning" : "default"} />
        <MetricCard label="Segnalazioni inviate" value={filteredReports.length} sub="Ultime create dall'utente" />
        <MetricCard label="Pratiche assegnate" value={filteredCases.length} sub="Da seguire o chiudere" variant={filteredCases.length > 0 ? "danger" : "default"} />
      </OperazioniMetricStrip>

      {error ? <p className="text-sm text-red-700">{error}</p> : null}

      <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr),auto]">
        <OperazioniToolbar
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Cerca per titolo, numero o ID"
          filterValue={focus}
          onFilterChange={setFocus}
          filterOptions={[
            { value: "", label: "Tutte le liste" },
            { value: "activities", label: "Solo attività" },
            { value: "reports", label: "Solo segnalazioni" },
            { value: "cases", label: "Solo pratiche" },
          ]}
        />
        <div className="rounded-[24px] border border-[#e4e8e2] bg-[#fcfcf9] p-3 xl:w-[220px]">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#667267]">Aggiornamento</p>
          <button
            type="button"
            className="btn-secondary mt-3 w-full"
            disabled={isRefreshing}
            onClick={() => {
              setIsRefreshing(true);
              void loadData();
            }}
          >
            {isRefreshing ? "Aggiornamento..." : "Aggiorna liste"}
          </button>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        {showActivities ? <OperazioniCollectionPanel
          title="Attività in corso"
          description="Attività ancora aperte per l'operatore corrente."
          count={filteredActivities.length}
        >
          {isLoading ? (
            <p className="text-sm text-gray-500">Caricamento attività.</p>
          ) : filteredActivities.length === 0 ? (
            <EmptyState
              icon={RefreshIcon}
              title="Nessuna attività aperta"
              description={normalizedSearch ? "Nessuna attività corrisponde ai filtri correnti." : "Non risultano attività in corso per l'utente corrente."}
            />
          ) : (
            <OperazioniList>
              {filteredActivities.map((activity) => (
                <OperazioniListLink
                  key={activity.id}
                  href={`/operazioni/attivita/${activity.id}?context=miniapp`}
                  title={`Attività ${activity.id.slice(0, 8)}…`}
                  meta={activity.started_at ? `Avviata il ${new Date(activity.started_at).toLocaleString("it-IT")}` : "Avvio non disponibile"}
                  status={activityStatusLabels[String(activity.status ?? "")] || String(activity.status ?? "In corso")}
                  statusTone="bg-amber-50 text-amber-700"
                />
              ))}
            </OperazioniList>
          )}
        </OperazioniCollectionPanel> : null}

        {showReports ? <OperazioniCollectionPanel
          title="Segnalazioni inviate"
          description="Ultime segnalazioni create dall'operatore."
          count={filteredReports.length}
        >
          {isLoading ? (
            <p className="text-sm text-gray-500">Caricamento segnalazioni.</p>
          ) : filteredReports.length === 0 ? (
            <EmptyState
              icon={AlertTriangleIcon}
              title="Nessuna segnalazione"
              description={normalizedSearch ? "Nessuna segnalazione corrisponde ai filtri correnti." : "L'utente corrente non ha ancora inviato segnalazioni."}
            />
          ) : (
            <OperazioniList>
              {filteredReports.map((report) => (
                <OperazioniListLink
                  key={report.id}
                  href={`/operazioni/segnalazioni/${report.id}?context=miniapp`}
                  title={String(report.title ?? "Segnalazione")}
                  meta={`${String(report.report_number ?? "Numero non disponibile")}${report.created_at ? ` · ${new Date(report.created_at).toLocaleDateString("it-IT")}` : ""}`}
                  status={String(report.status ?? "Registrata")}
                  statusTone="bg-sky-50 text-sky-700"
                />
              ))}
            </OperazioniList>
          )}
        </OperazioniCollectionPanel> : null}

        {showCases ? <OperazioniCollectionPanel
          title="Pratiche assegnate"
          description="Pratiche attualmente assegnate all'operatore."
          count={filteredCases.length}
        >
          {isLoading ? (
            <p className="text-sm text-gray-500">Caricamento pratiche.</p>
          ) : filteredCases.length === 0 ? (
            <EmptyState
              icon={DocumentIcon}
              title="Nessuna pratica assegnata"
              description={normalizedSearch ? "Nessuna pratica corrisponde ai filtri correnti." : "Non risultano pratiche assegnate all'utente corrente."}
            />
          ) : (
            <OperazioniList>
              {filteredCases.map((item) => (
                <OperazioniListLink
                  key={item.id}
                  href={`/operazioni/pratiche/${item.id}?context=miniapp`}
                  title={String(item.title ?? item.case_number ?? "Pratica")}
                  meta={`${String(item.case_number ?? "Numero non disponibile")}${item.created_at ? ` · ${new Date(item.created_at).toLocaleDateString("it-IT")}` : ""}`}
                  status={caseStatusLabels[String(item.status ?? "")] || String(item.status ?? "Assegnata")}
                  statusTone="bg-rose-50 text-rose-700"
                />
              ))}
            </OperazioniList>
          )}
        </OperazioniCollectionPanel> : null}
      </div>

      <div className="flex flex-wrap gap-3">
        <Link href="/operazioni/miniapp" className="btn-secondary">
          Torna alla Mini-App
        </Link>
        <Link href="/operazioni" className="btn-secondary">
          Dashboard Operazioni
        </Link>
      </div>
    </div>
  );
}

export default function MiniAppListePersonaliPage() {
  return (
    <OperazioniModulePage
      title="Liste personali"
      description="Vista personale di attività, segnalazioni e pratiche per operatore."
      breadcrumb="Mini-app"
    >
      {({ currentUser }) => <ListePersonaliContent currentUserId={currentUser.id} />}
    </OperazioniModulePage>
  );
}
