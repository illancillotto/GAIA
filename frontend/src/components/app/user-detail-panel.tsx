"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Avatar } from "@/components/ui/avatar";
import { AlertBanner } from "@/components/ui/alert-banner";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { SearchIcon } from "@/components/ui/icons";
import { PermissionBadge } from "@/components/ui/permission-badge";
import { SourceTag } from "@/components/ui/source-tag";
import { useDomainData } from "@/hooks/use-domain-data";
import { getEffectivePermissions, getReviews } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import {
  buildPermissionTree,
  filterPermissionTreeForDisplay,
  getAnomalousPermissions,
  isEscalation,
  isMultiSourceAnomaly,
  parseSourceTokens,
} from "@/lib/permissions";
import { getPermissionLevel } from "@/lib/presentation";
import { cn } from "@/lib/cn";
import type { EffectivePermission, Review } from "@/types/api";

type TabKey = "permissions" | "reviews" | "activity";

type UserDetailPanelProps = {
  userId: number;
  compact?: boolean;
  onClose?: () => void;
};

export function UserDetailPanel({ userId, compact = false, onClose }: UserDetailPanelProps) {
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

  const user = users.find((item) => item.id === userId);

  const userPermissions = useMemo(
    () => permissions.filter((permission) => permission.nas_user_id === userId),
    [permissions, userId],
  );
  const userReviews = useMemo(
    () => reviews.filter((review) => review.nas_user_id === userId),
    [reviews, userId],
  );
  const anomalousPermissions = useMemo(
    () => getAnomalousPermissions(userPermissions),
    [userPermissions],
  );
  const hasAnomalies = anomalousPermissions.length > 0;
  const permissionTree = useMemo(
    () => filterPermissionTreeForDisplay(buildPermissionTree(userPermissions, shares)),
    [shares, userPermissions],
  );

  const groupBadgeMeta = useMemo(() => {
    const stats = new Map<
      string,
      {
        firstSeenAt: number;
        lowestLevelRank: number;
        isSecondary: boolean;
      }
    >();

    userPermissions.forEach((permission, permissionIndex) => {
      const tokens = parseSourceTokens(permission.source_summary);
      const groupTokens = tokens.filter((token) => token.type === "group");

      groupTokens.forEach((token) => {
        const existing = stats.get(token.name);
        const levelRank =
          token.level.toLowerCase().includes("write")
            ? 2
            : token.level.toLowerCase().includes("read")
              ? 1
              : 0;

        if (!existing) {
          stats.set(token.name, {
            firstSeenAt: permissionIndex,
            lowestLevelRank: levelRank,
            isSecondary: false,
          });
          return;
        }

        existing.lowestLevelRank = Math.min(existing.lowestLevelRank, levelRank);
      });

      if (!permission.can_write) {
        return;
      }

      const groupRanks = groupTokens.map((token) => ({
        name: token.name,
        rank:
          token.level.toLowerCase().includes("write")
            ? 2
            : token.level.toLowerCase().includes("read")
              ? 1
              : 0,
      }));

      if (groupRanks.length < 2) {
        return;
      }

      const minRank = Math.min(...groupRanks.map((token) => token.rank));
      const maxRank = Math.max(...groupRanks.map((token) => token.rank));

      if (maxRank <= minRank) {
        return;
      }

      groupRanks
        .filter((token) => token.rank === maxRank)
        .forEach((token) => {
          const current = stats.get(token.name);
          if (current) {
            current.isSecondary = true;
          }
        });
    });

    const orderedGroups = Array.from(stats.entries()).sort((left, right) => {
      const [, leftMeta] = left;
      const [, rightMeta] = right;

      if (leftMeta.lowestLevelRank !== rightMeta.lowestLevelRank) {
        return leftMeta.lowestLevelRank - rightMeta.lowestLevelRank;
      }

      return leftMeta.firstSeenAt - rightMeta.firstSeenAt;
    });

    const primaryGroupName = orderedGroups[0]?.[0] ?? null;
    const secondaryGroupNames = new Set(
      orderedGroups
        .filter(([groupName, meta]) => meta.isSecondary && groupName !== primaryGroupName)
        .map(([groupName]) => groupName),
    );

    return {
      orderedGroups,
      secondaryGroupNames,
    };
  }, [userPermissions]);

  const guessedGroups = useMemo(() => {
    return groupBadgeMeta.orderedGroups
      .map(([groupName]) => groups.find((group) => group.name === groupName))
      .filter((group): group is (typeof groups)[number] => Boolean(group));
  }, [groupBadgeMeta.orderedGroups, groups]);

  return (
    <div className="page-stack">
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      {!user ? (
        <article className="panel-card">
          <EmptyState
            icon={SearchIcon}
            title="Utente non trovato"
            description="Il record richiesto non è disponibile nel dominio sincronizzato."
          />
        </article>
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
                      <Badge
                        key={group.id}
                        variant={groupBadgeMeta.secondaryGroupNames.has(group.name) ? "warning" : "info"}
                      >
                        {group.name}
                      </Badge>
                    ))
                  ) : (
                    <Badge variant="neutral">Gruppi non dedotti</Badge>
                  )}
                </div>
              </div>
              {onClose ? (
                <button className="btn-secondary self-start" onClick={onClose} type="button">
                  Chiudi
                </button>
              ) : null}
            </div>
          </article>

          <article className="panel-card">
            {hasAnomalies ? (
              <AlertBanner title="Permessi da origini multiple rilevati" variant="warning">
                <p>
                  {anomalousPermissions.length === 1
                    ? "1 cartella ha un livello di accesso derivante da un gruppo secondario."
                    : `${anomalousPermissions.length} cartelle hanno livelli di accesso derivanti da gruppi secondari.`}{" "}
                  Verificare le origini nella colonna Origine e valutare una review.
                </p>
              </AlertBanner>
            ) : null}

            <div className={cn("flex flex-wrap gap-2", hasAnomalies ? "mt-4 mb-4" : "mb-4")}>
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
                <div className={cn("overflow-hidden rounded-xl border border-gray-100", compact ? "max-h-[26rem] overflow-y-auto" : "")}>
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
                      {permissionTree.map((node) => {
                        const { permission, share } = node;
                        const isAnomalous = isMultiSourceAnomaly(permission.source_summary);
                        const hasEscalation = isEscalation(node);

                        return (
                          <tr
                            key={permission.id}
                            className={isAnomalous ? "bg-amber-50" : undefined}
                          >
                            <td>
                              <div
                                className="flex items-center gap-1"
                                style={{ paddingLeft: `${node.depth * 16}px` }}
                              >
                                {node.depth > 0 ? (
                                  <span className="select-none text-gray-300">↳</span>
                                ) : null}
                                <span
                                  className={node.depth > 0 ? "text-sm text-gray-700" : "text-sm font-medium text-gray-900"}
                                >
                                  {share.name}
                                </span>
                              </div>
                            </td>
                            <td>
                              <div className="inline-flex items-center">
                                <PermissionBadge level={getPermissionLevel(permission)} />
                                {hasEscalation ? (
                                  <span
                                    title="Livello di accesso superiore alla cartella padre. Verificare l'origine."
                                    className="ml-1 inline-flex cursor-help items-center rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-700"
                                  >
                                    ↑
                                  </span>
                                ) : null}
                                {isAnomalous ? (
                                  <span className="ml-1 inline-flex items-center rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-800">
                                    !
                                  </span>
                                ) : null}
                              </div>
                            </td>
                            <td>{permission.can_read ? "✓" : "—"}</td>
                            <td>{permission.can_write ? "✓" : "—"}</td>
                            <td>{permission.is_denied ? "✗" : "—"}</td>
                            <td>
                              <SourceTag source={permission.source_summary} expanded={isAnomalous} />
                            </td>
                          </tr>
                        );
                      })}
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
                <div className={cn("space-y-3", compact ? "max-h-[26rem] overflow-y-auto pr-1" : "")}>
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
                {!compact ? (
                  <Link className="font-medium text-[#1D4E35]" href="/accessi/users">
                    Torna all’elenco utenti
                  </Link>
                ) : null}
              </div>
            ) : null}
          </article>
        </>
      )}
    </div>
  );
}
