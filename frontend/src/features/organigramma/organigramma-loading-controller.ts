import { getCurrentUser, getOrgTree, listAllApplicationUsers, getOrgAssignments, getOrgOverrides, getOrgUnit, isAuthError } from "@/lib/api";
import { flattenTree } from "@/lib/organigramma";
import type { OrganigrammaLoadingContext } from "@/features/organigramma/organigramma-loading-context";

type LoadCoreContext = Pick<OrganigrammaLoadingContext, "token" | "structureKind" | "setError" | "setLoading" | "setCurrentUser" | "setTree" | "setUsers" | "setAllAssignments" | "setExpanded" | "setSelectedId" | "setOverrides" | "setCanManage">;

export async function loadCore({ token, structureKind, setError, setLoading, setCurrentUser, setTree, setUsers, setAllAssignments, setExpanded, setSelectedId, setOverrides, setCanManage }: LoadCoreContext) {
  if (!token) {
    setError("Sessione non disponibile.");
    setLoading(false);
    return;
  }
  setLoading(true);
  try {
    const [sessionUser, treeData, usersData, assignmentsData] = await Promise.all([
      getCurrentUser(token),
      getOrgTree(token, structureKind),
      listAllApplicationUsers(token),
      getOrgAssignments(token, { structureKind }),
    ]);
    setCurrentUser(sessionUser);
    setTree(treeData);
    setUsers(usersData);
    setAllAssignments(assignmentsData);
    const flat = flattenTree(treeData);
    if (flat.length) {
      setExpanded(new Set(flat.slice(0, 3).map((n) => n.id)));
      setSelectedId((prev) => prev ?? flat[0].id);
    }
    // overrides are manage-gated; tolerate 403 for read-only users
    try {
      setOverrides(await getOrgOverrides(token, structureKind));
    } catch (err) {
      if (!isAuthError(err)) setOverrides([]);
    }
    setCanManage(sessionUser.role === "super_admin");
    setError(null);
  } catch (err) {
    setError(err instanceof Error ? err.message : "Errore di caricamento");
  } finally {
    setLoading(false);
  }
}

type RefreshStructureContext = Pick<OrganigrammaLoadingContext, "token" | "structureKind" | "setTree" | "setAllAssignments" | "selectedId" | "setDetail" | "setNotice">;

export async function refreshStructure({ token, structureKind, setTree, setAllAssignments, selectedId, setDetail, setNotice }: RefreshStructureContext) {
  if (!token) return;
  try {
    const [treeData, assignmentsData] = await Promise.all([
      getOrgTree(token, structureKind),
      getOrgAssignments(token, { structureKind }),
    ]);
    setTree(treeData);
    setAllAssignments(assignmentsData);
    if (selectedId) {
      try {
        setDetail(await getOrgUnit(token, selectedId, structureKind));
      } catch {
        // the selected unit may no longer exist; the selection effect handles it
      }
    }
  } catch (err) {
    setNotice(err instanceof Error ? err.message : "Aggiornamento dati non riuscito");
  }
}
