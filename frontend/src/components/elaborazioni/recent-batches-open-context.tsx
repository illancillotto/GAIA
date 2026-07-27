"use client";

import { createContext, useContext } from "react";

type RecentBatchesOpenContextValue = {
  onOpenBatch: (batchId: string) => void;
};

const RecentBatchesOpenContext = createContext<RecentBatchesOpenContextValue | null>(null);

export const RecentBatchesOpenProvider = RecentBatchesOpenContext.Provider;

export function useRecentBatchesOpenHandler(): ((batchId: string) => void) | null {
  return useContext(RecentBatchesOpenContext)?.onOpenBatch ?? null;
}
