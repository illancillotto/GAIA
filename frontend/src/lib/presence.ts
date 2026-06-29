export type PresenceRouteMeta = {
  moduleKey: string;
  routeLabel: string;
};

const ROUTE_RULES: Array<{ prefix: string; moduleKey: string; routeLabel: string }> = [
  { prefix: "/gaia/users/attivita", moduleKey: "gaia", routeLabel: "Utenti GAIA / Attivita utenti" },
  { prefix: "/gaia/users", moduleKey: "gaia", routeLabel: "Utenti GAIA" },
  { prefix: "/nas-control", moduleKey: "accessi", routeLabel: "NAS Control" },
  { prefix: "/network", moduleKey: "rete", routeLabel: "Rete" },
  { prefix: "/inventory", moduleKey: "inventario", routeLabel: "Inventario" },
  { prefix: "/catasto", moduleKey: "catasto", routeLabel: "Catasto" },
  { prefix: "/utenze", moduleKey: "utenze", routeLabel: "Utenze" },
  { prefix: "/anagrafica", moduleKey: "utenze", routeLabel: "Utenze / ANPR" },
  { prefix: "/operazioni", moduleKey: "operazioni", routeLabel: "Operazioni" },
  { prefix: "/riordino", moduleKey: "riordino", routeLabel: "Riordino" },
  { prefix: "/ruolo", moduleKey: "ruolo", routeLabel: "Ruolo" },
  { prefix: "/presenze", moduleKey: "presenze", routeLabel: "Giornaliere" },
  { prefix: "/organigramma", moduleKey: "organigramma", routeLabel: "Organigramma" },
  { prefix: "/wiki", moduleKey: "wiki", routeLabel: "Wiki" },
  { prefix: "/elaborazioni", moduleKey: "elaborazioni", routeLabel: "Elaborazioni" },
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
