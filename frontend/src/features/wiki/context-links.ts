export function buildWikiContextHref(entityKey?: string | null, moduleKey?: string | null): string | null {
  const contextKey = entityKey ?? "";
  if (contextKey.startsWith("catasto.particelle.")) {
    const id = contextKey.replace("catasto.particelle.", "");
    return `/catasto/particelle/${id}`;
  }
  if (contextKey.startsWith("accessi.shares.")) {
    const shareName = contextKey.replace("accessi.shares.", "");
    return shareName === "lookup" ? "/nas-control/shares" : `/nas-control/shares?q=${encodeURIComponent(shareName)}`;
  }
  if (contextKey.startsWith("accessi.share.")) {
    const shareName = contextKey.replace("accessi.share.", "");
    return `/nas-control/shares?q=${encodeURIComponent(shareName)}`;
  }
  if (contextKey.startsWith("accessi.nas-users.")) {
    const username = contextKey.replace("accessi.nas-users.", "");
    return username === "lookup" ? "/nas-control/users" : `/nas-control/users?q=${encodeURIComponent(username)}`;
  }
  if (contextKey.startsWith("accessi.permissions.")) {
    return "/gaia/users";
  }
  if (contextKey.startsWith("utenze.subjects.")) {
    const id = contextKey.replace("utenze.subjects.", "");
    return `/utenze/${id}`;
  }
  if (contextKey.startsWith("ruolo.subjects.")) {
    const query = contextKey.replace("ruolo.subjects.", "");
    return query === "lookup" ? "/ruolo/avvisi" : `/ruolo/avvisi?q=${encodeURIComponent(query)}`;
  }
  if (contextKey.startsWith("riordino.practices.")) {
    const id = contextKey.replace("riordino.practices.", "");
    return `/riordino/pratiche/${id}`;
  }
  if (contextKey.startsWith("operazioni.cases.")) {
    const id = contextKey.replace("operazioni.cases.", "");
    return `/operazioni/pratiche/${id}`;
  }
  if (contextKey.startsWith("operazioni.activities.")) {
    const id = contextKey.replace("operazioni.activities.", "");
    return `/operazioni/attivita/${id}`;
  }

  if (moduleKey === "accessi") {
    return "/nas-control";
  }
  if (moduleKey === "catasto") {
    return "/catasto";
  }
  if (moduleKey === "operazioni") {
    return "/operazioni";
  }
  if (moduleKey === "riordino") {
    return "/riordino";
  }
  if (moduleKey === "ruolo") {
    return "/ruolo";
  }
  if (moduleKey === "utenze") {
    return "/utenze";
  }
  return null;
}
