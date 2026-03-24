"use client";

import { useEffect, useMemo } from "react";
import { useState } from "react";
import { useParams } from "next/navigation";

import { ProtectedPage } from "@/components/app/protected-page";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { PermissionBadge } from "@/components/ui/permission-badge";
import { SourceTag } from "@/components/ui/source-tag";
import { SearchIcon } from "@/components/ui/icons";
import { useDomainData } from "@/hooks/use-domain-data";
import { getEffectivePermissions } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { getPermissionLevel } from "@/lib/presentation";
import type { EffectivePermission } from "@/types/api";

export default function ShareDetailPage() {
  const params = useParams<{ id: string }>();
  const [permissions, setPermissions] = useState<EffectivePermission[]>([]);
  const [error, setError] = useState<string | null>(null);
  const { users, shares } = useDomainData();

  useEffect(() => {
    async function loadDetails() {
      const token = getStoredAccessToken();
      if (!token) return;

      try {
        setPermissions(await getEffectivePermissions(token));
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento dettaglio share");
      }
    }

    void loadDetails();
  }, []);

  const shareId = Number(params.id);
  const share = shares.find((item) => item.id === shareId);
  const sharePermissions = useMemo(
    () => permissions.filter((permission) => permission.share_id === shareId),
    [permissions, shareId],
  );

  return (
    <ProtectedPage
      title="Dettaglio cartella condivisa"
      description="Vista analitica della share con accessi effettivi e origini delle regole applicate."
      breadcrumb="Cartelle condivise"
    >
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      {!share ? (
        <EmptyState
          icon={SearchIcon}
          title="Cartella non trovata"
          description="La share richiesta non è disponibile nel dominio sincronizzato."
        />
      ) : (
        <>
          <article className="panel-card">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-xl font-medium text-gray-900">{share.name}</h3>
                  {share.sector ? <Badge variant="info">{share.sector}</Badge> : null}
                </div>
                <p className="mt-2 text-sm text-gray-500">{share.path}</p>
                <p className="mt-1 text-sm text-gray-500">{share.description ?? "Descrizione non disponibile"}</p>
              </div>
              <div className="rounded-lg bg-gray-50 px-4 py-3 text-right">
                <p className="text-xs uppercase tracking-wide text-gray-400">Snapshot</p>
                <p className="mt-1 text-sm font-medium text-gray-900">{share.last_seen_snapshot_id ?? "—"}</p>
              </div>
            </div>
          </article>

          <article className="panel-card overflow-hidden p-0">
            <div className="border-b border-gray-100 px-5 py-4">
              <p className="section-title">Accessi effettivi</p>
              <p className="section-copy">Utenti, stato lettura/scrittura, deny e origine regola per questa share.</p>
            </div>
            {sharePermissions.length === 0 ? (
              <div className="p-5">
                <EmptyState
                  icon={SearchIcon}
                  title="Nessun accesso trovato"
                  description="Per questa cartella non risultano permessi persistiti nell’ultimo snapshot."
                />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Utente NAS</th>
                      <th>Permesso</th>
                      <th>Lettura</th>
                      <th>Scrittura</th>
                      <th>Deny</th>
                      <th>Origine</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sharePermissions.map((permission) => (
                      <tr key={permission.id}>
                        <td>{users.find((user) => user.id === permission.nas_user_id)?.username ?? permission.nas_user_id}</td>
                        <td>
                          <PermissionBadge level={getPermissionLevel(permission)} />
                        </td>
                        <td>{permission.can_read ? "✓" : "—"}</td>
                        <td>{permission.can_write ? "✓" : "—"}</td>
                        <td>{permission.is_denied ? "✗" : "—"}</td>
                        <td>
                          <SourceTag source={permission.source_summary} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </article>
        </>
      )}
    </ProtectedPage>
  );
}
