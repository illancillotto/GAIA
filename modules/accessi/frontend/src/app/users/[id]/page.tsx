"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { ProtectedPage } from "@/components/app/protected-page";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { PermissionBadge } from "@/components/ui/permission-badge";
import { SourceTag } from "@/components/ui/source-tag";
import { SearchIcon } from "@/components/ui/icons";
import { useDomainData } from "@/hooks/use-domain-data";
import { getPermissionLevel } from "@/lib/presentation";
import { useEffect } from "react";
import { getEffectivePermissions, getReviews } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { EffectivePermission, Review } from "@/types/api";

type TabKey = "permissions" | "reviews" | "activity";

export default function UserDetailPage() {
  const params = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState<TabKey>("permissions");
  const [permissions, setPermissions] = useState<EffectivePermission[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [error, setError] = useState<string | null>(null);
  const { users, groups, shares } = useDomainData();

  useEffect(() => {
    async function loadDetails() {
      const token = getStoredAccessToken();
      if (!token) return;

      try {
        const [permissionItems, reviewItems] = await Promise.all([
          getEffectivePermissions(token),
          getReviews(token),
        ]);
        setPermissions(permissionItems);
        setReviews(reviewItems);
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento dettaglio utente");
      }
    }

    void loadDetails();
  }, []);

  const userId = Number(params.id);
  const user = users.find((item) => item.id === userId);

  const userPermissions = useMemo(
    () => permissions.filter((permission) => permission.nas_user_id === userId),
    [permissions, userId],
  );
  const userReviews = useMemo(
    () => reviews.filter((review) => review.nas_user_id === userId),
    [reviews, userId],
  );

  const guessedGroups = useMemo(() => {
    const relatedSources = userPermissions.flatMap((permission) => permission.source_summary.split(","));
    return groups.filter((group) => relatedSources.some((source) => source.includes(`group:${group.name}:`)));
  }, [groups, userPermissions]);

  return (
    <ProtectedPage
      title="Dettaglio utente"
      description="Vista analitica di permessi effettivi, review e tracce operative del singolo utente NAS."
      breadcrumb="Utenti"
    >
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      {!user ? (
        <EmptyState
          icon={SearchIcon}
          title="Utente non trovato"
          description="Il record richiesto non è disponibile nel dominio sincronizzato."
        />
      ) : (
        <>
          <article className="panel-card">
            <div className="flex flex-col gap-4 md:flex-row md:items-center">
              <Avatar label={user.full_name ?? user.username} size="lg" />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-xl font-medium text-gray-900">{user.full_name ?? user.username}</h3>
                  <Badge variant={user.is_active ? "success" : "neutral"}>
                    {user.is_active ? "Attivo" : "Inattivo"}
                  </Badge>
                </div>
                <p className="mt-1 text-sm text-gray-500">
                  @{user.username} · UID {user.source_uid ?? "—"} · Snapshot {user.last_seen_snapshot_id ?? "—"}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {guessedGroups.length > 0 ? (
                    guessedGroups.map((group) => (
                      <Badge key={group.id} variant="info">
                        {group.name}
                      </Badge>
                    ))
                  ) : (
                    <Badge variant="neutral">Gruppi non dedotti</Badge>
                  )}
                </div>
              </div>
            </div>
          </article>

          <article className="panel-card">
            <div className="mb-4 flex flex-wrap gap-2">
              {([
                ["permissions", "Permessi effettivi"],
                ["reviews", "Review"],
                ["activity", "Attività"],
              ] as const).map(([key, label]) => (
                <button
                  key={key}
                  className={key === activeTab ? "btn-primary" : "btn-secondary"}
                  onClick={() => setActiveTab(key)}
                  type="button"
                >
                  {label}
                </button>
              ))}
            </div>

            {activeTab === "permissions" ? (
              userPermissions.length === 0 ? (
                <EmptyState
                  icon={SearchIcon}
                  title="Nessun permesso effettivo"
                  description="Per questo utente non risultano record nel calcolo dell’ultimo snapshot."
                />
              ) : (
                <div className="overflow-hidden rounded-xl border border-gray-100">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Cartella</th>
                        <th>Permesso</th>
                        <th>Lettura</th>
                        <th>Scrittura</th>
                        <th>Deny</th>
                        <th>Origine</th>
                      </tr>
                    </thead>
                    <tbody>
                      {userPermissions.map((permission) => (
                        <tr key={permission.id}>
                          <td>{shares.find((share) => share.id === permission.share_id)?.name ?? permission.share_id}</td>
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
              )
            ) : null}

            {activeTab === "reviews" ? (
              userReviews.length === 0 ? (
                <EmptyState
                  icon={SearchIcon}
                  title="Nessuna review"
                  description="Non risultano review associate a questo utente."
                />
              ) : (
                <div className="space-y-3">
                  {userReviews.map((review) => (
                    <div key={review.id} className="rounded-lg border border-gray-100 bg-gray-50 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-medium text-gray-900">
                            {shares.find((share) => share.id === review.share_id)?.name ?? review.share_id}
                          </p>
                          <p className="text-xs text-gray-400">
                            Snapshot #{review.snapshot_id ?? "—"} · Reviewer #{review.reviewer_user_id}
                          </p>
                        </div>
                        <Badge variant={review.decision === "approved" ? "success" : review.decision === "revoked" ? "danger" : "warning"}>
                          {review.decision}
                        </Badge>
                      </div>
                      <p className="mt-3 text-sm text-gray-600">{review.note ?? "Nessuna nota disponibile."}</p>
                    </div>
                  ))}
                </div>
              )
            ) : null}

            {activeTab === "activity" ? (
              <div className="space-y-3 text-sm text-gray-600">
                <p>Record ultimo snapshot: {user.last_seen_snapshot_id ?? "—"}</p>
                <p>Permessi persistiti: {userPermissions.length}</p>
                <p>Review associate: {userReviews.length}</p>
                <Link className="font-medium text-[#1D4E35]" href="/users">
                  Torna all’elenco utenti
                </Link>
              </div>
            ) : null}
          </article>
        </>
      )}
    </ProtectedPage>
  );
}
