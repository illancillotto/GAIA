"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { usePolling } from "@/hooks/use-polling";
import { getStoredAccessToken } from "@/lib/auth";
import { syncError, type SyncServiceState } from "@/lib/sync-dashboard-model";
import { SYNC_SERVICES } from "@/lib/sync-dashboard-services";

export function useSyncDashboard() {
  const [states, setStates] = useState<Record<string, SyncServiceState>>({});
  const [refreshing, setRefreshing] = useState(false);
  const busy = useRef(false);
  const mounted = useRef(false);
  const refresh = useCallback(async () => {
    const token = getStoredAccessToken();
    if (!token || busy.current) return;
    busy.current = true;
    setRefreshing(true);
    await Promise.allSettled(SYNC_SERVICES.map(async (service) => {
      let state: SyncServiceState;
      try {
        const snapshots = await service.load(token);
        state = { snapshots, updatedAt: new Date().toISOString(), error: null };
      } catch (error) {
        state = { snapshots: [], updatedAt: null, error: syncError(error) };
      }
      if (mounted.current) setStates((current) => ({ ...current, [service.id]: state }));
    }));
    busy.current = false;
    if (mounted.current) setRefreshing(false);
  }, []);
  useEffect(() => {
    mounted.current = true;
    void refresh();
    return () => { mounted.current = false; };
  }, [refresh]);
  usePolling(refresh, { enabled: true, intervalMs: 30000 });
  return { states, refreshing, refresh };
}
