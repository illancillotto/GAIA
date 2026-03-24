"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { TableFilters } from "@/components/table/table-filters";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { SearchIcon } from "@/components/ui/icons";
import { useDomainData } from "@/hooks/use-domain-data";
import { getReviews } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { Review } from "@/types/api";

type DecisionFilter = "all" | "approved" | "revoked" | "pending";

const decisionMeta = {
  approved: { label: "Approvata", variant: "success" as const },
  revoked: { label: "Revocata", variant: "danger" as const },
  pending: { label: "In attesa", variant: "warning" as const },
};

export default function ReviewsPage() {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [decisionFilter, setDecisionFilter] = useState<DecisionFilter>("all");
  const { users, shares, error: domainError } = useDomainData();

  const deferredSearchTerm = useDeferredValue(searchTerm);

  const userLabelMap = useMemo(
    () => new Map(users.map((user) => [user.id, user.username])),
    [users],
  );

  const shareLabelMap = useMemo(
    () => new Map(shares.map((share) => [share.id, share.name])),
    [shares],
  );

  useEffect(() => {
    async function loadReviews() {
      const token = getStoredAccessToken();
      if (!token) return;

      try {
        setReviews(await getReviews(token));
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento review");
      }
    }

    void loadReviews();
  }, []);

  const filteredReviews = useMemo(() => {
    const normalizedSearch = deferredSearchTerm.trim().toLowerCase();

    return reviews.filter((review) => {
      if (decisionFilter !== "all" && review.decision !== decisionFilter) return false;

      if (!normalizedSearch) return true;

      return [
        userLabelMap.get(review.nas_user_id) ?? String(review.nas_user_id),
        shareLabelMap.get(review.share_id) ?? String(review.share_id),
        review.decision,
        review.note ?? "",
      ].some((value) => value.toLowerCase().includes(normalizedSearch));
    });
  }, [reviews, deferredSearchTerm, decisionFilter, userLabelMap, shareLabelMap]);

  return (
    <ProtectedPage
      title="Review accessi"
      description="Coda di validazione per utenti e cartelle con stato decisionale e note operative."
      breadcrumb="Validazione"
    >
      {error || domainError ? <p className="text-sm text-red-600">{error ?? domainError}</p> : null}

      <div className="surface-grid">
        <MetricCard label="Review totali" value={reviews.length} sub="Richieste presenti in piattaforma" />
        <MetricCard label="In attesa" value={reviews.filter((review) => review.decision === "pending").length} sub="Da validare" variant="warning" />
        <MetricCard label="Approvate" value={reviews.filter((review) => review.decision === "approved").length} sub="Confermate dai reviewer" variant="success" />
        <MetricCard label="Revocate" value={reviews.filter((review) => review.decision === "revoked").length} sub="Da bonificare" variant="danger" />
      </div>

      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Filtri</p>
          <p className="section-copy">Ricerca su utente, share, decisione e nota.</p>
        </div>
        <TableFilters>
          <label className="text-sm font-medium text-gray-700">
            Cerca
            <input
              className="form-control mt-1"
              type="text"
              placeholder="Es. AlessandroPorcu, EmailSaver, approvata"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
          </label>
          <label className="text-sm font-medium text-gray-700">
            Stato review
            <select
              className="form-control mt-1"
              value={decisionFilter}
              onChange={(event) => setDecisionFilter(event.target.value as DecisionFilter)}
            >
              <option value="all">Tutte</option>
              <option value="pending">In attesa</option>
              <option value="approved">Approvate</option>
              <option value="revoked">Revocate</option>
            </select>
          </label>
        </TableFilters>
      </article>

      {filteredReviews.length === 0 ? (
        <EmptyState
          icon={SearchIcon}
          title="Nessuna review trovata"
          description="Nessuna review corrisponde ai filtri selezionati."
        />
      ) : (
        <div className="space-y-4">
          {filteredReviews.map((review) => {
            const meta = decisionMeta[review.decision as keyof typeof decisionMeta] ?? {
              label: review.decision,
              variant: "neutral" as const,
            };

            return (
              <article key={review.id} className="panel-card">
                <div className="flex items-start gap-3">
                  <Avatar label={userLabelMap.get(review.nas_user_id) ?? String(review.nas_user_id)} />
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 flex flex-wrap items-center gap-2">
                      <p className="text-sm font-medium text-gray-900">{userLabelMap.get(review.nas_user_id) ?? review.nas_user_id}</p>
                      <span className="text-gray-300">→</span>
                      <p className="text-sm text-gray-600">{shareLabelMap.get(review.share_id) ?? review.share_id}</p>
                    </div>
                    <p className="text-xs text-gray-400">Snapshot #{review.snapshot_id ?? "—"} · Reviewer #{review.reviewer_user_id}</p>
                  </div>
                  <Badge variant={meta.variant}>{meta.label}</Badge>
                </div>
                <div className="mt-4 border-t border-gray-50 pt-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-400">Note</p>
                  <p className="mt-2 text-sm text-gray-600">{review.note ?? "Nessuna nota registrata."}</p>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </ProtectedPage>
  );
}
