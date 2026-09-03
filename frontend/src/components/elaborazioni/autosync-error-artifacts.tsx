"use client";

/* eslint-disable @next/next/no-img-element -- authenticated artifact previews use short-lived Blob URLs. */

import { useEffect, useRef, useState } from "react";

import {
  downloadElaborazioneRequestArtifactsBlob,
  fetchElaborazioneRequestArtifactPreviewBlob,
} from "@/lib/api";
import { getAutoSyncErrorRequest } from "@/lib/autosync-error-artifacts-api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type {
  CatastoPerpetualSyncItem,
  ElaborazioneRichiesta,
} from "@/types/api";

function itemLabel(item: CatastoPerpetualSyncItem): string {
  if (item.search_mode === "soggetto") {
    return `${item.intestazione ?? item.subject_kind ?? "Soggetto"} · ${item.subject_identifier ?? "identificativo mancante"}`;
  }
  return `${item.comune ?? "Comune non risolto"} · Fg. ${item.foglio ?? "-"} · Part. ${item.particella ?? "-"}`;
}

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = window.document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function useErrorRequest(item: CatastoPerpetualSyncItem) {
  const [request, setRequest] = useState<ElaborazioneRichiesta | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token || !item.linked_request_id) {
      setError("Dettagli richiesta non disponibili.");
      setLoading(false);
      return;
    }
    let cancelled = false;
    void getAutoSyncErrorRequest(token, item.linked_request_id)
      .then((result) => {
        if (!cancelled) setRequest(result);
      })
      .catch((loadError: unknown) => {
        if (!cancelled)
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Errore caricamento dettagli richiesta",
          );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [item.linked_request_id]);

  return { request, error, loading, setError };
}

async function downloadArtifact(
  request: ElaborazioneRichiesta,
  setError: (value: string | null) => void,
  setLoading: (value: boolean) => void,
): Promise<void> {
  const token = getStoredAccessToken();
  if (!token || !request.artifact_dir) return;
  setLoading(true);
  try {
    triggerDownload(
      await downloadElaborazioneRequestArtifactsBlob(token, request.id),
      `request-${request.id}-artifacts.zip`,
    );
    setError(null);
  } catch (error) {
    setError(
      error instanceof Error
        ? error.message
        : "Errore download artifact richiesta",
    );
  } finally {
    setLoading(false);
  }
}

async function previewArtifact(
  request: ElaborazioneRichiesta,
  setError: (value: string | null) => void,
  setLoading: (value: boolean) => void,
  setUrl: React.Dispatch<React.SetStateAction<string | null>>,
): Promise<void> {
  const token = getStoredAccessToken();
  if (!token || !request.artifact_dir) return;
  setLoading(true);
  try {
    const url = URL.createObjectURL(
      await fetchElaborazioneRequestArtifactPreviewBlob(token, request.id),
    );
    setUrl((current) => {
      if (current) URL.revokeObjectURL(current);
      return url;
    });
    setError(null);
  } catch (error) {
    setError(
      error instanceof Error
        ? error.message
        : "Errore caricamento preview screenshot",
    );
  } finally {
    setLoading(false);
  }
}

function ArtifactActions({
  request,
  setError,
  item,
}: {
  request: ElaborazioneRichiesta;
  setError: (value: string | null) => void;
  item: CatastoPerpetualSyncItem;
}) {
  const [downloading, setDownloading] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const previewUrlRef = useRef<string | null>(null);
  useEffect(() => {
    previewUrlRef.current = previewUrl;
  }, [previewUrl]);
  useEffect(
    () => () => {
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    },
    [],
  );

  if (!request.artifact_dir)
    return (
      <p className="text-sm text-gray-500">
        Nessun artifact disponibile per questa richiesta.
      </p>
    );
  return (
    <>
      <div className="flex flex-wrap gap-3 border-t border-gray-100 pt-4">
        <button
          className="btn-secondary"
          disabled={downloading}
          onClick={() =>
            void downloadArtifact(request, setError, setDownloading)
          }
          type="button"
        >
          {downloading ? "Download artifact..." : "Scarica artifact"}
        </button>
        <button
          className="btn-secondary"
          disabled={previewLoading}
          onClick={() =>
            void previewArtifact(
              request,
              setError,
              setPreviewLoading,
              setPreviewUrl,
            )
          }
          type="button"
        >
          {previewLoading ? "Caricamento preview..." : "Preview screenshot"}
        </button>
      </div>
      {previewUrl ? (
        <img
          alt={`Preview screenshot ${itemLabel(item)}`}
          className="max-h-[62vh] w-full rounded-xl border border-[#d9dfd6] object-contain"
          src={previewUrl}
        />
      ) : null}
    </>
  );
}

function RequestFacts({ request }: { request: ElaborazioneRichiesta }) {
  return (
    <>
      <dl className="grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-xs font-medium text-gray-500">Stato richiesta</dt>
          <dd className="mt-1 font-semibold text-gray-900">{request.status}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-gray-500">Tentativi</dt>
          <dd className="mt-1 font-semibold text-gray-900">
            {request.attempts}
          </dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-gray-500">Operazione</dt>
          <dd className="mt-1 text-gray-900">
            {request.current_operation ?? "-"}
          </dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-gray-500">Eseguita</dt>
          <dd className="mt-1 text-gray-900">
            {formatDateTime(request.processed_at)}
          </dd>
        </div>
      </dl>
      {request.error_message ? (
        <div className="rounded-xl bg-red-50 p-3 text-sm text-red-700">
          {request.error_message}
        </div>
      ) : null}
    </>
  );
}

function AutoSyncErrorDetails({
  item,
  onClose,
}: {
  item: CatastoPerpetualSyncItem;
  onClose: () => void;
}) {
  const { request, error, loading, setError } = useErrorRequest(item);
  return (
    <div
      aria-modal="true"
      className="fixed inset-0 z-[80] flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-sm"
      role="dialog"
    >
      <div className="flex max-h-[96vh] w-full max-w-2xl flex-col overflow-hidden rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
        <div className="flex items-start justify-between gap-4 border-b border-gray-100 px-6 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">
              Dettagli richiesta AutoSync
            </p>
            <h2 className="mt-1 text-lg font-semibold text-gray-900">
              {itemLabel(item)}
            </h2>
          </div>
          <button className="btn-secondary" onClick={onClose} type="button">
            Chiudi
          </button>
        </div>
        <div className="overflow-auto p-6">
          {loading ? (
            <p className="text-sm text-gray-500">Caricamento dettagli...</p>
          ) : null}
          {error ? (
            <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700">
              {error}
            </p>
          ) : null}
          {request ? (
            <div className="space-y-4">
              <RequestFacts request={request} />
              <ArtifactActions
                item={item}
                request={request}
                setError={setError}
              />
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function AutoSyncErrorArtifactList({
  items,
}: {
  items: CatastoPerpetualSyncItem[];
}) {
  const [selected, setSelected] = useState<CatastoPerpetualSyncItem | null>(
    null,
  );
  if (!items.length)
    return (
      <p className="text-sm text-gray-500">Nessun elemento da mostrare.</p>
    );
  return (
    <>
      <div className="mt-3 space-y-3">
        {items.map((item) => (
          <div
            className="rounded-[18px] border border-red-100 bg-red-50 px-4 py-3"
            key={item.id}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-gray-900">
                  {itemLabel(item)}
                </p>
                <p className="mt-1 text-xs text-gray-500">
                  tentativi {item.attempt_count} · prossimo ciclo{" "}
                  {formatDateTime(item.next_due_at)}
                </p>
                {item.last_error_message ? (
                  <p className="mt-1 text-sm text-red-700">
                    {item.last_error_message}
                  </p>
                ) : null}
                {item.linked_request_id ? (
                  <button
                    className="btn-secondary mt-3 px-3 py-1.5 text-xs"
                    onClick={() => setSelected(item)}
                    type="button"
                  >
                    Dettagli
                  </button>
                ) : null}
              </div>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
                {item.status}
              </span>
            </div>
          </div>
        ))}
      </div>
      {selected ? (
        <AutoSyncErrorDetails
          item={selected}
          onClose={() => setSelected(null)}
        />
      ) : null}
    </>
  );
}
