export type PresenceRouteMeta = {
  moduleKey: string;
  routeLabel: string;
};

const ROUTE_RULES: Array<{ prefix: string; moduleKey: string; routeLabel: string }> = [
  { prefix: "/gaia/users/operatori-cruscotto", moduleKey: "gaia", routeLabel: "Utenti GAIA / Cruscotto operatori" },
  { prefix: "/gaia/users/attivita", moduleKey: "gaia", routeLabel: "Utenti GAIA / Attivita utenti" },
  { prefix: "/gaia/users", moduleKey: "gaia", routeLabel: "Utenti GAIA" },
  { prefix: "/nas-control/sync", moduleKey: "accessi", routeLabel: "NAS Control / Sincronizzazione" },
  { prefix: "/nas-control/users", moduleKey: "accessi", routeLabel: "NAS Control / Utenti" },
  { prefix: "/nas-control/groups", moduleKey: "accessi", routeLabel: "NAS Control / Gruppi" },
  { prefix: "/nas-control/shares", moduleKey: "accessi", routeLabel: "NAS Control / Cartelle condivise" },
  { prefix: "/nas-control/effective-permissions", moduleKey: "accessi", routeLabel: "NAS Control / Permessi effettivi" },
  { prefix: "/nas-control/reviews", moduleKey: "accessi", routeLabel: "NAS Control / Review" },
  { prefix: "/nas-control/reports", moduleKey: "accessi", routeLabel: "NAS Control / Report" },
  { prefix: "/nas-control", moduleKey: "accessi", routeLabel: "NAS Control" },
  { prefix: "/network/devices", moduleKey: "rete", routeLabel: "Rete / Dispositivi" },
  { prefix: "/network/firewalls", moduleKey: "rete", routeLabel: "Rete / Firewall" },
  { prefix: "/network/tracking", moduleKey: "rete", routeLabel: "Rete / Tracking" },
  { prefix: "/network/vpn-bypass", moduleKey: "rete", routeLabel: "Rete / VPN Bypass" },
  { prefix: "/network/statistics", moduleKey: "rete", routeLabel: "Rete / Statistiche" },
  { prefix: "/network/floor-plan", moduleKey: "rete", routeLabel: "Rete / Planimetria" },
  { prefix: "/network/alerts", moduleKey: "rete", routeLabel: "Rete / Alert" },
  { prefix: "/network/scans", moduleKey: "rete", routeLabel: "Rete / Scansioni" },
  { prefix: "/network/sophos", moduleKey: "rete", routeLabel: "Rete / Sophos" },
  { prefix: "/network", moduleKey: "rete", routeLabel: "Rete" },
  { prefix: "/inventory", moduleKey: "inventario", routeLabel: "Inventario" },
  { prefix: "/catasto/gis", moduleKey: "catasto", routeLabel: "Catasto / GIS" },
  { prefix: "/catasto/distretti", moduleKey: "catasto", routeLabel: "Catasto / Distretti" },
  { prefix: "/catasto/particelle", moduleKey: "catasto", routeLabel: "Catasto / Particelle" },
  { prefix: "/catasto/letture-contatori", moduleKey: "catasto", routeLabel: "Catasto / Contatori irrigui" },
  { prefix: "/catasto/anomalie", moduleKey: "catasto", routeLabel: "Catasto / Anomalie" },
  { prefix: "/catasto/import", moduleKey: "catasto", routeLabel: "Catasto / Import" },
  { prefix: "/catasto/archive", moduleKey: "catasto", routeLabel: "Catasto / Archivio documenti" },
  { prefix: "/catasto", moduleKey: "catasto", routeLabel: "Catasto" },
  { prefix: "/utenze/import", moduleKey: "utenze", routeLabel: "Utenze / Import dati" },
  { prefix: "/utenze/visure-routing-anomalies", moduleKey: "utenze", routeLabel: "Utenze / Anomalie visure" },
  { prefix: "/utenze", moduleKey: "utenze", routeLabel: "Utenze" },
  { prefix: "/anagrafica", moduleKey: "utenze", routeLabel: "Utenze / ANPR" },
  { prefix: "/operazioni/miniapp/liste", moduleKey: "operazioni", routeLabel: "Operazioni / Miniapp liste" },
  { prefix: "/operazioni/attivita-contatori", moduleKey: "operazioni", routeLabel: "Operazioni / Attivita contatori" },
  { prefix: "/operazioni/attivita/", moduleKey: "operazioni", routeLabel: "Operazioni / Dettaglio attivita" },
  { prefix: "/operazioni/attivita", moduleKey: "operazioni", routeLabel: "Operazioni / Attivita" },
  { prefix: "/operazioni/analisi", moduleKey: "operazioni", routeLabel: "Operazioni / Analisi" },
  { prefix: "/operazioni/operatori", moduleKey: "operazioni", routeLabel: "Operazioni / Operatori" },
  { prefix: "/operazioni/carte-carburante", moduleKey: "operazioni", routeLabel: "Operazioni / Carte carburante" },
  { prefix: "/operazioni/mezzi", moduleKey: "operazioni", routeLabel: "Operazioni / Mezzi" },
  { prefix: "/operazioni/segnalazioni/cruscotto", moduleKey: "operazioni", routeLabel: "Operazioni / Cruscotto segnalazioni" },
  { prefix: "/operazioni/segnalazioni", moduleKey: "operazioni", routeLabel: "Operazioni / Segnalazioni" },
  { prefix: "/operazioni/pratiche", moduleKey: "operazioni", routeLabel: "Operazioni / Pratiche" },
  { prefix: "/operazioni", moduleKey: "operazioni", routeLabel: "Operazioni" },
  { prefix: "/riordino/pratiche", moduleKey: "riordino", routeLabel: "Riordino / Pratiche" },
  { prefix: "/riordino/configurazione", moduleKey: "riordino", routeLabel: "Riordino / Configurazione" },
  { prefix: "/riordino", moduleKey: "riordino", routeLabel: "Riordino" },
  { prefix: "/ruolo/avvisi/", moduleKey: "ruolo", routeLabel: "Ruolo / Dettaglio avviso" },
  { prefix: "/ruolo/avvisi", moduleKey: "ruolo", routeLabel: "Ruolo / Avvisi" },
  { prefix: "/ruolo/particelle", moduleKey: "ruolo", routeLabel: "Ruolo / Particelle" },
  { prefix: "/ruolo/stats", moduleKey: "ruolo", routeLabel: "Ruolo / Statistiche" },
  { prefix: "/ruolo/import", moduleKey: "ruolo", routeLabel: "Ruolo / Storico workflow" },
  { prefix: "/ruolo/calcolo-gaia", moduleKey: "ruolo", routeLabel: "Ruolo / Calcolo GAIA" },
  { prefix: "/ruolo", moduleKey: "ruolo", routeLabel: "Ruolo" },
  { prefix: "/presenze/collaboratori", moduleKey: "presenze", routeLabel: "Giornaliere / Collaboratori" },
  { prefix: "/presenze/giornaliere", moduleKey: "presenze", routeLabel: "Giornaliere / Giornaliere" },
  { prefix: "/presenze/organigramma", moduleKey: "presenze", routeLabel: "Giornaliere / Organigramma" },
  { prefix: "/presenze/export", moduleKey: "presenze", routeLabel: "Giornaliere / Export" },
  { prefix: "/presenze/banca-ore", moduleKey: "presenze", routeLabel: "Giornaliere / Banca ore" },
  { prefix: "/presenze/sync", moduleKey: "presenze", routeLabel: "Giornaliere / Sync" },
  { prefix: "/presenze/anomalie", moduleKey: "presenze", routeLabel: "Giornaliere / Anomalie" },
  { prefix: "/presenze/configurazione", moduleKey: "presenze", routeLabel: "Giornaliere / Configurazione" },
  { prefix: "/presenze/recuperi", moduleKey: "presenze", routeLabel: "Giornaliere / Recuperi" },
  { prefix: "/presenze/assegnazione-territoriale", moduleKey: "presenze", routeLabel: "Giornaliere / Assegnazione territoriale" },
  { prefix: "/presenze", moduleKey: "presenze", routeLabel: "Giornaliere" },
  { prefix: "/organigramma", moduleKey: "organigramma", routeLabel: "Organigramma" },
  { prefix: "/wiki/support/inbox", moduleKey: "wiki", routeLabel: "Wiki / Inbox supporto" },
  { prefix: "/wiki/support/analytics", moduleKey: "wiki", routeLabel: "Wiki / Analytics supporto" },
  { prefix: "/wiki/support", moduleKey: "wiki", routeLabel: "Wiki / Supporto" },
  { prefix: "/wiki/requests/", moduleKey: "wiki", routeLabel: "Wiki / Dettaglio richiesta" },
  { prefix: "/wiki/requests", moduleKey: "wiki", routeLabel: "Wiki / Richieste" },
  { prefix: "/wiki/audit", moduleKey: "wiki", routeLabel: "Wiki / Audit" },
  { prefix: "/wiki/telemetry", moduleKey: "wiki", routeLabel: "Wiki / Telemetry" },
  { prefix: "/wiki/conversations/analytics", moduleKey: "wiki", routeLabel: "Wiki / Analytics conversazioni" },
  { prefix: "/wiki/conversations/settings", moduleKey: "wiki", routeLabel: "Wiki / Configurazione conversazioni" },
  { prefix: "/wiki/conversations", moduleKey: "wiki", routeLabel: "Wiki / Conversazioni" },
  { prefix: "/wiki", moduleKey: "wiki", routeLabel: "Wiki" },
  { prefix: "/elaborazioni/bonifica", moduleKey: "elaborazioni", routeLabel: "Elaborazioni / WhiteCompany Sync" },
  { prefix: "/elaborazioni/anpr", moduleKey: "elaborazioni", routeLabel: "Elaborazioni / ANPR batch" },
  { prefix: "/elaborazioni/visure", moduleKey: "elaborazioni", routeLabel: "Elaborazioni / Visure" },
  { prefix: "/elaborazioni/capacitas", moduleKey: "elaborazioni", routeLabel: "Elaborazioni / Capacitas" },
  { prefix: "/elaborazioni/ade-alignment", moduleKey: "elaborazioni", routeLabel: "Elaborazioni / Allineamento AdE" },
  { prefix: "/elaborazioni/autodoc", moduleKey: "elaborazioni", routeLabel: "Elaborazioni / AUTODOC" },
  { prefix: "/elaborazioni/gaia-mobile-sync", moduleKey: "elaborazioni", routeLabel: "Elaborazioni / GAIA Mobile Sync" },
  { prefix: "/elaborazioni/settings", moduleKey: "elaborazioni", routeLabel: "Elaborazioni / Credenziali" },
  { prefix: "/elaborazioni", moduleKey: "elaborazioni", routeLabel: "Elaborazioni" },
  { prefix: "/me/presenze", moduleKey: "me", routeLabel: "La mia attivita / Presenze" },
  { prefix: "/me/operativita", moduleKey: "me", routeLabel: "La mia attivita / Operativita" },
  { prefix: "/me/dotazioni", moduleKey: "me", routeLabel: "La mia attivita / Dotazioni" },
  { prefix: "/me/anomalie", moduleKey: "me", routeLabel: "La mia attivita / Anomalie" },
  { prefix: "/me", moduleKey: "me", routeLabel: "La mia attivita" },
];

function buildFallbackLabel(pathname: string): string {
  const cleaned = pathname.replace(/^\/+|\/+$/g, "");
  if (!cleaned) {
    return "Home";
  }
  return cleaned
    .split("/")
    .map((segment) => segment.replace(/[-_]/g, " "))
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" / ");
}

export function resolvePresenceRouteMeta(pathname: string | null | undefined): PresenceRouteMeta {
  const value = pathname && pathname.trim() ? pathname : "/";
  if (value === "/") {
    return { moduleKey: "home", routeLabel: "Home" };
  }

  const matchedRule = ROUTE_RULES.find((rule) => value.startsWith(rule.prefix));
  if (matchedRule) {
    return {
      moduleKey: matchedRule.moduleKey,
      routeLabel: matchedRule.routeLabel,
    };
  }

  return {
    moduleKey: value.split("/").filter(Boolean)[0] ?? "other",
    routeLabel: buildFallbackLabel(value),
  };
}
