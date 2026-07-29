"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import {
  getCurrentUser,
  getDashboardSummary,
  getMyPermissions,
  getPresenceSummary,
  getUtenzeStats,
  SESSION_BOOTSTRAP_TIMEOUT_MS,
  isAuthError,
} from "@/lib/api";
import { catastoGetIndiciOverview } from "@/lib/api/catasto";
import { searchOperational } from "@/lib/operational-search-api";
import { getRuoloStats, getRuoloStatsAnalytics } from "@/lib/ruolo-api";
import { clearStoredAccessToken, getStoredAccessToken } from "@/lib/auth";
import { cn } from "@/lib/cn";
import { hasUserModuleAccess } from "@/lib/module-access";
import { usePresenceHeartbeat } from "@/lib/use-presence-heartbeat";
import { hasSectionAccess } from "@/lib/section-access";
import { WikiWelcomePopup } from "@/components/wiki/WikiWelcomePopup";
import type {
  AnagraficaStats,
  CurrentUser,
  DashboardSummary,
  OperationalSearchResult,
  UserPresenceSummary,
} from "@/types/api";
import type { CatIndiceOverview } from "@/types/catasto";
import type { RuoloStatsAnalyticsResponse, RuoloStatsResponse } from "@/types/ruolo";

type ModuleStatus = "active" | "warming" | "coming";
type ModuleId = "me" | "admin" | "accessi" | "rete" | "inventario" | "gis" | "catasto" | "elaborazioni" | "utenze" | "operazioni" | "riordino" | "ruolo" | "wiki" | "presenze";

type HomeModule = {
  id: ModuleId;
  title: string;
  eyebrow: string;
  description: string;
  href: string;
  status: ModuleStatus;
  statusLabel: string;
  icon: string;
  enabledKeys: string[];
  requiredSection?: string;
  requiredRoles?: string[];
};

type SearchRoute = {
  label: string;
  href: string;
  moduleKey?: string;
  requiredSection?: string;
  requiredRoles?: string[];
  keywords?: string[];
};

const menuSearchRoutes: SearchRoute[] = [
  // Self service
  { label: "La mia attività · Panoramica", href: "/me", keywords: ["me", "attivita", "presenze", "self service"] },
  { label: "La mia attività · Presenze", href: "/me/presenze", keywords: ["presenze", "giornaliere"] },
  { label: "La mia attività · Operatività", href: "/me/operativita", keywords: ["operativita", "attivita", "segnalazioni", "pratiche"] },
  { label: "La mia attività · Dotazioni", href: "/me/dotazioni", keywords: ["dotazioni", "dispositivi", "mezzi"] },
  { label: "La mia attività · Anomalie", href: "/me/anomalie", keywords: ["anomalie", "warning"] },

  // NAS / Accessi
  { label: "NAS Control · Dashboard", href: "/nas-control", moduleKey: "accessi", keywords: ["nas", "accessi"] },
  { label: "NAS Control · Sincronizzazione", href: "/nas-control/sync", moduleKey: "accessi", keywords: ["sync", "sincronizzazione"] },
  { label: "NAS Control · Utenti", href: "/nas-control/users", moduleKey: "accessi", requiredSection: "accessi.users", keywords: ["utenti", "users"] },
  { label: "NAS Control · Gruppi", href: "/nas-control/groups", moduleKey: "accessi", keywords: ["gruppi", "groups"] },
  { label: "NAS Control · Cartelle condivise", href: "/nas-control/shares", moduleKey: "accessi", keywords: ["shares", "cartelle"] },
  { label: "NAS Control · Permessi effettivi", href: "/nas-control/effective-permissions", moduleKey: "accessi", keywords: ["permessi", "effective"] },
  { label: "NAS Control · Review NAS", href: "/nas-control/reviews", moduleKey: "accessi", keywords: ["review", "validazione"] },
  { label: "NAS Control · Report", href: "/nas-control/reports", moduleKey: "accessi", keywords: ["report"] },

  // Elaborazioni
  { label: "Elaborazioni · Dashboard", href: "/elaborazioni", moduleKey: "elaborazioni", requiredRoles: ["super_admin"], keywords: ["batch"] },
  { label: "Elaborazioni · WhiteCompany Sync", href: "/elaborazioni/bonifica", moduleKey: "elaborazioni", requiredRoles: ["super_admin"], keywords: ["white", "bonifica", "sync"] },
  { label: "Elaborazioni · Presenze INAZ Sync", href: "/elaborazioni/presenze-sync", moduleKey: "presenze", keywords: ["sync", "portale", "inaz", "giornaliere"] },
  { label: "Elaborazioni · Visure", href: "/elaborazioni/visure", moduleKey: "elaborazioni", requiredRoles: ["super_admin"], keywords: ["visure"] },
  { label: "Elaborazioni · Capacitas", href: "/elaborazioni/capacitas", moduleKey: "elaborazioni", requiredRoles: ["super_admin"], keywords: ["capacitas"] },
  { label: "Elaborazioni · Poste Online", href: "/elaborazioni/posta-online", moduleKey: "elaborazioni", requiredRoles: ["super_admin"], keywords: ["poste", "posta online", "raccomandate"] },
  { label: "Elaborazioni · GAIA Mobile Sync", href: "/elaborazioni/gaia-mobile-sync", moduleKey: "elaborazioni", requiredRoles: ["super_admin"], keywords: ["gaia mobile", "mobile sync", "gateway"] },
  { label: "Elaborazioni · Credenziali", href: "/elaborazioni/settings", moduleKey: "elaborazioni", requiredRoles: ["super_admin"], keywords: ["credenziali", "settings"] },

  // Wiki
  { label: "Wiki · Documentazione e assistente", href: "/wiki", keywords: ["wiki", "documentazione", "assistente"] },
  { label: "Wiki · Supporto", href: "/wiki/support", keywords: ["wiki", "supporto", "anomalia", "feature", "richiesta", "bug"] },
  { label: "Wiki · Inbox supporto", href: "/wiki/support/inbox", keywords: ["wiki", "supporto", "inbox", "triage", "anomalia", "accesso", "dati"] },
  { label: "Wiki · Analytics supporto", href: "/wiki/support/analytics", keywords: ["wiki", "supporto", "analytics", "trend", "feature request", "bug"] },
  { label: "Wiki · Richieste", href: "/wiki/requests", keywords: ["wiki", "richieste", "feature request", "bug report"] },

  // Presenze
  { label: "Presenze · Dashboard", href: "/presenze", moduleKey: "presenze", keywords: ["giornaliere", "cartellino", "presenze"] },
  { label: "Presenze · Collaboratori", href: "/presenze/collaboratori", moduleKey: "presenze", keywords: ["collaboratori", "dipendenti"] },
  { label: "Presenze · Giornaliere", href: "/presenze/giornaliere", moduleKey: "presenze", keywords: ["giornaliere", "presenze"] },
  { label: "Presenze · Organigramma", href: "/presenze/organigramma", moduleKey: "presenze", keywords: ["organigramma", "gerarchia", "capi settore", "permessi"] },
  { label: "Presenze · Export", href: "/presenze/export", moduleKey: "presenze", keywords: ["export", "xlsm"] },
  { label: "Presenze · Banca ore", href: "/presenze/banca-ore", moduleKey: "presenze", keywords: ["banca ore", "liquidazioni", "saldo ore"] },

  { label: "GIS Platform · Catalogo", href: "/gis/catalogo", moduleKey: "gis", keywords: ["gis", "catalogo", "layer", "postgis", "martin"] },

  // Catasto
  { label: "Catasto · Dashboard", href: "/catasto", moduleKey: "catasto" },
  { label: "Catasto · Distretti", href: "/catasto/distretti", moduleKey: "catasto", keywords: ["distretti"] },
  { label: "Catasto · Particelle", href: "/catasto/particelle", moduleKey: "catasto", keywords: ["mappali", "terreni"] },
  { label: "Catasto · Contatori irrigui", href: "/catasto/letture-contatori", moduleKey: "catasto", keywords: ["letture contatori", "contatori", "gate mobile", "mobile", "gps", "foto"] },
  { label: "Catasto · Anomalie", href: "/catasto/anomalie", moduleKey: "catasto", keywords: ["errori"] },
  { label: "Catasto · Import", href: "/catasto/import", moduleKey: "catasto", keywords: ["caricamento"] },
  { label: "Catasto · Archivio documenti", href: "/catasto/archive", moduleKey: "catasto", keywords: ["documenti"] },

  // Network (rete)
  { label: "Rete · Dashboard", href: "/network", moduleKey: "rete" },
  { label: "Rete · Dispositivi", href: "/network/devices", moduleKey: "rete", keywords: ["switch", "ap", "devices"] },
  { label: "Rete · Firewall", href: "/network/firewalls", moduleKey: "rete", keywords: ["sophos", "xgs", "syslog", "snmp"] },
  { label: "Rete · Statistiche", href: "/network/statistics", moduleKey: "rete", keywords: ["analytics", "traffico", "navigazione"] },
  { label: "Rete · Planimetria", href: "/network/floor-plan", moduleKey: "rete", keywords: ["mappa", "planimetria"] },
  { label: "Rete · Alert", href: "/network/alerts", moduleKey: "rete", keywords: ["allarmi"] },
  { label: "Rete · Scansioni", href: "/network/scans", moduleKey: "rete", keywords: ["scan", "scansioni"] },

  // Utenze / Anagrafica
  { label: "Utenze · Dashboard", href: "/utenze", moduleKey: "utenze" },
  { label: "Utenze · Soggetti", href: "/utenze/import#utenze-soggetti", moduleKey: "utenze", keywords: ["anagrafica", "subjects"] },
  { label: "Utenze · Import dati", href: "/utenze/import", moduleKey: "utenze", keywords: ["import"] },

  // Operazioni
  { label: "Operazioni · Dashboard", href: "/operazioni", moduleKey: "operazioni" },
  { label: "Operazioni · Analisi operazioni", href: "/operazioni/analisi", moduleKey: "operazioni", keywords: ["analisi"] },
  { label: "Operazioni · Operatori", href: "/operazioni/operatori", moduleKey: "operazioni" },
  { label: "Operazioni · Carte carburante", href: "/operazioni/carte-carburante", moduleKey: "operazioni", keywords: ["fuel", "carburante"] },
  { label: "Operazioni · Mezzi", href: "/operazioni/mezzi", moduleKey: "operazioni", keywords: ["veicoli", "automezzi"] },
  { label: "Operazioni · Attività", href: "/operazioni/attivita", moduleKey: "operazioni" },
  { label: "Operazioni · Cruscotto segnalazioni", href: "/operazioni/segnalazioni/cruscotto", moduleKey: "operazioni", keywords: ["cruscotto"] },
  { label: "Operazioni · Segnalazioni", href: "/operazioni/segnalazioni", moduleKey: "operazioni" },
  { label: "Operazioni · Pratiche", href: "/operazioni/pratiche", moduleKey: "operazioni" },

  // Riordino
  { label: "Riordino · Dashboard", href: "/riordino", moduleKey: "riordino" },
  { label: "Riordino · Pratiche", href: "/riordino/pratiche", moduleKey: "riordino" },
  { label: "Riordino · Configurazione", href: "/riordino/configurazione", moduleKey: "riordino", keywords: ["settings"] },

  // Ruolo
  { label: "Ruolo · Dashboard", href: "/ruolo", moduleKey: "ruolo" },
  { label: "Ruolo · Avvisi", href: "/ruolo/avvisi", moduleKey: "ruolo" },
  { label: "Ruolo · Particelle", href: "/ruolo/particelle", moduleKey: "ruolo", requiredSection: "ruolo.avvisi", keywords: ["particelle", "mappali", "ruolo"] },
  { label: "Ruolo · Statistiche", href: "/ruolo/stats", moduleKey: "ruolo", keywords: ["analytics"] },
  { label: "Ruolo · Storico workflow", href: "/ruolo/import", moduleKey: "ruolo", keywords: ["ruolo", "storico", "incass"] },

  // Admin GAIA users (include section check)
  {
    label: "Amministrazione · Attività utenti GAIA",
    href: "/gaia/users/attivita",
    moduleKey: "accessi",
    requiredSection: "accessi.users",
    requiredRoles: ["admin", "super_admin"],
    keywords: ["attivita utenti", "connessi", "attivi", "gaia"],
  },
  {
    label: "Amministrazione · Utenti GAIA",
    href: "/gaia/users",
    moduleKey: "accessi",
    requiredSection: "accessi.users",
    requiredRoles: ["admin", "super_admin"],
    keywords: ["admin", "utenti", "gaia"],
  },
];

const emptyPresenceSummary: UserPresenceSummary = {
  window_minutes: 15,
  active_users: 0,
  visible_users: 0,
  items: [],
  by_module: [],
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
  deceased_updates_last_24h: 0,
  deceased_updates_current_month: 0,
  deceased_updates_current_year: 0,
  by_letter: {},
};

const emptyDashboardSummary: DashboardSummary = {
  nas_users: 0,
  nas_groups: 0,
  shares: 0,
  reviews: 0,
  snapshots: 0,
  sync_runs: 0,
};

const emptyRuoloStats: RuoloStatsResponse = {
  items: [],
};

const allModules: HomeModule[] = [
  {
    id: "admin",
    title: "Amministrazione GAIA",
    eyebrow: "Governance piattaforma",
    description:
      "Utenti applicativi, ruoli, abilitazioni e perimetri di accesso alla piattaforma GAIA.",
    href: "/gaia/users",
    status: "active",
    statusLabel: "Operativo",
    icon: "manage_accounts",
    enabledKeys: ["accessi"],
    requiredSection: "accessi.users",
    requiredRoles: ["admin", "super_admin"],
  },
  {
    id: "me",
    title: "La mia attività",
    eyebrow: "Self service personale",
    description:
      "Presenze, attività operative, utilizzo mezzi, pratiche, segnalazioni e dotazioni personali in un unico spazio.",
    href: "/me",
    status: "active",
    statusLabel: "Operativo",
    icon: "person",
    enabledKeys: [],
  },
  {
    id: "catasto",
    title: "GAIA Catasto",
    eyebrow: "Dominio dati",
    description:
      "Distretti, particelle, anomalie, ricerca anagrafica e import Capacitas.",
    href: "/catasto",
    status: "warming",
    statusLabel: "In sviluppo",
    icon: "account_balance",
    enabledKeys: ["catasto"],
  },
  {
    id: "gis",
    title: "GIS Platform",
    eyebrow: "Catalogo geospaziale",
    description:
      "Catalogo centrale dei layer, permessi, health check ed export GIS pubblicati dai domini GAIA.",
    href: "/gis/catalogo",
    status: "active",
    statusLabel: "Operativo",
    icon: "map",
    enabledKeys: ["gis"],
  },
  {
    id: "operazioni",
    title: "GAIA Operazioni",
    eyebrow: "Field operations",
    description:
      "Modulo in sviluppo per mezzi, attività, segnalazioni e pratiche operative.",
    href: "/operazioni",
    status: "warming",
    statusLabel: "In sviluppo",
    icon: "local_shipping",
    enabledKeys: ["operazioni"],
  },
  {
    id: "utenze",
    title: "GAIA Utenze",
    eyebrow: "Soggetti e documenti",
    description:
      "Modulo in sviluppo per soggetti, documenti e qualità del dato, con superficie ancora non consolidata.",
    href: "/utenze",
    status: "warming",
    statusLabel: "In sviluppo",
    icon: "badge",
    enabledKeys: ["utenze"],
  },
  {
    id: "ruolo",
    title: "GAIA Ruolo",
    eyebrow: "Ruolo consortile",
    description:
      "Import e consultazione degli avvisi del ruolo consortile (Capacitas). Collegamento soggetti, statistiche per comune e anno tributario.",
    href: "/ruolo",
    status: "warming",
    statusLabel: "In sviluppo",
    icon: "receipt_long",
    enabledKeys: ["ruolo"],
  },
  {
    id: "accessi",
    title: "GAIA NAS Control",
    eyebrow: "Governance accessi",
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
    eyebrow: "Monitoraggio infrastruttura",
    description:
      "Scansione dispositivi, mappa per piano, alert operativi e controllo dello stato rete con visualizzazioni immediate.",
    href: "/network",
    status: "active",
    statusLabel: "Operativo",
    icon: "hub",
    enabledKeys: ["rete"],
  },
  {
    id: "elaborazioni",
    title: "GAIA Elaborazioni",
    eyebrow: "Runtime operativo catasto",
    description:
      "Modulo in sviluppo: perimetro e workflow applicativi sono ancora in consolidamento.",
    href: "/elaborazioni",
    status: "warming",
    statusLabel: "In sviluppo",
    icon: "sync_alt",
    enabledKeys: ["catasto"],
    requiredRoles: ["super_admin"],
  },
  {
    id: "wiki",
    title: "GAIA Wiki",
    eyebrow: "Documentazione e assistente",
    description:
      "Documentazione indicizzata e assistente contestuale per navigare procedure, moduli e flussi GAIA.",
    href: "/wiki",
    status: "active",
    statusLabel: "Operativo",
    icon: "menu_book",
    enabledKeys: ["wiki"],
  },
  {
    id: "presenze",
    title: "GAIA Presenze",
    eyebrow: "Giornaliere e collaboratori",
    description:
      "Collaboratori, giornaliere, import JSON dal portale presenze, sync live ed export XLSM per i capi settore.",
    href: "/presenze",
    status: "active",
    statusLabel: "Operativo",
    icon: "calendar_month",
    enabledKeys: ["presenze"],
  },
  {
    id: "riordino",
    title: "GAIA Riordino",
    eyebrow: "Workflow riordino catastale",
    description:
      "Modulo in sviluppo per pratiche, workflow, documenti e anomalie del riordino catastale.",
    href: "/riordino",
    status: "warming",
    statusLabel: "In sviluppo",
    icon: "description",
    enabledKeys: ["riordino"],
  },
  {
    id: "inventario",
    title: "GAIA Inventario",
    eyebrow: "Asset fisici",
    description:
      "Area non ancora avviata: non sono presenti workflow o dati operativi utilizzabili.",
    href: "/inventory",
    status: "coming",
    statusLabel: "Non avviato",
    icon: "inventory_2",
    enabledKeys: ["inventario"],
  },
];

function formatNumber(value: number): string {
  return new Intl.NumberFormat("it-IT").format(value);
}

function isRuoloOperationalDistrict(value: string | null | undefined): boolean {
  const normalized = (value ?? "").trim().toUpperCase();
  return normalized.length > 0 && normalized !== "FD" && normalized !== "N/D";
}

function HomePageSkeleton() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-surface text-on-surface font-body">
      <span className="font-headline text-3xl font-bold text-primary mb-6">GAIA</span>
      <p className="text-outline text-sm mb-2">Verifica sessione in corso…</p>
      <Link
        className="mt-6 bg-primary text-on-primary px-6 py-3 rounded font-medium text-sm transition hover:opacity-90"
        href="/login"
      >
        Vai al login
      </Link>
    </div>
  );
}

function HomePageAccessRequired({ loadError }: { loadError: string | null }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-surface text-on-surface font-body">
      <span className="font-headline text-3xl font-bold text-primary mb-6">GAIA</span>
      <p className="text-outline text-sm mb-2">Accesso richiesto</p>
      <p className="text-outline text-sm">{loadError ?? "Effettua il login per aprire l'hub operativo."}</p>
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
  const [dashboardSummary, setDashboardSummary] = useState<DashboardSummary>(emptyDashboardSummary);
  const [utenzeSummary, setUtenzeSummary] = useState<AnagraficaStats>(emptyUtenzeSummary);
  const [presenceSummary, setPresenceSummary] = useState<UserPresenceSummary>(emptyPresenceSummary);
  const [ruoloStats, setRuoloStats] = useState<RuoloStatsResponse>(emptyRuoloStats);
  const [ruoloAnalytics, setRuoloAnalytics] = useState<RuoloStatsAnalyticsResponse | null>(null);
  const [catastoIndiciOverview, setCatastoIndiciOverview] = useState<CatIndiceOverview | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const [grantedSectionKeys, setGrantedSectionKeys] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [activeSearchSurface, setActiveSearchSurface] = useState<"topbar" | "hero">("hero");
  const [operationalSearchResults, setOperationalSearchResults] = useState<OperationalSearchResult[]>([]);
  const [isOperationalSearchLoading, setIsOperationalSearchLoading] = useState(false);
  const [operationalSearchError, setOperationalSearchError] = useState<string | null>(null);

  usePresenceHeartbeat({ enabled: Boolean(currentUser) });

  useEffect(() => {
    async function loadHome() {
      const token = getStoredAccessToken();

      if (!token) {
        setCurrentUser(null);
        setDashboardSummary(emptyDashboardSummary);
        setUtenzeSummary(emptyUtenzeSummary);
        setPresenceSummary(emptyPresenceSummary);
        setRuoloStats(emptyRuoloStats);
        setRuoloAnalytics(null);
        setCatastoIndiciOverview(null);
        setGrantedSectionKeys([]);
        setLoadError("Accesso richiesto. Effettua il login.");
        setIsCheckingSession(false);
        router.replace("/login");
        return;
      }

      try {
        const [user, permissionSummary] = await Promise.all([
          getCurrentUser(token, { timeoutMs: SESSION_BOOTSTRAP_TIMEOUT_MS }),
          getMyPermissions(token, { timeoutMs: SESSION_BOOTSTRAP_TIMEOUT_MS }),
        ]);

        const hasCatasto = user.enabled_modules.includes("catasto");
        const hasRuolo = user.enabled_modules.includes("ruolo");
        const hasUtenze = user.enabled_modules.includes("utenze");
        const hasAccessi = user.enabled_modules.includes("accessi");
        const canReadPresenceSummary =
          (user.role === "admin" || user.role === "super_admin")
          && user.enabled_modules.includes("accessi")
          && hasSectionAccess(permissionSummary.granted_keys, "accessi.users");

        const [dashboardSummaryResult, utenzeStatsResult, presenceSummaryResult, ruoloStatsResult] = await Promise.allSettled([
          hasAccessi ? getDashboardSummary(token, { timeoutMs: SESSION_BOOTSTRAP_TIMEOUT_MS }) : Promise.resolve(emptyDashboardSummary),
          hasUtenze ? getUtenzeStats(token) : Promise.resolve(emptyUtenzeSummary),
          canReadPresenceSummary ? getPresenceSummary(token, { windowMinutes: 15 }) : Promise.resolve(emptyPresenceSummary),
          hasRuolo ? getRuoloStats(token) : Promise.resolve(emptyRuoloStats),
        ]);

        const loadedDashboardSummary =
          dashboardSummaryResult.status === "fulfilled" ? dashboardSummaryResult.value : emptyDashboardSummary;
        const loadedUtenzeSummary =
          utenzeStatsResult.status === "fulfilled" ? utenzeStatsResult.value : emptyUtenzeSummary;
        const presence =
          presenceSummaryResult.status === "fulfilled" ? presenceSummaryResult.value : emptyPresenceSummary;
        const loadedRuoloStats =
          ruoloStatsResult.status === "fulfilled" ? ruoloStatsResult.value : emptyRuoloStats;
        const latestRuoloYear = loadedRuoloStats.items[0]?.anno_tributario;
        const [ruoloAnalyticsResult, catastoIndiciOverviewResult] = await Promise.allSettled([
          hasRuolo && latestRuoloYear != null ? getRuoloStatsAnalytics(token, latestRuoloYear) : Promise.resolve(null),
          hasCatasto ? catastoGetIndiciOverview(token, latestRuoloYear) : Promise.resolve(null),
        ]);
        const loadedRuoloAnalytics =
          ruoloAnalyticsResult.status === "fulfilled" ? ruoloAnalyticsResult.value : null;
        const loadedCatastoIndiciOverview =
          catastoIndiciOverviewResult.status === "fulfilled" ? catastoIndiciOverviewResult.value : null;

        setCurrentUser(user);
        setDashboardSummary(loadedDashboardSummary);
        setUtenzeSummary(loadedUtenzeSummary);
        setPresenceSummary(presence);
        setRuoloStats(loadedRuoloStats);
        setRuoloAnalytics(loadedRuoloAnalytics);
        setCatastoIndiciOverview(loadedCatastoIndiciOverview);
        setGrantedSectionKeys(permissionSummary.granted_keys);
        setLoadError(null);

        if (
          dashboardSummaryResult.status === "rejected" ||
          utenzeStatsResult.status === "rejected" ||
          presenceSummaryResult.status === "rejected" ||
          ruoloStatsResult.status === "rejected" ||
          ruoloAnalyticsResult.status === "rejected" ||
          catastoIndiciOverviewResult.status === "rejected"
        ) {
          console.warn("Home dashboard loaded with partial module data", {
            dashboardError:
              dashboardSummaryResult.status === "rejected" ? dashboardSummaryResult.reason : null,
            utenzeError: utenzeStatsResult.status === "rejected" ? utenzeStatsResult.reason : null,
            presenceSummaryError:
              presenceSummaryResult.status === "rejected" ? presenceSummaryResult.reason : null,
            ruoloStatsError: ruoloStatsResult.status === "rejected" ? ruoloStatsResult.reason : null,
            ruoloAnalyticsError:
              ruoloAnalyticsResult.status === "rejected" ? ruoloAnalyticsResult.reason : null,
            catastoIndiciOverviewError:
              catastoIndiciOverviewResult.status === "rejected" ? catastoIndiciOverviewResult.reason : null,
          });
        }
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore imprevisto");
        if (isAuthError(error)) {
          clearStoredAccessToken();
          setCurrentUser(null);
          setDashboardSummary(emptyDashboardSummary);
          setUtenzeSummary(emptyUtenzeSummary);
          setPresenceSummary(emptyPresenceSummary);
          setRuoloStats(emptyRuoloStats);
          setRuoloAnalytics(null);
          setCatastoIndiciOverview(null);
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
    setDashboardSummary(emptyDashboardSummary);
    setUtenzeSummary(emptyUtenzeSummary);
    setPresenceSummary(emptyPresenceSummary);
    setRuoloStats(emptyRuoloStats);
    setRuoloAnalytics(null);
    setCatastoIndiciOverview(null);
    setGrantedSectionKeys([]);
    router.replace("/login");
  }

  const menuSearchResults = useMemo(() => {
    const user = currentUser;
    if (!user) return [];
    const activeUser: CurrentUser = user;
    const query = searchQuery.trim().toLowerCase();
    if (!query) return [];

    const userRole = user.role;
    const isAdmin = userRole === "admin" || userRole === "super_admin";

    function isRouteAllowed(route: SearchRoute): boolean {
      if (route.requiredRoles && !route.requiredRoles.includes(userRole)) return false;
      if (route.requiredSection && !hasSectionAccess(grantedSectionKeys, route.requiredSection)) return false;
      if (!route.moduleKey) return true;
      if (isAdmin) return true;
      return hasUserModuleAccess(activeUser, route.moduleKey);
    }

    function scoreRoute(route: SearchRoute): number {
      const haystack = [route.label, ...(route.keywords ?? [])].join(" ").toLowerCase();
      if (haystack === query) return 100;
      if (route.label.toLowerCase().startsWith(query)) return 80;
      if (haystack.includes(query)) return 60;
      return 0;
    }

    return menuSearchRoutes
      .filter(isRouteAllowed)
      .map((route) => ({ route, score: scoreRoute(route) }))
      .filter((item) => item.score > 0)
      .sort((a, b) => b.score - a.score || a.route.label.localeCompare(b.route.label))
      .slice(0, 10)
      .map((item) => item.route);
  }, [currentUser, grantedSectionKeys, searchQuery]);

  useEffect(() => {
    const token = getStoredAccessToken();
    const query = searchQuery.trim();

    if (!currentUser || !token || query.length < 2) {
      setOperationalSearchResults([]);
      setIsOperationalSearchLoading(false);
      setOperationalSearchError(null);
      return;
    }

    let cancelled = false;
    setIsOperationalSearchLoading(true);
    setOperationalSearchError(null);

    const timeoutId = window.setTimeout(() => {
      searchOperational(token, query, { limit: 8 })
        .then((response) => {
          /* v8 ignore next -- defensive guard for stale in-flight searches after cleanup. */
          if (cancelled) return;
          setOperationalSearchResults(response.items);
        })
        .catch((error) => {
          /* v8 ignore next -- defensive guard for stale in-flight searches after cleanup. */
          if (cancelled) return;
          setOperationalSearchResults([]);
          setOperationalSearchError(error instanceof Error ? error.message : "Ricerca non disponibile");
        })
        .finally(() => {
          /* v8 ignore next -- defensive guard for stale in-flight searches after cleanup. */
          if (!cancelled) {
            setIsOperationalSearchLoading(false);
          }
        });
    }, 180);

    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [currentUser, searchQuery]);

  const groupedOperationalResults = useMemo(() => {
    const groups: Record<string, OperationalSearchResult[]> = {};
    for (const item of operationalSearchResults) {
      groups[item.module] = [...(groups[item.module] ?? []), item];
    }
    return Object.entries(groups);
  }, [operationalSearchResults]);

  const firstSearchHref = operationalSearchResults[0]?.href ?? menuSearchResults[0]?.href;
  const moduleLabels: Record<string, string> = {
    utenze: "Utenze",
    ruolo: "Ruolo",
    catasto: "Catasto",
  };

  useEffect(() => {
    function handleDocumentClick(event: MouseEvent) {
      const target = event.target as Node | null;
      /* v8 ignore next -- browser-dispatched mouse events always provide a target. */
      if (!target) return;
      if (target instanceof Element && !target.closest("[data-home-search]")) {
        setIsSearchOpen(false);
      }
    }
    document.addEventListener("mousedown", handleDocumentClick);
    return () => document.removeEventListener("mousedown", handleDocumentClick);
  }, []);

  if (isCheckingSession) {
    return <HomePageSkeleton />;
  }

  if (!currentUser) {
    return <HomePageAccessRequired loadError={loadError} />;
  }

  const user = currentUser;

  const canManageGaiaUsers =
    (user.role === "admin" || user.role === "super_admin")
    && user.enabled_modules.includes("accessi")
    && hasSectionAccess(grantedSectionKeys, "accessi.users");
  const recentPresencePreview = presenceSummary.items.slice(0, 4);

  const visibleModules = allModules.filter((mod) => {
    if (mod.requiredRoles && !mod.requiredRoles.includes(user.role)) {
      return false;
    }
    if (mod.requiredSection && !hasSectionAccess(grantedSectionKeys, mod.requiredSection)) {
      return false;
    }
    if (mod.status === "coming") return true;
    if (mod.id === "me") return true;
    if (mod.id === "wiki") return true;
    return mod.enabledKeys.some((key) => hasUserModuleAccess(user, key));
  });
  const sortedVisibleModules = [...visibleModules].sort((a, b) =>
    a.title.replace("GAIA ", "").localeCompare(b.title.replace("GAIA ", ""), "it", { sensitivity: "base" }),
  );
  const canOpenGisPlatform = visibleModules.some((mod) => mod.id === "gis" && mod.status !== "coming");

  const latestRuoloStats = ruoloStats.items[0] ?? null;
  const latestRuoloYear = latestRuoloStats?.anno_tributario ?? ruoloAnalytics?.anno_tributario ?? catastoIndiciOverview?.anno_riferimento ?? null;
  const roleParcels =
    catastoIndiciOverview?.ruolo_reconciliation.particelle_ruolo_totali_count
    ?? ruoloAnalytics?.particelle_summary.total_particelle
    ?? 0;
  const roleDistrictKeys = new Set<string>();
  if (catastoIndiciOverview) {
    for (const item of catastoIndiciOverview.items) {
      for (const distretto of item.distretti ?? []) {
        if (isRuoloOperationalDistrict(distretto.num_distretto)) {
          roleDistrictKeys.add(distretto.num_distretto.trim().toUpperCase());
        }
      }
    }
  }
  const roleDistricts = catastoIndiciOverview
    ? roleDistrictKeys.size
    : ruoloAnalytics?.distretto_breakdown.filter((item) => isRuoloOperationalDistrict(item.key)).length ?? 0;
  const nasDataCount = dashboardSummary.nas_users + dashboardSummary.nas_groups + dashboardSummary.shares;
  const roleStatusStats = [
    {
      label: "Utenti in anagrafica",
      value: formatNumber(utenzeSummary.total_subjects),
      copy: `${formatNumber(utenzeSummary.active_subjects)} attivi nel modulo Utenze`,
      icon: "group",
    },
    {
      label: "Anagrafiche anomale",
      value: formatNumber(utenzeSummary.requires_review),
      copy: "Soggetti Utenze marcati per revisione",
      icon: "warning",
    },
    {
      label: "Ruoli caricati",
      value: formatNumber(ruoloStats.items.length),
      copy: "Annualità ruolo disponibili in GAIA",
      icon: "receipt_long",
    },
    {
      label: "Particelle a ruolo",
      value: formatNumber(roleParcels),
      copy: latestRuoloYear ? `Particelle distinte nel perimetro ruolo ${latestRuoloYear}` : "In attesa dati ruolo",
      icon: "map",
    },
    {
      label: "Distretti",
      value: formatNumber(roleDistricts),
      copy: "Distretti ruolo effettivi, escluso FD",
      icon: "account_tree",
    },
    {
      label: "Dati NAS",
      value: formatNumber(nasDataCount),
      copy: `${formatNumber(dashboardSummary.nas_users)} utenti, ${formatNumber(dashboardSummary.nas_groups)} gruppi, ${formatNumber(dashboardSummary.shares)} cartelle`,
      icon: "storage",
    },
  ];

  const statusBadge: Record<ModuleStatus, string> = {
    active: "bg-primary-fixed text-on-primary-fixed",
    warming: "bg-tertiary-fixed-dim text-on-tertiary-fixed-variant",
    coming: "bg-tertiary-fixed-dim text-on-tertiary-fixed-variant",
  };

  function renderSearchDropdown(surface: "topbar" | "hero") {
    if (!isSearchOpen || activeSearchSurface !== surface || !searchQuery.trim()) return null;
    const dropdownClassName =
      surface === "hero"
        ? "absolute left-0 right-0 mt-3 overflow-hidden rounded-3xl border border-surface-container bg-white shadow-xl"
        : "absolute right-0 mt-2 w-[min(42rem,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-surface-container bg-white shadow-lg";

    return (
      <div className={dropdownClassName}>
        <div className="max-h-[420px] overflow-auto py-2">
          {isOperationalSearchLoading ? (
            <div className="px-4 py-3 text-sm text-outline">Ricerca operativa in corso…</div>
          ) : null}
          {operationalSearchError ? (
            <div className="px-4 py-3 text-sm text-error">{operationalSearchError}</div>
          ) : null}
          {groupedOperationalResults.map(([module, items]) => (
            <div key={module} className="py-1">
              <p className="px-4 pb-1 pt-2 text-[11px] font-label uppercase tracking-[0.12em] text-outline">
                {moduleLabels[module] ?? module}
              </p>
              {items.map((item) => (
                <button
                  key={`${item.module}-${item.type}-${item.id}`}
                  type="button"
                  className="w-full px-4 py-2 text-left hover:bg-surface-container-low"
                  onClick={() => {
                    setIsSearchOpen(false);
                    router.push(item.href);
                  }}
                >
                  <span className="block text-sm font-medium text-gray-950">{item.title}</span>
                  <span className="block text-xs text-outline">{item.subtitle}</span>
                  {item.description ? (
                    <span className="mt-0.5 block text-xs text-on-surface-variant">{item.description}</span>
                  ) : null}
                </button>
              ))}
            </div>
          ))}
          {menuSearchResults.length > 0 ? (
            <div className="border-t border-surface-container py-1">
              <p className="px-4 pb-1 pt-2 text-[11px] font-label uppercase tracking-[0.12em] text-outline">
                Scorciatoie
              </p>
              {menuSearchResults.map((item) => (
                <button
                  key={item.href}
                  type="button"
                  className="w-full px-4 py-2 text-left text-sm text-gray-900 hover:bg-surface-container-low"
                  onClick={() => {
                    setIsSearchOpen(false);
                    router.push(item.href);
                  }}
                >
                  {item.label}
                </button>
              ))}
            </div>
          ) : null}
          {!isOperationalSearchLoading && groupedOperationalResults.length === 0 && menuSearchResults.length === 0 ? (
            <div className="px-4 py-3 text-sm text-outline">Nessun risultato disponibile per i permessi correnti.</div>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface text-on-surface font-body">
      {/* TopAppBar */}
      <header className="bg-surface fixed top-0 w-full z-50">
        <div className="flex justify-between items-center w-full px-8 py-3 max-w-full">
          <div className="flex items-center gap-12">
            <span className="font-headline text-xl font-bold italic text-primary">GAIA</span>
            <nav className="hidden md:flex gap-8">
              {sortedVisibleModules
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
            <div className="relative hidden lg:block" data-home-search>
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-sm pointer-events-none">
                search
              </span>
              <input
                className="bg-surface-container-high border-none rounded-lg pl-10 pr-4 py-2 text-sm focus:ring-1 focus:ring-primary w-56 transition-all outline-none"
                placeholder="Ricerca rapida…"
                type="text"
                value={searchQuery}
                onChange={(event) => {
                  setSearchQuery(event.target.value);
                  setActiveSearchSurface("topbar");
                  setIsSearchOpen(true);
                }}
                onFocus={() => {
                  setActiveSearchSurface("topbar");
                  setIsSearchOpen(true);
                }}
                onKeyDown={(event) => {
                  if (event.key === "Escape") {
                    setIsSearchOpen(false);
                  }
                  if (event.key === "Enter" && firstSearchHref) {
                    setIsSearchOpen(false);
                    router.push(firstSearchHref);
                  }
                }}
              />
              {renderSearchDropdown("topbar")}
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
      <main className="pt-24 pb-12 px-8 max-w-[90rem] mx-auto min-h-screen">
        {/* Hero */}
        <section className="mb-16 flex min-h-[58vh] flex-col items-center justify-center text-center">
          <div className="w-full max-w-4xl">
            <p className="mb-5 text-xs font-label uppercase tracking-[0.28em] text-outline">Hub operativo GAIA</p>
            <h1 className="font-headline text-7xl font-semibold italic leading-none text-[#123826] md:text-8xl">
              GAIA
            </h1>
            <p className="mx-auto mt-5 max-w-2xl text-lg font-body text-outline leading-relaxed">
              Cerca in utenze, ruolo e catasto da un unico punto: soggetti, codici fiscali,
              avvisi, fogli, particelle e documenti.
            </p>
            <div className="relative mx-auto mt-9 max-w-3xl" data-home-search>
              <span className="material-symbols-outlined absolute left-6 top-1/2 -translate-y-1/2 text-primary text-2xl pointer-events-none">
                search
              </span>
              <input
                className="w-full rounded-full border border-surface-container-high bg-white py-5 pl-16 pr-6 text-lg shadow-sm outline-none transition hover:shadow-md focus:border-primary focus:shadow-md focus:ring-2 focus:ring-primary/20"
                placeholder="Cerca utenza, ruolo, catasto…"
                type="text"
                value={searchQuery}
                onChange={(event) => {
                  setSearchQuery(event.target.value);
                  setActiveSearchSurface("hero");
                  setIsSearchOpen(true);
                }}
                onFocus={() => {
                  setActiveSearchSurface("hero");
                  setIsSearchOpen(true);
                }}
                onKeyDown={(event) => {
                  if (event.key === "Escape") {
                    setIsSearchOpen(false);
                  }
                  if (event.key === "Enter" && firstSearchHref) {
                    setIsSearchOpen(false);
                    router.push(firstSearchHref);
                  }
                }}
              />
              {renderSearchDropdown("hero")}
            </div>
            <div className="mt-6 flex flex-wrap justify-center gap-3 text-sm">
              {["Utenze", "Ruolo", "Catasto"].map((label) => (
                <span key={label} className="rounded-full bg-surface-container-low px-4 py-2 text-on-surface-variant">
                  {label}
                </span>
              ))}
            </div>
          </div>
        </section>

        <section className="mb-10 grid gap-4 xl:grid-cols-[minmax(0,1fr)_20rem]">
          <div className="rounded-3xl border border-surface-container-high bg-white/75 px-5 py-4 shadow-sm">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-center">
              <div className="shrink-0 text-left">
                <h2 className="text-sm font-label uppercase tracking-[0.18em] text-primary">Stato operativo</h2>
                <p className="mt-1 text-xs text-outline">Sintesi piattaforma e profilo corrente.</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {roleStatusStats.map((stat) => (
                  <div
                    key={`quick-${stat.label}`}
                    className="inline-flex items-center gap-2 rounded-full bg-surface-container-low px-3 py-2 text-sm text-on-surface-variant"
                    title={stat.copy}
                  >
                    <span className="material-symbols-outlined text-primary text-[17px]" aria-hidden="true">{stat.icon}</span>
                    <span className="text-outline">{stat.label}</span>
                    <span className="font-headline text-base font-semibold text-primary">{stat.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
          {canOpenGisPlatform ? (
            <Link
              href="/gis/catalogo"
              aria-label="Apri GIS Platform"
              className="group flex min-h-[104px] items-center justify-between overflow-hidden rounded-3xl border border-emerald-900/30 bg-[linear-gradient(135deg,#123826_0%,#173d2a_52%,#0f2c20_100%)] px-5 py-4 text-white shadow-sm transition hover:border-emerald-200/45 hover:shadow-md"
            >
              <div>
                <p className="text-xs font-label uppercase tracking-[0.18em] text-emerald-100/75">Mappa operativa</p>
                <h2 className="mt-1 text-2xl font-headline font-semibold">GIS Platform</h2>
                <p className="mt-1 text-sm text-emerald-50/80">Catalogo layer, particelle e viste geospaziali.</p>
              </div>
              <span
                className="material-symbols-outlined rounded-full bg-white/12 px-3 py-3 text-3xl text-white ring-1 ring-white/15 transition group-hover:translate-x-1 group-hover:bg-white/18"
                aria-hidden="true"
              >
                map
              </span>
            </Link>
          ) : null}
        </section>

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
                <span className="w-2 h-2 rounded-full bg-tertiary-fixed-dim" /> In sviluppo o non avviato
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {sortedVisibleModules.map((mod) => {
              const isInteractive = mod.status !== "coming";
              const card = (
                <article
                  className={cn(
                    "group bg-surface-container-lowest p-8 rounded-xl border border-outline-variant/15 transition-all duration-300 flex h-full flex-col justify-between relative overflow-hidden",
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
                    <p className="mb-2 text-[11px] font-label uppercase tracking-[0.18em] text-outline">{mod.eyebrow}</p>
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

              if (!isInteractive) return <div key={mod.id} className="h-full">{card}</div>;

              return (
                <Link
                  key={mod.id}
                  href={mod.href}
                  className="block h-full rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
                >
                  {card}
                </Link>
              );
            })}
          </div>
        </section>

        {canManageGaiaUsers ? (
          <section className="mt-10">
            <Link
              href="/gaia/users/attivita"
              className="block rounded-2xl bg-surface-container-low p-6 transition-all duration-300 hover:shadow-md"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-medium text-primary text-sm tracking-wide">Attività utenti GAIA</p>
                  <p className="mt-1 text-sm text-on-surface-variant">
                    Presenza applicativa recente basata su heartbeat, non online reale websocket.
                  </p>
                </div>
                <span className="material-symbols-outlined text-primary text-xl">groups</span>
              </div>
              <div className="mt-5 grid gap-3 sm:grid-cols-3">
                <div className="rounded-lg bg-white/80 px-4 py-3">
                  <p className="text-[11px] uppercase tracking-[0.12em] text-outline">Attivi {presenceSummary.window_minutes} min</p>
                  <p className="mt-1 text-2xl font-headline text-primary">{formatNumber(presenceSummary.active_users)}</p>
                </div>
                <div className="rounded-lg bg-white/80 px-4 py-3">
                  <p className="text-[11px] uppercase tracking-[0.12em] text-outline">Schede visibili</p>
                  <p className="mt-1 text-2xl font-headline text-primary">{formatNumber(presenceSummary.visible_users)}</p>
                </div>
                <div className="rounded-lg bg-white/80 px-4 py-3">
                  <p className="text-[11px] uppercase tracking-[0.12em] text-outline">Moduli coinvolti</p>
                  <p className="mt-1 text-2xl font-headline text-primary">{formatNumber(presenceSummary.by_module.length)}</p>
                </div>
              </div>
              <div className="mt-4 space-y-2">
                {recentPresencePreview.length === 0 ? (
                  <p className="text-sm text-outline">Nessuna attività rilevata nella finestra corrente.</p>
                ) : (
                  recentPresencePreview.map((item) => (
                    <div key={item.user_id} className="flex items-center justify-between gap-3 rounded-lg border border-white/70 bg-white/70 px-3 py-2">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-primary">{item.full_name || item.username}</p>
                        <p className="truncate text-xs text-outline">{item.route_label || item.path}</p>
                      </div>
                      <p className="shrink-0 text-xs text-outline">{item.minutes_since_last_seen} min fa</p>
                    </div>
                  ))
                )}
              </div>
              <div className="mt-4 flex items-center justify-end text-sm font-medium text-primary">
                Apri dettaglio
                <span className="material-symbols-outlined ml-2 text-[18px]">arrow_forward</span>
              </div>
            </Link>
          </section>
        ) : null}
      </main>

      <footer className="px-8 py-6 border-t border-outline-variant/20 max-w-[90rem] mx-auto flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-xs text-outline">
        <p>© GAIA platform · Consorzio di Bonifica dell&apos;Oristanese</p>
        <p>Sessione attiva: {currentUser.username} · {currentUser.role}</p>
      </footer>

      <WikiWelcomePopup />
    </div>
  );
}
