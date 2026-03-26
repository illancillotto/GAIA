"use client";

import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { PermissionBadge } from "@/components/ui/permission-badge";
import { SourceTag } from "@/components/ui/source-tag";
import { SearchIcon } from "@/components/ui/icons";
import { useDomainData } from "@/hooks/use-domain-data";
import { getEffectivePermissions } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { getPermissionLevel } from "@/lib/presentation";
import { cn } from "@/lib/cn";
import type { EffectivePermission } from "@/types/api";

type ShareDetailPanelProps = {
  shareId: number;
  compact?: boolean;
  onClose?: () => void;
};

export function ShareDetailPanel({ shareId, compact = false, onClose }: ShareDetailPanelProps) {
  const [permissions, setPermissions] = useState<EffectivePermission[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showNoAccess, setShowNoAccess] = useState(false);
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

  const share = shares.find((item) => item.id === shareId);
  const sharePermissions = useMemo(
    () => permissions.filter((permission) => permission.share_id === shareId),
    [permissions, shareId],
  );
  const visiblePermissions = useMemo(
    () =>
      showNoAccess
        ? sharePermissions
        : sharePermissions.filter(
            (permission) => permission.can_read || permission.can_write || permission.is_denied,
          ),
    [sharePermissions, showNoAccess],
  );

  return (
    <div className="page-stack">
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
              <div className="flex items-start gap-3">
                {onClose ? (
                  <button className="btn-secondary" onClick={onClose} type="button">
                    Chiudi
                  </button>
                ) : null}
              </div>
            </div>
          </article>

          <article className="panel-card overflow-hidden p-0">
            <div className="flex flex-wrap items-start justify-between gap-4 border-b border-gray-100 px-5 py-4">
              <div>
                <p className="section-title">Permessi effettivi</p>
                <p className="section-copy">Utenti, stato lettura/scrittura, deny e origine regola per questa share.</p>
              </div>
              <label className="flex items-center gap-3 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm font-medium text-gray-700">
                <input
                  checked={showNoAccess}
                  className="h-4 w-4 rounded border-gray-300 text-[#1D4E35] focus:ring-[#1D4E35]"
                  onChange={(event) => setShowNoAccess(event.target.checked)}
                  type="checkbox"
                />
                Mostra utenti senza accesso
              </label>
            </div>
            {visiblePermissions.length === 0 ? (
              <div className="p-5">
                <EmptyState
                  icon={SearchIcon}
                  title="Nessun accesso visibile"
                  description={
                    sharePermissions.length === 0
                      ? "Per questa cartella non risultano permessi persistiti nell’ultimo snapshot."
                      : "I record disponibili risultano tutti senza accesso. Attivare il toggle per visualizzarli."
                  }
                />
              </div>
            ) : (
              <div className={cn("overflow-x-auto", compact ? "max-h-[26rem] overflow-y-auto" : "")}>
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
                    {visiblePermissions.map((permission) => (
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
    </div>
  );
}
