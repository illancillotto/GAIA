"use client";

import { useCallback, useState } from "react";

import { catastoGisSelect } from "@/lib/api/catasto";
import type { GisFilters, GisSelectResult } from "@/types/gis";

interface UseGisSelectionReturn {
  result: GisSelectResult | null;
  isLoading: boolean;
  error: string | null;
  runSelection: (geometry: GeoJSON.Geometry, filters?: GisFilters) => Promise<void>;
  clearSelection: () => void;
}

export function useGisSelection(token: string | null): UseGisSelectionReturn {
  const [result, setResult] = useState<GisSelectResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSelection = useCallback(
    async (geometry: GeoJSON.Geometry, filters?: GisFilters) => {
      if (!token) {
        setError("Sessione non disponibile. Accedi di nuovo.");
        return;
      }

      setIsLoading(true);
      setError(null);
      try {
        setResult(await catastoGisSelect(token, geometry, filters));
      } catch (selectionError) {
        setError(selectionError instanceof Error ? selectionError.message : "Errore selezione spaziale");
      } finally {
        setIsLoading(false);
      }
    },
    [token],
  );

  const clearSelection = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { result, isLoading, error, runSelection, clearSelection };
}
