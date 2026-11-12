"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { getStoredAccessToken } from "@/lib/auth";
import { parcelHistoryRequest } from "@/lib/parcel-history-api";
import type { ParcelHistory, ParcelHistoryPage } from "@/types/parcel-history";

export function useParcelHistory() {
  const params = useSearchParams();
  const [result, setResult] = useState<{ path: string; value: ParcelHistoryPage | ParcelHistory } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const selected = params.get("storia");
  const query = new URLSearchParams();
  for (const key of ["comune", "foglio", "particella", "search", "page"]) {
    const value = params.get(key);
    if (value) query.set(key, value);
  }
  const path = selected ? `/${encodeURIComponent(selected)}` : `?${query}`;
  useEffect(() => {
    let active = true;
    setLoading(true); setError(""); setResult(null);
    const token = getStoredAccessToken();
    if (!token) { setError("Accedi a GAIA per consultare lo storico."); setLoading(false); return; }
    parcelHistoryRequest<ParcelHistoryPage | ParcelHistory>(token, path)
      .then(value => { if (active) setResult({ path, value }); })
      .catch(reason => { if (active) setError(reason instanceof Error ? reason.message : "Caricamento non riuscito"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [path, revision]);
  return { data: result?.path === path ? result.value : null, loading, error, selected, retry: () => setRevision(value => value + 1) };
}
