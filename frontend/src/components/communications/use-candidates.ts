"use client";

import { useCallback, useEffect, useState } from "react";
import { communications } from "@/lib/communications-api";
import type { Account, Candidate, Channel, Template } from "@/types/communications";

export function useCandidates(token: string, channel: Channel, canEdit: boolean) {
  const [filters, setFilters] = useState({ q: "", has_contact: "", state: "", date_from: "", date_to: "", account_id: "", batch_id: "", payment_state: "", notification_state: "", has_pec: "", has_email: "", [`has_${channel}`]: "true" });
  const [page, setPage] = useState(1);
  const [revision, setRevision] = useState(0);
  const reload = useCallback(() => setRevision(value => value + 1), []);
  const search = useDebouncedSearch(filters.q);
  const query = new URLSearchParams({ channel, year: "2021", page: String(page), page_size: "25" });
  for (const [key, value] of Object.entries({ ...filters, q: search })) if (value) query.set(key, value);
  const list = useCandidateResults(token, `/ruolo/candidates?${query}`, revision);
  const catalogs = useCandidateCatalogs(token, canEdit, revision);
  return { filters, setFilters, page, setPage, reload,
    data: { ...list.data, ...catalogs.data },
    loading: list.loading || filters.q !== search,
    loadError: list.error || catalogs.error };
}

function useDebouncedSearch(value: string) {
  const [search, setSearch] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setSearch(value), 300);
    return () => clearTimeout(timer);
  }, [value]);
  return search;
}

function useCandidateResults(token: string, path: string, revision: number) {
  const [data, setData] = useState<{ items: Candidate[]; total: number }>({ items: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError("");
    communications<typeof data>(token, path, undefined, undefined, controller.signal).then(value => {
      if (!controller.signal.aborted) { setData(value); setLoading(false); }
    }).catch((failure: Error) => {
      if (!controller.signal.aborted) { setError(failure.message); setLoading(false); }
    });
    return () => controller.abort();
  }, [token, path, revision]);
  return { data, loading, error };
}

function useCandidateCatalogs(token: string, canEdit: boolean, revision: number) {
  const [data, setData] = useState<{ accounts: Account[]; templates: Template[] }>({ accounts: [], templates: [] });
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    setError("");
    Promise.all([
      canEdit ? communications<Account[]>(token, "/accounts", undefined, undefined, controller.signal) : Promise.resolve([]),
      communications<Template[]>(token, "/templates", undefined, undefined, controller.signal),
    ]).then(([accounts, templates]) => {
      if (!controller.signal.aborted) setData({ accounts, templates });
    }).catch((failure: Error) => {
      if (!controller.signal.aborted) setError(failure.message);
    });
    return () => controller.abort();
  }, [token, canEdit, revision]);
  return { data, error };
}
