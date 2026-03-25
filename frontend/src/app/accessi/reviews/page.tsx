"use client";

import Link from "next/link";
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
const decisionOrder: Record<DecisionFilter, number> = {
  pending: 0,
  approved: 1,
  revoked: 2,
  all: 3,
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

    return [...reviews]
      .filter((review) => {
        if (decisionFilter !== "all" && review.decision !== decisionFilter) return false;

        if (!normalizedSearch) return true;

        return [
          userLabelMap.get(review.nas_user_id) ?? String(review.nas_user_id),
          shareLabelMap.get(review.share_id) ?? String(review.share_id),
          review.decision,
          review.note ?? "",
        ].some((value) => value.toLowerCase().includes(normalizedSearch));
      })
      .sort((left, right) => {
        const leftOrder = decisionOrder[left.decision as DecisionFilter] ?? decisionOrder.all;
        const rightOrder = decisionOrder[right.decision as DecisionFilter] ?? decisionOrder.all;

        if (leftOrder !== rightOrder) {
          return leftOrder - rightOrder;
        }

        return right.id - left.id;
      });
  }, [reviews, deferredSearchTerm, decisionFilter, userLabelMap, shareLabelMap]);

  const pendingCount = reviews.filter((review) => review.decision === "pending").length;
  const approvedCount = reviews.filter((review) => review.decision === "approved").length;
  const revokedCount = reviews.filter((review) => review.decision === "revoked").length;
  const reviewedCount = approvedCount + revokedCount;
  const reviewCoverage =
    reviews.length > 0 ? Math.round((reviewedCount / reviews.length) * 100) : 0;
  const hasActiveFilters = decisionFilter !== "all" || Boolean(searchTerm.trim());

  return (
    <ProtectedPage
      title="Review accessi"
      description="Coda di validazione per utenti e cartelle con stato decisionale e note operative."
      breadcrumb="Validazione"
    >
      {error || domainError ? <p className="text-sm text-red-600">{error ?? domainError}</p> : null}

      <div className="surface-grid">
        <MetricCard label="Review totali" value={reviews.length} sub="Richieste presenti in piattaforma" />
        <MetricCard label="In attesa" value={pendingCount} sub="Da validare" variant="warning" />
        <MetricCard label="Approvate" value={approvedCount} sub="Confermate dai reviewer" variant="success" />
        <MetricCard label="Revocate" value={revokedCount} sub="Da bonificare" variant="danger" />
      </div>

      <article className="panel-card">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="section-title">Filtri</p>
            <p className="section-copy">Ricerca su utente, share, decisione e nota.</p>
          </div>
          <div className="rounded-lg bg-gray-50 px-3 py-2 text-right">
            <p className="text-xs uppercase tracking-wide text-gray-400">Copertura review</p>
            <p className="text-sm font-semibold text-gray-900">{reviewCoverage}% completata</p>
            <p className="text-xs text-gray-500">
              {reviewedCount} su {reviews.length} già valutate
            </p>
          </div>
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
            <div className="mt-2 flex flex-wrap gap-2">
              {([
                ["all", "Tutte", reviews.length],
                ["pending", "In attesa", pendingCount],
                ["approved", "Approvate", approvedCount],
                ["revoked", "Revocate", revokedCount],
              ] as const).map(([value, label, count]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setDecisionFilter(value)}
                  className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition ${
                    decisionFilter === value
                      ? "border-[#1D4E35] bg-[#EAF3E8] text-[#1D4E35]"
                      : "border-gray-200 bg-white text-gray-600 hover:border-gray-300"
                  }`}
                >
                  <span>{label}</span>
                  <span className="rounded-full bg-white/80 px-1.5 py-0.5 text-[11px] leading-none text-gray-500">
                    {count}
                  </span>
                </button>
              ))}
            </div>
          </label>
          {hasActiveFilters ? (
            <div className="flex items-end">
              <button
                type="button"
                onClick={() => {
                  setSearchTerm("");
                  setDecisionFilter("all");
                }}
                className="rounded-md border border-gray-200 px-3 py-2 text-sm font-medium text-gray-600 transition hover:border-gray-300 hover:bg-gray-50"
              >
                Azzera filtri
              </button>
            </div>
          ) : null}
        </TableFilters>
        <p className="mt-3 text-xs text-gray-500">
          Mostrate {filteredReviews.length} review su {reviews.length}. Ordinamento: in attesa prima, poi più recenti.
        </p>
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
                  <div className="mb-3 flex flex-wrap items-center gap-2">
                    <Link
                      href={`/users/${review.nas_user_id}`}
                      className="rounded-md bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 transition hover:bg-gray-200"
                    >
                      Apri utente
                    </Link>
                    <Link
                      href={`/shares/${review.share_id}`}
                      className="rounded-md bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 transition hover:bg-gray-200"
                    >
                      Apri cartella
                    </Link>
                  </div>
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
