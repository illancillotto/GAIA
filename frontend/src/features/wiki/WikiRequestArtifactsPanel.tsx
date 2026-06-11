"use client";

import { useMemo } from "react";

import type { WikiRequestArtifact } from "@/types/api";

type Props = {
  artifacts: WikiRequestArtifact[];
  artifactsLoading: boolean;
  screenshotPreviewUrl: string | null;
  downloadingArtifactId: string | null;
  onDownloadArtifact: (artifact: WikiRequestArtifact) => void | Promise<void>;
};

function formatSnapshotValue(value: unknown): string {
  if (value == null) return "n/d";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map((item) => formatSnapshotValue(item)).join(", ");
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function humanizeSnapshotKey(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function WikiRequestArtifactsPanel({
  artifacts,
  artifactsLoading,
  screenshotPreviewUrl,
  downloadingArtifactId,
  onDownloadArtifact,
}: Props) {
  const uiSnapshotArtifact = useMemo(
    () => artifacts.find((item) => item.artifact_type === "ui_snapshot") ?? null,
    [artifacts],
  );
  const screenshotArtifact = useMemo(
    () => artifacts.find((item) => item.artifact_type === "screenshot") ?? null,
    [artifacts],
  );
  const screenshotMetaArtifact = useMemo(
    () => artifacts.find((item) => item.artifact_type === "screenshot_meta") ?? null,
    [artifacts],
  );
  const moduleSnapshot = useMemo(() => {
    const payload = uiSnapshotArtifact?.payload;
    if (!payload || typeof payload !== "object" || !("module_snapshot" in payload)) {
      return null;
    }
    const value = payload.module_snapshot;
    return value && typeof value === "object" ? (value as Record<string, unknown>) : null;
  }, [uiSnapshotArtifact]);
  const moduleSnapshotEntity = useMemo(() => {
    const entity = moduleSnapshot?.entity;
    return entity && typeof entity === "object" ? (entity as Record<string, unknown>) : null;
  }, [moduleSnapshot]);
  const moduleSnapshotFilters = useMemo(() => {
    const filters = moduleSnapshot?.filters;
    return filters && typeof filters === "object" ? (filters as Record<string, unknown>) : null;
  }, [moduleSnapshot]);
  const moduleSnapshotActiveTabs = useMemo(() => {
    const tabs = moduleSnapshot?.active_tabs;
    return Array.isArray(tabs) ? tabs : [];
  }, [moduleSnapshot]);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Snapshot del caso</p>
        <span className="rounded-full border border-gray-200 bg-gray-50 px-2 py-1 text-[11px] text-gray-600">
          {artifacts.length} artifact
        </span>
      </div>
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.05fr)_minmax(20rem,0.95fr)]">
        <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] p-3">
          {artifactsLoading ? (
            <p className="text-sm text-gray-500">Caricamento screenshot e snapshot...</p>
          ) : screenshotPreviewUrl ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-gray-900">Schermata catturata</p>
                  <p className="text-xs text-gray-500">Freeze frame della pagina nel momento in cui l’operatore ha aperto il caso.</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <a
                    href={screenshotPreviewUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded-full border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700"
                  >
                    Apri immagine
                  </a>
                  {screenshotArtifact ? (
                    <button
                      type="button"
                      onClick={() => void onDownloadArtifact(screenshotArtifact)}
                      disabled={downloadingArtifactId === screenshotArtifact.id}
                      className="rounded-full border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 disabled:opacity-50"
                    >
                      {downloadingArtifactId === screenshotArtifact.id ? "Download..." : "Scarica screenshot"}
                    </button>
                  ) : null}
                </div>
              </div>
              <a href={screenshotPreviewUrl} target="_blank" rel="noreferrer">
                <img
                  src={screenshotPreviewUrl}
                  alt="Screenshot del caso al momento della richiesta"
                  className="max-h-[26rem] w-full rounded-xl border border-gray-200 object-contain"
                />
              </a>
            </div>
          ) : (
            <p className="text-sm text-gray-500">Nessuno screenshot salvato per questa richiesta.</p>
          )}
        </div>
        <div className="space-y-4">
          {moduleSnapshot ? (
            <div className="space-y-4">
              <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-950">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Contesto modulo</p>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-700/80">Modulo</p>
                    <p className="mt-1 text-sm">{formatSnapshotValue(moduleSnapshot.module)}</p>
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-700/80">Route</p>
                    <p className="mt-1 text-sm">{formatSnapshotValue(moduleSnapshot.route_type)}</p>
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-700/80">Entity ID</p>
                    <p className="mt-1 text-sm break-words">{formatSnapshotValue(moduleSnapshot.entity_id)}</p>
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-700/80">Route Key</p>
                    <p className="mt-1 text-sm break-words">{formatSnapshotValue(moduleSnapshot.route_key)}</p>
                  </div>
                </div>
                {moduleSnapshotActiveTabs.length > 0 ? (
                  <div className="mt-3">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-700/80">Tab attivi</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {moduleSnapshotActiveTabs.map((item) => (
                        <span key={String(item)} className="rounded-full border border-emerald-200 bg-white px-2 py-1 text-[11px] font-medium text-emerald-900">
                          {formatSnapshotValue(item)}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>

              {moduleSnapshotEntity ? (
                <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm text-gray-700">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Stato operativo catturato</p>
                  <div className="mt-3 grid gap-3 md:grid-cols-2">
                    {Object.entries(moduleSnapshotEntity).map(([key, value]) => (
                      <div key={key}>
                        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-400">{humanizeSnapshotKey(key)}</p>
                        <p className="mt-1 break-words text-sm text-gray-800">{formatSnapshotValue(value)}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {moduleSnapshotFilters && Object.keys(moduleSnapshotFilters).length > 0 ? (
                <div className="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-950">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">Filtri e parametri attivi</p>
                    {uiSnapshotArtifact ? (
                      <button
                        type="button"
                        onClick={() => void onDownloadArtifact(uiSnapshotArtifact)}
                        disabled={downloadingArtifactId === uiSnapshotArtifact.id}
                        className="rounded-full border border-sky-200 bg-white px-3 py-1.5 text-xs font-medium text-sky-900 disabled:opacity-50"
                      >
                        {downloadingArtifactId === uiSnapshotArtifact.id ? "Download..." : "Scarica snapshot JSON"}
                      </button>
                    ) : null}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {Object.entries(moduleSnapshotFilters).map(([key, value]) => (
                      <span key={key} className="rounded-full border border-sky-200 bg-white px-2.5 py-1 text-[11px] font-medium text-sky-900">
                        {humanizeSnapshotKey(key)}: {formatSnapshotValue(value)}
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}

          <details className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm text-gray-700">
            <summary className="cursor-pointer list-none text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">
              Dettagli tecnici snapshot
            </summary>
            <div className="mt-3 space-y-4">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-400">Metadata screenshot</p>
                <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs text-gray-600">
                  {JSON.stringify(screenshotMetaArtifact?.payload ?? {}, null, 2)}
                </pre>
              </div>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-400">Snapshot UI completo</p>
                <pre className="mt-2 max-h-[20rem] overflow-auto whitespace-pre-wrap text-xs text-gray-600">
                  {JSON.stringify(uiSnapshotArtifact?.payload ?? {}, null, 2)}
                </pre>
              </div>
            </div>
          </details>
        </div>
      </div>
    </div>
  );
}
