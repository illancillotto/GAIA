"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { getStoredAccessToken } from "@/lib/auth";
import { buildCatastoGisCoordinateHref } from "@/lib/catasto-gis-coordinate-search";
import { cn } from "@/lib/cn";
import { hasUserModuleAccess } from "@/lib/module-access";
import { searchOperational } from "@/lib/operational-search-api";
import { hasSectionAccess } from "@/lib/section-access";
import type { CurrentUser, OperationalSearchResult } from "@/types/api";

type SearchRoute = {
  label: string;
  href: string;
  moduleKey?: string;
  requiredSection?: string;
  requiredRoles?: string[];
  keywords?: string[];
};

type OperationalSearchBoxProps = {
  currentUser: CurrentUser;
  grantedSectionKeys: string[];
  variant: "hero" | "compact";
  autoFocus?: boolean;
  enableHotkey?: boolean;
  className?: string;
};

const menuSearchRoutes: SearchRoute[] = [
  { label: "La mia attività · Panoramica", href: "/me", keywords: ["me", "attivita", "presenze", "self service"] },
  { label: "La mia attività · Presenze", href: "/me/presenze", keywords: ["presenze", "giornaliere"] },
  { label: "La mia attività · Operatività", href: "/me/operativita", keywords: ["operativita", "attivita", "segnalazioni", "pratiche"] },
  { label: "La mia attività · Dotazioni", href: "/me/dotazioni", keywords: ["dotazioni", "dispositivi", "mezzi"] },
  { label: "La mia attività · Anomalie", href: "/me/anomalie", keywords: ["anomalie", "warning"] },
  { label: "NAS Control · Dashboard", href: "/nas-control", moduleKey: "accessi", keywords: ["nas", "accessi"] },
  { label: "NAS Control · Sincronizzazione", href: "/nas-control/sync", moduleKey: "accessi", keywords: ["sync", "sincronizzazione"] },
  { label: "NAS Control · Utenti", href: "/nas-control/users", moduleKey: "accessi", requiredSection: "accessi.users", keywords: ["utenti", "users"] },
  { label: "NAS Control · Gruppi", href: "/nas-control/groups", moduleKey: "accessi", keywords: ["gruppi", "groups"] },
  { label: "NAS Control · Cartelle condivise", href: "/nas-control/shares", moduleKey: "accessi", keywords: ["shares", "cartelle"] },
  { label: "NAS Control · Permessi effettivi", href: "/nas-control/effective-permissions", moduleKey: "accessi", keywords: ["permessi", "effective"] },
  { label: "NAS Control · Review NAS", href: "/nas-control/reviews", moduleKey: "accessi", keywords: ["review", "validazione"] },
  { label: "NAS Control · Report", href: "/nas-control/reports", moduleKey: "accessi", keywords: ["report"] },
  { label: "Elaborazioni · Dashboard", href: "/elaborazioni", moduleKey: "elaborazioni", requiredRoles: ["super_admin"], keywords: ["batch"] },
  { label: "Elaborazioni · WhiteCompany Sync", href: "/elaborazioni/bonifica", moduleKey: "elaborazioni", requiredRoles: ["super_admin"], keywords: ["white", "bonifica", "sync"] },
  { label: "Elaborazioni · Presenze INAZ Sync", href: "/elaborazioni/presenze-sync", moduleKey: "presenze", keywords: ["sync", "portale", "inaz", "giornaliere"] },
  { label: "Elaborazioni · Visure", href: "/elaborazioni/visure", moduleKey: "elaborazioni", requiredRoles: ["super_admin"], keywords: ["visure"] },
  { label: "Elaborazioni · Capacitas", href: "/elaborazioni/capacitas", moduleKey: "elaborazioni", requiredRoles: ["super_admin"], keywords: ["capacitas"] },
  { label: "Elaborazioni · Poste Online", href: "/elaborazioni/posta-online", moduleKey: "elaborazioni", requiredRoles: ["super_admin"], keywords: ["poste", "posta online", "raccomandate"] },
  { label: "Elaborazioni · GAIA Mobile Sync", href: "/elaborazioni/gaia-mobile-sync", moduleKey: "elaborazioni", requiredRoles: ["super_admin"], keywords: ["gaia mobile", "mobile sync", "gateway"] },
  { label: "Elaborazioni · Credenziali", href: "/elaborazioni/settings", moduleKey: "elaborazioni", requiredRoles: ["super_admin"], keywords: ["credenziali", "settings"] },
  { label: "Wiki · Documentazione e assistente", href: "/wiki", keywords: ["wiki", "documentazione", "assistente"] },
  { label: "Wiki · Supporto", href: "/wiki/support", keywords: ["wiki", "supporto", "anomalia", "feature", "richiesta", "bug"] },
  { label: "Wiki · Inbox supporto", href: "/wiki/support/inbox", keywords: ["wiki", "supporto", "inbox", "triage", "anomalia", "accesso", "dati"] },
  { label: "Wiki · Analytics supporto", href: "/wiki/support/analytics", keywords: ["wiki", "supporto", "analytics", "trend", "feature request", "bug"] },
  { label: "Wiki · Richieste", href: "/wiki/requests", keywords: ["wiki", "richieste", "feature request", "bug report"] },
  { label: "Presenze · Dashboard", href: "/presenze", moduleKey: "presenze", keywords: ["giornaliere", "cartellino", "presenze"] },
  { label: "Presenze · Collaboratori", href: "/presenze/collaboratori", moduleKey: "presenze", keywords: ["collaboratori", "dipendenti"] },
  { label: "Presenze · Giornaliere", href: "/presenze/giornaliere", moduleKey: "presenze", keywords: ["giornaliere", "presenze"] },
  { label: "Presenze · Organigramma", href: "/presenze/organigramma", moduleKey: "presenze", keywords: ["organigramma", "gerarchia", "capi settore", "permessi"] },
  { label: "Presenze · Export", href: "/presenze/export", moduleKey: "presenze", keywords: ["export", "xlsm"] },
  { label: "Presenze · Banca ore", href: "/presenze/banca-ore", moduleKey: "presenze", keywords: ["banca ore", "liquidazioni", "saldo ore"] },
  { label: "GIS Platform · Catalogo", href: "/gis/catalogo", moduleKey: "gis", keywords: ["gis", "catalogo", "layer", "postgis", "martin"] },
  { label: "Catasto · Dashboard", href: "/catasto", moduleKey: "catasto" },
  { label: "Catasto · GIS", href: "/catasto/gis", moduleKey: "catasto", keywords: ["gis", "mappa", "coordinate", "latitudine", "longitudine"] },
  { label: "Catasto · Distretti", href: "/catasto/distretti", moduleKey: "catasto", keywords: ["distretti"] },
  { label: "Catasto · Particelle", href: "/catasto/particelle", moduleKey: "catasto", keywords: ["mappali", "terreni"] },
  { label: "Catasto · Contatori irrigui", href: "/catasto/letture-contatori", moduleKey: "catasto", keywords: ["letture contatori", "contatori", "gate mobile", "mobile", "gps", "foto"] },
  { label: "Catasto · Anomalie", href: "/catasto/anomalie", moduleKey: "catasto", keywords: ["errori"] },
  { label: "Catasto · Import", href: "/catasto/import", moduleKey: "catasto", keywords: ["caricamento"] },
  { label: "Catasto · Archivio documenti", href: "/catasto/archive", moduleKey: "catasto", keywords: ["documenti"] },
  { label: "Rete · Dashboard", href: "/network", moduleKey: "rete" },
  { label: "Rete · Dispositivi", href: "/network/devices", moduleKey: "rete", keywords: ["switch", "ap", "devices"] },
  { label: "Rete · Firewall", href: "/network/firewalls", moduleKey: "rete", keywords: ["sophos", "xgs", "syslog", "snmp"] },
  { label: "Rete · Statistiche", href: "/network/statistics", moduleKey: "rete", keywords: ["analytics", "traffico", "navigazione"] },
  { label: "Rete · Planimetria", href: "/network/floor-plan", moduleKey: "rete", keywords: ["mappa", "planimetria"] },
  { label: "Rete · Alert", href: "/network/alerts", moduleKey: "rete", keywords: ["allarmi"] },
  { label: "Rete · Scansioni", href: "/network/scans", moduleKey: "rete", keywords: ["scan", "scansioni"] },
  { label: "Utenze · Dashboard", href: "/utenze", moduleKey: "utenze" },
  { label: "Utenze · Soggetti", href: "/utenze/import#utenze-soggetti", moduleKey: "utenze", keywords: ["anagrafica", "subjects"] },
  { label: "Utenze · Import dati", href: "/utenze/import", moduleKey: "utenze", keywords: ["import"] },
  { label: "Operazioni · Dashboard", href: "/operazioni", moduleKey: "operazioni" },
  { label: "Operazioni · Analisi operazioni", href: "/operazioni/analisi", moduleKey: "operazioni", keywords: ["analisi"] },
  { label: "Operazioni · Operatori", href: "/operazioni/operatori", moduleKey: "operazioni" },
  { label: "Operazioni · Carte carburante", href: "/operazioni/carte-carburante", moduleKey: "operazioni", keywords: ["fuel", "carburante"] },
  { label: "Operazioni · Mezzi", href: "/operazioni/mezzi", moduleKey: "operazioni", keywords: ["veicoli", "automezzi"] },
  { label: "Operazioni · Attività", href: "/operazioni/attivita", moduleKey: "operazioni" },
  { label: "Operazioni · Cruscotto segnalazioni", href: "/operazioni/segnalazioni/cruscotto", moduleKey: "operazioni", keywords: ["cruscotto"] },
  { label: "Operazioni · Segnalazioni", href: "/operazioni/segnalazioni", moduleKey: "operazioni" },
  { label: "Operazioni · Pratiche", href: "/operazioni/pratiche", moduleKey: "operazioni" },
  { label: "Riordino · Dashboard", href: "/riordino", moduleKey: "riordino" },
  { label: "Riordino · Pratiche", href: "/riordino/pratiche", moduleKey: "riordino" },
  { label: "Riordino · Configurazione", href: "/riordino/configurazione", moduleKey: "riordino", keywords: ["settings"] },
  { label: "Ruolo · Dashboard", href: "/ruolo", moduleKey: "ruolo" },
  { label: "Ruolo · Avvisi", href: "/ruolo/avvisi", moduleKey: "ruolo" },
  { label: "Ruolo · Particelle", href: "/ruolo/particelle", moduleKey: "ruolo", requiredSection: "ruolo.avvisi", keywords: ["particelle", "mappali", "ruolo"] },
  { label: "Ruolo · Statistiche", href: "/ruolo/stats", moduleKey: "ruolo", keywords: ["analytics"] },
  { label: "Ruolo · Storico workflow", href: "/ruolo/import", moduleKey: "ruolo", keywords: ["ruolo", "storico", "incass"] },
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

const moduleLabels: Record<string, string> = {
  utenze: "Utenze",
  ruolo: "Ruolo",
  catasto: "Catasto",
};
const operationalSearchModuleOrder = ["utenze", "ruolo", "catasto"];

function searchPageHref(query: string): string {
  return `/search?q=${encodeURIComponent(query.trim())}`;
}

function buildCoordinateSearchRoute(query: string, currentUser: CurrentUser): SearchRoute | null {
  const href = buildCatastoGisCoordinateHref(query);
  if (!href || !hasUserModuleAccess(currentUser, "catasto")) return null;
  return {
    label: "Catasto · GIS coordinate",
    href,
    moduleKey: "catasto",
    keywords: ["coordinate", "latitudine", "longitudine", "dms"],
  };
}

function canShowMenuSearchRoute(route: SearchRoute, currentUser: CurrentUser, grantedSectionKeys: string[]): boolean {
  const userRole = currentUser.role;
  const isAdmin = userRole === "admin" || userRole === "super_admin";
  if (route.requiredRoles && !route.requiredRoles.includes(userRole)) return false;
  if (route.requiredSection && !hasSectionAccess(grantedSectionKeys, route.requiredSection)) return false;
  if (!route.moduleKey) return true;
  if (isAdmin) return true;
  return hasUserModuleAccess(currentUser, route.moduleKey);
}

function scoreMenuSearchRoute(route: SearchRoute, query: string): number {
  const haystack = [route.label, ...(route.keywords ?? [])].join(" ").toLowerCase();
  if (haystack === query) return 100;
  if (route.label.toLowerCase().startsWith(query)) return 80;
  if (haystack.includes(query)) return 60;
  return 0;
}

function buildMenuSearchResults(query: string, currentUser: CurrentUser, grantedSectionKeys: string[]): SearchRoute[] {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) return [];
  const coordinateRoute = buildCoordinateSearchRoute(query, currentUser);
  const routes = menuSearchRoutes
    .filter((route) => canShowMenuSearchRoute(route, currentUser, grantedSectionKeys))
    .map((route) => ({ route, score: scoreMenuSearchRoute(route, normalizedQuery) }))
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score || a.route.label.localeCompare(b.route.label))
    .slice(0, 10)
    .map((item) => item.route);
  return coordinateRoute ? [coordinateRoute, ...routes] : routes;
}

function directSearchHrefForEnter(
  query: string,
  currentUser: CurrentUser,
  operationalResults: OperationalSearchResult[],
  menuResults: SearchRoute[],
): string | null {
  const coordinateHref = buildCatastoGisCoordinateHref(query);
  if (coordinateHref && hasUserModuleAccess(currentUser, "catasto")) return coordinateHref;
  const resultCount = operationalResults.length + menuResults.length;
  if (resultCount !== 1) return null;
  return operationalResults[0]?.href ?? menuResults[0].href;
}

export function OperationalSearchBox({
  currentUser,
  grantedSectionKeys,
  variant,
  autoFocus = false,
  enableHotkey = false,
  className,
}: OperationalSearchBoxProps) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isResultsModalOpen, setIsResultsModalOpen] = useState(false);
  const [operationalSearchResults, setOperationalSearchResults] = useState<OperationalSearchResult[]>([]);
  const [isOperationalSearchLoading, setIsOperationalSearchLoading] = useState(false);
  const [operationalSearchError, setOperationalSearchError] = useState<string | null>(null);
  const isHero = variant === "hero";

  const menuSearchResults = useMemo(() => {
    return buildMenuSearchResults(searchQuery, currentUser, grantedSectionKeys);
  }, [currentUser, grantedSectionKeys, searchQuery]);

  useEffect(() => {
    const token = getStoredAccessToken();
    const query = searchQuery.trim();

    if (!token || query.length < 2) {
      setOperationalSearchResults([]);
      setIsOperationalSearchLoading(false);
      setOperationalSearchError(null);
      return;
    }

    let cancelled = false;
    setIsOperationalSearchLoading(true);
    setOperationalSearchError(null);

    const timeoutId = window.setTimeout(() => {
      searchOperational(token, query, { limit: isResultsModalOpen ? 30 : 8 })
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
  }, [isResultsModalOpen, searchQuery]);

  useEffect(() => {
    function handleDocumentClick(event: MouseEvent) {
      const target = event.target as Node | null;
      /* v8 ignore next -- browser-dispatched mouse events always provide a target. */
      if (!target) return;
      if (target instanceof Element && !target.closest("[data-operational-search]")) {
        setIsSearchOpen(false);
      }
    }
    document.addEventListener("mousedown", handleDocumentClick);
    return () => document.removeEventListener("mousedown", handleDocumentClick);
  }, []);

  useEffect(() => {
    if (!enableHotkey) return;

    function handleShortcut(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        inputRef.current?.focus();
        setIsSearchOpen(true);
      }
    }

    document.addEventListener("keydown", handleShortcut);
    return () => document.removeEventListener("keydown", handleShortcut);
  }, [enableHotkey]);

  const groupedOperationalResults = useMemo(() => {
    const groups: Record<string, OperationalSearchResult[]> = {};
    for (const item of operationalSearchResults) {
      groups[item.module] = [...(groups[item.module] ?? []), item];
    }
    return Object.entries(groups).sort(([left], [right]) => operationalSearchModuleOrder.indexOf(left) - operationalSearchModuleOrder.indexOf(right));
  }, [operationalSearchResults]);

  const placeholder = isHero ? "Cerca utenza, ruolo, catasto o coordinate…" : "Cerca in GAIA…";
  const normalizedQuery = searchQuery.trim();
  const resultCount = operationalSearchResults.length + menuSearchResults.length;
  const shouldShowResultsModal = normalizedQuery.length >= 2 && resultCount !== 1;

  function navigateTo(href: string): void {
    setIsSearchOpen(false);
    setIsResultsModalOpen(false);
    router.push(href);
  }

  function openResultsModal(): void {
    setIsSearchOpen(false);
    setIsResultsModalOpen(true);
  }

  function navigateFromEnter(): void {
    if (!normalizedQuery) return;
    const directHref = directSearchHrefForEnter(normalizedQuery, currentUser, operationalSearchResults, menuSearchResults);
    if (directHref) return navigateTo(directHref);
    openResultsModal();
  }

  function renderDropdown() {
    if (!isSearchOpen || !searchQuery.trim()) return null;
    const dropdownClassName = isHero
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
                  onClick={() => navigateTo(item.href)}
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
                  onClick={() => navigateTo(item.href)}
                >
                  {item.label}
                </button>
              ))}
            </div>
          ) : null}
          {shouldShowResultsModal ? (
            <div className="border-t border-surface-container px-3 py-2">
              <button
                type="button"
                className="flex w-full items-center justify-between rounded-xl bg-primary px-3 py-2 text-left text-sm font-medium text-white transition hover:bg-primary/90"
                onClick={openResultsModal}
              >
                <span>Vedi tutti i risultati</span>
                <span className="material-symbols-outlined text-[18px]" aria-hidden="true">arrow_forward</span>
              </button>
            </div>
          ) : null}
          {!isOperationalSearchLoading && groupedOperationalResults.length === 0 && menuSearchResults.length === 0 ? (
            <div className="px-4 py-3 text-sm text-outline">Nessun risultato disponibile per i permessi correnti.</div>
          ) : null}
        </div>
      </div>
    );
  }

  function renderResultsModal() {
    if (!isResultsModalOpen) return null;

    return (
      <div className="fixed inset-0 z-50 flex items-start justify-center px-4 py-8 sm:py-14" role="dialog" aria-modal="true" aria-labelledby="operational-search-modal-title">
        <button
          type="button"
          className="absolute inset-0 bg-[#0f261c]/55 backdrop-blur-sm"
          aria-label="Chiudi risultati ricerca"
          onClick={() => setIsResultsModalOpen(false)}
        />
        <div className="relative z-10 w-full max-w-5xl overflow-hidden rounded-[2rem] border border-white/60 bg-white shadow-2xl">
          <div className="border-b border-surface-container bg-gradient-to-r from-[#f2fbf6] via-white to-[#f9f2df] px-6 py-5">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div>
                <p className="text-[11px] font-label uppercase tracking-[0.18em] text-primary">Ricerca operativa</p>
                <h2 id="operational-search-modal-title" className="mt-2 font-headline text-3xl font-semibold text-[#123826]">
                  Risultati per “{normalizedQuery}”
                </h2>
                <p className="mt-1 text-sm text-outline">
                  Seleziona un risultato senza uscire dalla ricerca, oppure apri la vista estesa.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="rounded-full border border-primary/20 bg-white px-4 py-2 text-sm font-medium text-primary transition hover:bg-primary/5"
                  onClick={() => navigateTo(searchPageHref(normalizedQuery))}
                >
                  Vista estesa
                </button>
                <button
                  type="button"
                  className="grid size-10 place-items-center rounded-full bg-white text-on-surface-variant shadow-sm transition hover:text-primary"
                  aria-label="Chiudi modal ricerca"
                  onClick={() => setIsResultsModalOpen(false)}
                >
                  <span className="material-symbols-outlined text-[20px]" aria-hidden="true">close</span>
                </button>
              </div>
            </div>
          </div>
          <div className="max-h-[min(70vh,42rem)] overflow-auto px-6 py-5">
            {isOperationalSearchLoading ? (
              <div className="rounded-2xl bg-surface-container-low px-4 py-3 text-sm text-outline">Ricerca operativa in corso…</div>
            ) : null}
            {operationalSearchError ? (
              <div className="rounded-2xl bg-error/10 px-4 py-3 text-sm text-error">{operationalSearchError}</div>
            ) : null}
            {groupedOperationalResults.length > 0 ? (
              <div className="grid gap-4 md:grid-cols-3">
                {groupedOperationalResults.map(([module, items]) => (
                  <section key={module} className="rounded-3xl border border-surface-container bg-surface-container-low/50 p-3">
                    <h3 className="px-2 pb-2 text-[11px] font-label uppercase tracking-[0.14em] text-primary">
                      {moduleLabels[module] ?? module}
                    </h3>
                    <div className="space-y-2">
                      {items.map((item) => (
                        <button
                          key={`${item.module}-${item.type}-${item.id}`}
                          type="button"
                          className="w-full rounded-2xl bg-white px-3 py-3 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
                          onClick={() => navigateTo(item.href)}
                        >
                          <span className="block text-sm font-semibold text-gray-950">{item.title}</span>
                          <span className="mt-1 block text-xs text-outline">{item.subtitle}</span>
                          {item.description ? (
                            <span className="mt-1 block text-xs text-on-surface-variant">{item.description}</span>
                          ) : null}
                        </button>
                      ))}
                    </div>
                  </section>
                ))}
              </div>
            ) : null}
            {menuSearchResults.length > 0 ? (
              <section className="mt-5 rounded-3xl border border-surface-container bg-white p-3">
                <h3 className="px-2 pb-2 text-[11px] font-label uppercase tracking-[0.14em] text-outline">Scorciatoie</h3>
                <div className="grid gap-2 md:grid-cols-2">
                  {menuSearchResults.map((item) => (
                    <button
                      key={item.href}
                      type="button"
                      className="rounded-2xl bg-surface-container-low px-3 py-3 text-left text-sm font-medium text-gray-900 transition hover:bg-primary/10 hover:text-primary"
                      onClick={() => navigateTo(item.href)}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </section>
            ) : null}
            {!isOperationalSearchLoading && groupedOperationalResults.length === 0 && menuSearchResults.length === 0 ? (
              <div className="rounded-2xl bg-surface-container-low px-4 py-4 text-sm text-outline">
                Nessun risultato disponibile per i permessi correnti.
              </div>
            ) : null}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("relative", className)} data-operational-search>
      <span
        className={cn(
          "material-symbols-outlined pointer-events-none absolute top-1/2 -translate-y-1/2",
          isHero ? "left-6 text-2xl text-primary" : "left-4 text-lg text-primary",
        )}
      >
        search
      </span>
      <input
        ref={inputRef}
        autoFocus={autoFocus}
        className={cn(
          "outline-none transition",
          isHero
            ? "w-full rounded-full border border-surface-container-high bg-white py-5 pl-16 pr-6 text-lg shadow-sm hover:shadow-md focus:border-primary focus:shadow-md focus:ring-2 focus:ring-primary/20"
            : "w-full rounded-2xl border border-primary/20 bg-primary/5 py-2.5 pl-11 pr-24 text-sm font-medium text-gray-950 shadow-sm placeholder:text-primary/60 hover:border-primary/35 hover:bg-white focus:border-primary focus:bg-white focus:ring-2 focus:ring-primary/15",
        )}
        placeholder={placeholder}
        type="text"
        value={searchQuery}
        onChange={(event) => {
          setSearchQuery(event.target.value);
          setIsSearchOpen(true);
        }}
        onFocus={() => setIsSearchOpen(true)}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            setIsSearchOpen(false);
          }
          if (event.key === "Enter") {
            navigateFromEnter();
          }
        }}
      />
      {!isHero ? (
        <span className="pointer-events-none absolute right-2 top-1/2 hidden -translate-y-1/2 rounded-md border border-gray-200 bg-white px-1.5 py-0.5 text-[10px] font-medium text-gray-400 xl:inline">
          Ctrl K
        </span>
      ) : null}
      {renderDropdown()}
      {renderResultsModal()}
    </div>
  );
}
