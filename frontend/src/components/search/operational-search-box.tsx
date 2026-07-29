"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { getStoredAccessToken } from "@/lib/auth";
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
  const [operationalSearchResults, setOperationalSearchResults] = useState<OperationalSearchResult[]>([]);
  const [isOperationalSearchLoading, setIsOperationalSearchLoading] = useState(false);
  const [operationalSearchError, setOperationalSearchError] = useState<string | null>(null);
  const isHero = variant === "hero";

  const menuSearchResults = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return [];

    const userRole = currentUser.role;
    const isAdmin = userRole === "admin" || userRole === "super_admin";

    function isRouteAllowed(route: SearchRoute): boolean {
      if (route.requiredRoles && !route.requiredRoles.includes(userRole)) return false;
      if (route.requiredSection && !hasSectionAccess(grantedSectionKeys, route.requiredSection)) return false;
      if (!route.moduleKey) return true;
      if (isAdmin) return true;
      return hasUserModuleAccess(currentUser, route.moduleKey);
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
  }, [searchQuery]);

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
    return Object.entries(groups);
  }, [operationalSearchResults]);

  const firstSearchHref = operationalSearchResults[0]?.href ?? menuSearchResults[0]?.href;
  const placeholder = isHero ? "Cerca utenza, ruolo, catasto…" : "Cerca in GAIA…";

  function navigateTo(href: string): void {
    setIsSearchOpen(false);
    router.push(href);
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
          {!isOperationalSearchLoading && groupedOperationalResults.length === 0 && menuSearchResults.length === 0 ? (
            <div className="px-4 py-3 text-sm text-outline">Nessun risultato disponibile per i permessi correnti.</div>
          ) : null}
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
          if (event.key === "Enter" && firstSearchHref) {
            navigateTo(firstSearchHref);
          }
        }}
      />
      {!isHero ? (
        <span className="pointer-events-none absolute right-2 top-1/2 hidden -translate-y-1/2 rounded-md border border-gray-200 bg-white px-1.5 py-0.5 text-[10px] font-medium text-gray-400 xl:inline">
          Ctrl K
        </span>
      ) : null}
      {renderDropdown()}
    </div>
  );
}
