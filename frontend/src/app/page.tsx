"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  getCatastoDocuments,
  getCurrentUser,
  getDashboardSummary,
  getMyPermissions,
  getNetworkDashboard,
  getUtenzeStats,
  isAuthError,
} from "@/lib/api";
import { clearStoredAccessToken, getStoredAccessToken } from "@/lib/auth";
import { cn } from "@/lib/cn";
import { hasSectionAccess } from "@/lib/section-access";
import type {
  AnagraficaStats,
  CatastoDocument,
  CurrentUser,
  DashboardSummary,
  NetworkDashboardSummary,
} from "@/types/api";

type ModuleStatus = "active" | "warming" | "coming";
type ModuleId = "accessi" | "rete" | "inventario" | "catasto" | "utenze";

type HomeModule = {
  id: ModuleId;
  title: string;
  description: string;
  href: string;
  status: ModuleStatus;
  statusLabel: string;
  icon: string;
  enabledKeys: string[];
};

const emptySummary: DashboardSummary = {
  nas_users: 0,
  nas_groups: 0,
  shares: 0,
  reviews: 0,
  snapshots: 0,
  sync_runs: 0,
};

const emptyNetworkSummary: NetworkDashboardSummary = {
  total_devices: 0,
  online_devices: 0,
  offline_devices: 0,
  open_alerts: 0,
  scans_last_24h: 0,
  floor_plans: 0,
  latest_scan_at: null,
};

const emptyUtenzeSummary: AnagraficaStats = {
  total_subjects: 0,
  total_persons: 0,
  total_companies: 0,
  total_unknown: 0,
  total_documents: 0,
  requires_review: 0,
  active_subjects: 0,
  inactive_subjects: 0,
  documents_unclassified: 0,
  by_letter: {},
};

const allModules: HomeModule[] = [
  {
    id: "accessi",
    title: "GAIA NAS Control",
    description:
      "Monitoraggio avanzato e gestione dei permessi per infrastrutture NAS Synology. Utenti, gruppi, cartelle condivise e workflow di review centralizzato.",
    href: "/nas-control",
    status: "active",
    statusLabel: "Operativo",
    icon: "storage",
    enabledKeys: ["accessi"],
  },
  {
    id: "rete",
    title: "GAIA Rete",
    description:
      "Scansione dispositivi, mappa per piano, alert operativi e controllo dello stato rete con visualizzazioni immediate.",
    href: "/network",
    status: "active",
    statusLabel: "Operativo",
    icon: "hub",
    enabledKeys: ["rete"],
  },
  {
    id: "catasto",
    title: "GAIA Catasto",
    description:
      "Servizi catastali: batch CSV, visure singole, CAPTCHA, ZIP e archivio documentale con una pipeline costruita per l'operatività quotidiana.",
    href: "/catasto",
    status: "active",
    statusLabel: "Operativo",
    icon: "account_balance",
    enabledKeys: ["catasto"],
  },
  {
    id: "utenze",
    title: "GAIA Utenze",
    description:
      "Gestione soggetti, documenti collegati al NAS e correlazioni con Catasto. Modulo operativo per ricerca, import archivio e qualità del dato.",
    href: "/utenze",
    status: "active",
    statusLabel: "Operativo",
    icon: "badge",
    enabledKeys: ["utenze"],
  },
  {
    id: "inventario",
    title: "GAIA Inventario",
    description:
      "Registro centralizzato di device, garanzie, assegnazioni e import da CSV. Struttura pronta, attivazione funzionale in corso.",
    href: "/inventory",
    status: "coming",
    statusLabel: "In sviluppo",
    icon: "inventory_2",
    enabledKeys: ["inventario"],
  },
];

function formatNumber(value: number): string {
  return new Intl.NumberFormat("it-IT").format(value);
}

function HomePageSkeleton({ loadError }: { loadError: string | null }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-surface text-on-surface font-body">
      <span className="font-headline text-3xl font-bold text-primary mb-6">GAIA</span>
      <p className="text-outline text-sm mb-2">Verifica sessione in corso…</p>
      {loadError ? (
        <p className="text-error text-sm mt-2">{loadError}</p>
      ) : null}
      <Link
        className="mt-6 bg-primary text-on-primary px-6 py-3 rounded font-medium text-sm transition hover:opacity-90"
        href="/login"
      >
        Vai al login
      </Link>
    </div>
  );
}

export default function HomePage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [summary, setSummary] = useState<DashboardSummary>(emptySummary);
  const [networkSummary, setNetworkSummary] = useState<NetworkDashboardSummary>(emptyNetworkSummary);
  const [utenzeSummary, setUtenzeSummary] = useState<AnagraficaStats>(emptyUtenzeSummary);
  const [catastoDocuments, setCatastoDocuments] = useState<CatastoDocument[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const [grantedSectionKeys, setGrantedSectionKeys] = useState<string[]>([]);

  useEffect(() => {
    async function loadHome() {
      const token = getStoredAccessToken();

      if (!token) {
        router.replace("/login");
        return;
      }

      try {
        const [user, dashboardSummary, permissionSummary] = await Promise.all([
          getCurrentUser(token),
          getDashboardSummary(token),
          getMyPermissions(token),
        ]);

        const hasNetwork = user.enabled_modules.includes("rete");
        const hasUtenze = user.enabled_modules.includes("utenze");
        const hasCatasto = user.enabled_modules.includes("catasto");

        const [networkDashboard, utenzeStats, documents] = await Promise.all([
          hasNetwork ? getNetworkDashboard(token) : Promise.resolve(emptyNetworkSummary),
          hasUtenze ? getUtenzeStats(token) : Promise.resolve(emptyUtenzeSummary),
          hasCatasto ? getCatastoDocuments(token) : Promise.resolve([]),
        ]);

        setCurrentUser(user);
        setSummary(dashboardSummary);
        setNetworkSummary(networkDashboard);
        setUtenzeSummary(utenzeStats);
        setCatastoDocuments(documents);
        setGrantedSectionKeys(permissionSummary.granted_keys);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore imprevisto");
        if (isAuthError(error)) {
          clearStoredAccessToken();
          setCurrentUser(null);
          setSummary(emptySummary);
          setNetworkSummary(emptyNetworkSummary);
          setUtenzeSummary(emptyUtenzeSummary);
          setCatastoDocuments([]);
          setGrantedSectionKeys([]);
          router.replace("/login");
        }
      } finally {
        setIsCheckingSession(false);
      }
    }

    void loadHome();
  }, [router]);

  function handleLogout(): void {
    clearStoredAccessToken();
    setCurrentUser(null);
    setSummary(emptySummary);
    setNetworkSummary(emptyNetworkSummary);
    setUtenzeSummary(emptyUtenzeSummary);
    setCatastoDocuments([]);
    setGrantedSectionKeys([]);
    router.replace("/login");
  }

  if (isCheckingSession || !currentUser) {
    return <HomePageSkeleton loadError={loadError} />;
  }

  const canManageGaiaUsers =
    (currentUser.role === "admin" || currentUser.role === "super_admin")
    && currentUser.enabled_modules.includes("accessi")
    && hasSectionAccess(grantedSectionKeys, "accessi.users");

  const visibleModules = allModules.filter((mod) => {
    if (mod.status === "coming") return true;
    return mod.enabledKeys.some((key) => currentUser.enabled_modules.includes(key));
  });

  const platformStats = [
    {
      label: "Utenze gestite",
      value: formatNumber(utenzeSummary.total_subjects),
      copy: `${formatNumber(utenzeSummary.active_subjects)} soggetti attivi e ${formatNumber(utenzeSummary.requires_review)} da verificare`,
      icon: "badge",
    },
    {
      label: "Dispositivi connessi",
      value: formatNumber(networkSummary.online_devices),
      copy: `${formatNumber(networkSummary.total_devices)} rilevati, ${formatNumber(networkSummary.offline_devices)} offline`,
      icon: "lan",
    },
    {
      label: "Alert rete aperti",
      value: formatNumber(networkSummary.open_alerts),
      copy: networkSummary.open_alerts === 0 ? "Nessun alert infrastrutturale aperto" : "Dispositivi sconosciuti o assenti da gestire",
      icon: "notifications_active",
    },
  ];

  const operationalStats = [
    {
      label: "Sync runs",
      value: formatNumber(summary.sync_runs),
      copy: "Cicli completati nelle ultime 24 ore",
      icon: "sync",
    },
    {
      label: "Documenti catasto",
      value: formatNumber(catastoDocuments.length),
      copy: "Archivio PDF disponibile per ricerca e download",
      icon: "description",
    },
  ];

  const statusBadge: Record<ModuleStatus, string> = {
    active: "bg-primary-fixed text-on-primary-fixed",
    warming: "bg-secondary-fixed text-on-secondary-fixed",
    coming: "bg-tertiary-fixed-dim text-on-tertiary-fixed-variant",
  };

  return (
    <div className="min-h-screen bg-surface text-on-surface font-body">
      {/* TopAppBar */}
      <header className="bg-surface fixed top-0 w-full z-50">
        <div className="flex justify-between items-center w-full px-8 py-4 max-w-full">
          <div className="flex items-center gap-12">
            <span className="font-headline text-2xl font-bold italic text-primary">GAIA</span>
            <nav className="hidden md:flex gap-8">
              {visibleModules
                .filter((m) => m.status !== "coming")
                .map((mod) => (
                  <Link
                    key={mod.id}
                    href={mod.href}
                    className="font-body font-medium text-outline hover:text-primary transition-colors duration-200"
                  >
                    {mod.title.replace("GAIA ", "")}
                  </Link>
                ))}
            </nav>
          </div>

          <div className="flex items-center gap-4">
            {/* Search (lg+) */}
            <div className="relative hidden lg:block">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-sm pointer-events-none">
                search
              </span>
              <input
                className="bg-surface-container-high border-none rounded-lg pl-10 pr-4 py-2 text-sm focus:ring-1 focus:ring-primary w-56 transition-all outline-none"
                placeholder="Ricerca globale…"
                type="text"
                readOnly
              />
            </div>

            {/* User + logout */}
            <span className="text-sm font-medium text-on-surface-variant hidden lg:block">
              {currentUser.username}
            </span>
            <button
              type="button"
              onClick={handleLogout}
              className="text-on-surface-variant hover:text-primary transition-colors"
              aria-label="Logout"
            >
              <span className="material-symbols-outlined">logout</span>
            </button>
          </div>
        </div>
        <div className="bg-surface-container h-[1px] w-full" />
      </header>

      {/* Main content */}
      <main className="pt-24 pb-12 px-8 max-w-7xl mx-auto min-h-screen">
        {/* Hero */}
        <section className="mb-16">
          <div>
            <h1 className="text-6xl font-headline font-medium text-primary leading-tight mb-4">
              Gestione Apparati Informativi
            </h1>
            <p className="text-xl font-body text-outline leading-relaxed">
              GAIA (Governance &amp; Audit for Information Assets) funge da nucleo centrale per il monitoraggio
              istituzionale, garantendo integrità, sicurezza e controllo granulare su tutte le infrastrutture IT
              e i flussi documentali dell&apos;ente.
            </p>
          </div>
        </section>

        <section className="mb-16">
          <div className="mb-5 flex items-end justify-between gap-4">
            <div>
              <h2 className="text-2xl font-headline text-primary">Cruscotto rapido</h2>
              <p className="text-sm text-outline">Tutti i numeri principali in una sola riga sui layout desktop ampi.</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4">
            {[...platformStats, ...operationalStats].map((stat) => (
              <div
                key={`quick-${stat.label}`}
                className="bg-surface-container-low p-5 rounded-xl flex flex-col justify-between min-h-[138px]"
              >
                <div className="flex justify-between items-start gap-3">
                  <span className="text-[11px] font-label tracking-[0.05em] uppercase text-outline">{stat.label}</span>
                  <span className="material-symbols-outlined text-primary text-[20px]">{stat.icon}</span>
                </div>
                <div className="mt-3">
                  <span className="text-3xl font-headline text-primary">{stat.value}</span>
                  <p className="text-xs text-on-secondary-container mt-2 leading-relaxed">{stat.copy}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Admin section */}
        {canManageGaiaUsers ? (
          <div className="mb-10">
            <Link
              href="/gaia/users"
              className="flex items-center justify-between bg-surface-container-low p-6 rounded-xl hover:shadow-md transition-all duration-300 group"
            >
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 bg-primary-container rounded-lg flex items-center justify-center">
                  <span className="material-symbols-outlined text-primary-fixed text-xl">manage_accounts</span>
                </div>
                <div>
                  <p className="font-medium text-primary text-sm tracking-wide">Amministrazione GAIA</p>
                  <p className="text-on-surface-variant text-sm">Utenti applicativi, ruoli e abilitazioni</p>
                </div>
              </div>
              <span className="material-symbols-outlined text-outline group-hover:text-primary transition-colors">
                arrow_forward
              </span>
            </Link>
          </div>
        ) : null}

        {/* Module domains */}
        <section>
          <div className="flex items-end justify-between mb-8">
            <div>
              <h2 className="text-3xl font-headline text-primary mb-2">Seleziona il dominio operativo</h2>
              <p className="text-outline font-body">Sistemi di controllo e gestione asset istituzionali</p>
            </div>
            <div className="flex gap-4">
              <span className="flex items-center gap-2 text-xs font-label tracking-widest uppercase text-outline">
                <span className="w-2 h-2 rounded-full bg-primary-fixed" /> Operativo
              </span>
              <span className="flex items-center gap-2 text-xs font-label tracking-widest uppercase text-outline">
                <span className="w-2 h-2 rounded-full bg-tertiary-fixed-dim" /> In sviluppo
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {visibleModules.map((mod) => {
              const isInteractive = mod.status !== "coming";
              const card = (
                <article
                  className={cn(
                    "group bg-surface-container-lowest p-8 rounded-xl border border-outline-variant/15 transition-all duration-300 flex flex-col justify-between min-h-[300px] relative overflow-hidden",
                    isInteractive
                      ? "hover:shadow-2xl cursor-pointer"
                      : "opacity-70 cursor-default",
                  )}
                >
                  {/* Status badge */}
                  <div className="absolute top-0 right-0 p-4">
                    <span
                      className={cn(
                        "inline-flex items-center rounded-full px-3 py-1 text-xs font-label uppercase tracking-wider",
                        statusBadge[mod.status],
                      )}
                    >
                      {mod.statusLabel}
                    </span>
                  </div>

                  <div>
                    <div className="w-12 h-12 bg-primary-container rounded-lg flex items-center justify-center mb-6">
                      <span className="material-symbols-outlined text-primary-fixed">{mod.icon}</span>
                    </div>
                    <h3 className="text-2xl font-headline text-primary mb-3">{mod.title}</h3>
                    <p className="text-on-surface-variant leading-relaxed text-sm">{mod.description}</p>
                  </div>

                  <button
                    className={cn(
                      "mt-8 flex items-center gap-2 font-bold transition-all",
                      isInteractive
                        ? "text-primary group-hover:gap-4"
                        : "text-outline cursor-default",
                    )}
                    tabIndex={isInteractive ? 0 : -1}
                    aria-hidden={!isInteractive}
                  >
                    {isInteractive ? "Accedi al modulo" : "Disponibile prossimamente"}
                    <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
                  </button>
                </article>
              );

              if (!isInteractive) return <div key={mod.id}>{card}</div>;

              return (
                <Link key={mod.id} href={mod.href} className="block rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30">
                  {card}
                </Link>
              );
            })}
          </div>
        </section>
      </main>

      <footer className="px-8 py-6 border-t border-outline-variant/20 max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-xs text-outline">
        <p>© GAIA platform · Consorzio di Bonifica dell&apos;Oristanese</p>
        <p>Sessione attiva: {currentUser.username} · {currentUser.role}</p>
      </footer>
    </div>
  );
}
