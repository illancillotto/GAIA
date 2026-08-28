"use client";

import { useEffect, useState } from "react";

import {
  createGisSchedaTerritoriale,
  downloadGisSchedaTerritoriale,
  getGisSchedaTerritoriale,
  type GisSchedaTerritoriale,
} from "@/lib/api/territorio";

export type SchedaTerritorialeState = {
  parcelId: string | null;
  sheet: GisSchedaTerritoriale | null;
  error: string | null;
  downloadUrl: string | null;
  generate: () => void;
};

function parcelIdFromGaia(gaia: Array<{ source_id: string; data: Array<Record<string, unknown>> }>): string | null {
  const id = gaia.find((source) => source.source_id === "particella")?.data[0]?.id;
  return typeof id === "string" ? id : null;
}

export function useSchedaTerritoriale(
  token: string | null,
  gaia: Array<{ source_id: string; data: Array<Record<string, unknown>> }>,
): SchedaTerritorialeState {
  const parcelId = parcelIdFromGaia(gaia);
  const [sheet, setSheet] = useState<GisSchedaTerritoriale | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);

  useEffect(() => {
    setSheet(null);
    setError(null);
    setDownloadUrl(null);
  }, [parcelId]);

  useEffect(() => {
    if (!token || !sheet || !["queued", "processing"].includes(sheet.status)) return;
    const timer = window.setTimeout(() => {
      void getGisSchedaTerritoriale(token, sheet.id)
        .then(setSheet)
        .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : String(reason)));
    }, 1000);
    return () => window.clearTimeout(timer);
  }, [sheet, token]);

  useEffect(() => {
    if (!token || sheet?.status !== "completed") return;
    void downloadGisSchedaTerritoriale(token, sheet.id)
      .then((blob) => setDownloadUrl(URL.createObjectURL(blob)))
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : String(reason)));
  }, [sheet, token]);

  useEffect(() => () => { if (downloadUrl) URL.revokeObjectURL(downloadUrl); }, [downloadUrl]);

  return {
    parcelId,
    sheet,
    error,
    downloadUrl,
    generate: () => {
      if (!token || !parcelId) return;
      setError(null);
      setDownloadUrl(null);
      void createGisSchedaTerritoriale(token, parcelId)
        .then(setSheet)
        .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : String(reason)));
    },
  };
}
