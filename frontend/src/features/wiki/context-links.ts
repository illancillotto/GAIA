export function buildWikiContextHref(entityKey?: string | null, moduleKey?: string | null): string | null {
  if (entityKey) {
    if (entityKey.startsWith("catasto.particelle.")) {
      const id = entityKey.replace("catasto.particelle.", "");
      return `/catasto/particelle/${id}`;
    }
    if (entityKey.startsWith("accessi.shares.")) {
      const shareName = entityKey.replace("accessi.shares.", "");
      return shareName === "lookup" ? "/nas-control/shares" : `/nas-control/shares?q=${encodeURIComponent(shareName)}`;
    }
    if (entityKey.startsWith("accessi.share.")) {
      const shareName = entityKey.replace("accessi.share.", "");
      return `/nas-control/shares?q=${encodeURIComponent(shareName)}`;
    }
    if (entityKey.startsWith("accessi.nas-users.")) {
      const username = entityKey.replace("accessi.nas-users.", "");
      return username === "lookup" ? "/nas-control/users" : `/nas-control/users?q=${encodeURIComponent(username)}`;
    }
    if (entityKey.startsWith("accessi.permissions.")) {
      return "/gaia/users";
    }
    if (entityKey.startsWith("utenze.subjects.")) {
      const id = entityKey.replace("utenze.subjects.", "");
      return `/utenze/${id}`;
    }
    if (entityKey.startsWith("ruolo.subjects.")) {
      const query = entityKey.replace("ruolo.subjects.", "");
      return query === "lookup" ? "/ruolo/avvisi" : `/ruolo/avvisi?q=${encodeURIComponent(query)}`;
    }
    if (entityKey.startsWith("riordino.practices.")) {
      const id = entityKey.replace("riordino.practices.", "");
      return `/riordino/pratiche/${id}`;
    }
    if (entityKey.startsWith("operazioni.cases.")) {
      const id = entityKey.replace("operazioni.cases.", "");
      return `/operazioni/pratiche/${id}`;
    }
    if (entityKey.startsWith("operazioni.activities.")) {
      const id = entityKey.replace("operazioni.activities.", "");
      return `/operazioni/attivita/${id}`;
    }
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
