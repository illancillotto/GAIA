import { useEffect, useState } from "react";

import { listPresenzeCollaborators } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { PresenzeDashboardCollaborator } from "@/types/api";

export function useDashboardCollaborators(
  initialCollaborators: PresenzeDashboardCollaborator[],
  reportError: (message: string) => void,
) {
  const [recentCollaborators, setRecentCollaborators] = useState<PresenzeDashboardCollaborator[]>([]);
  const [collaboratorSearch, setCollaboratorSearch] = useState("");
  const [isCollaboratorsLoading, setIsCollaboratorsLoading] = useState(false);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    const query = collaboratorSearch.trim();
    if (!query) {
      setRecentCollaborators(initialCollaborators);
      setIsCollaboratorsLoading(false);
      return;
    }
    let cancelled = false;
    setIsCollaboratorsLoading(true);
    const handle = window.setTimeout(() => {
      listPresenzeCollaborators(token, { q: query, page: 1, pageSize: 10 })
        .then((response) => {
          if (!cancelled) setRecentCollaborators(response.items);
        })
        .catch((loadError) => {
          if (!cancelled) reportError(loadError instanceof Error ? loadError.message : "Errore ricerca collaboratori giornaliere");
        })
        .finally(() => {
          if (!cancelled) setIsCollaboratorsLoading(false);
        });
    }, 250);
    return () => {
      cancelled = true;
      window.clearTimeout(handle);
    };
  }, [collaboratorSearch, initialCollaborators, reportError]);

  return { collaboratorSearch, isCollaboratorsLoading, recentCollaborators, setCollaboratorSearch };
}
