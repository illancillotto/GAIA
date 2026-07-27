"use client";

import { useState } from "react";

import { formatDateTime } from "@/lib/presentation";
import type { AnagraficaCatastoDocument, ElaborazioneBatchDetail } from "@/types/api";

export type SubjectVisuraRequestInfo = {
  identifier: string;
  identifierLabel: string;
  subjectKind: "PF" | "PNF";
};

type Props = {
  requestState: SubjectVisuraRequestInfo | null;
  latestVisura: AnagraficaCatastoDocument | null;
  isRequesting: boolean;
  error: string | null;
  result: ElaborazioneBatchDetail | null;
  isEmbedded: boolean;
  nowMs?: number;
  onRequest: () => void | Promise<void>;
  onPreviewLatest: (document: AnagraficaCatastoDocument) => void | Promise<void>;
};

const RECENT_VISURA_WINDOW_MS = 7 * 24 * 60 * 60 * 1000;

export function isVisuraYoungerThanSevenDays(visura: AnagraficaCatastoDocument | null, nowMs = Date.now()): boolean {
  if (!visura) return false;
  const createdAtMs = new Date(visura.created_at).getTime();
  return Number.isFinite(createdAtMs) && createdAtMs <= nowMs && nowMs - createdAtMs < RECENT_VISURA_WINDOW_MS;
}

export function UtenzeSubjectVisuraCard({
  requestState,
  latestVisura,
  isRequesting,
  error,
  result,
  isEmbedded,
  nowMs,
  onRequest,
  onPreviewLatest,
}: Props) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const hasRecentVisura = isVisuraYoungerThanSevenDays(latestVisura, nowMs);

  function handleRequestClick() {
    if (hasRecentVisura) {
      setConfirmOpen(true);
      return;
    }
    void onRequest();
  }

  function handleConfirmRequest() {
    setConfirmOpen(false);
    void onRequest();
  }

  return (
    <div className="rounded-2xl border border-[#d8e2d8] bg-[#f8fbf7] p-4 md:col-span-2">
      {confirmOpen && latestVisura ? (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl" role="dialog" aria-modal="true" aria-labelledby="recent-visura-confirm-title">
            <p id="recent-visura-confirm-title" className="section-title">Conferma nuova visura</p>
            <p className="section-copy mt-2">
              La visura più recente è stata scaricata il {formatDateTime(latestVisura.created_at)}: ha meno di 7 giorni. Vuoi richiedere comunque una nuova visura SISTER?
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button className="btn-secondary" type="button" onClick={() => setConfirmOpen(false)}>
                Annulla
              </button>
              <button className="btn-primary" type="button" onClick={handleConfirmRequest} disabled={isRequesting}>
                Conferma richiesta
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-sm font-semibold text-[#1D4E35]">Visura per soggetto</p>
          <p className="mt-1 text-sm text-gray-600">
            Invia una richiesta rapida al runtime SISTER usando i dati anagrafici del soggetto aperto.
          </p>
        </div>
        <button
          className="btn-primary min-w-44"
          type="button"
          onClick={handleRequestClick}
          disabled={isRequesting || !requestState}
        >
          {isRequesting ? "Richiesta in corso..." : "Richiedi visura"}
        </button>
      </div>

      {latestVisura ? (
        <div className="mt-4 rounded-xl border border-emerald-100 bg-white px-4 py-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Ultima visura scaricata</p>
              <p className="mt-1 text-sm font-medium text-gray-900">{formatDateTime(latestVisura.created_at)}</p>
              <p className="mt-1 text-xs text-gray-500">{latestVisura.filename}</p>
            </div>
            <button
              className="text-sm font-medium text-[#1D4E35] transition hover:text-[#163a29]"
              type="button"
              onClick={() => void onPreviewLatest(latestVisura)}
            >
              Visualizza visura
            </button>
          </div>
        </div>
      ) : null}

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-white/70 bg-white px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Tipo soggetto</p>
          <p className="mt-1 text-sm text-gray-800">{requestState?.subjectKind ?? "Non disponibile"}</p>
        </div>
        <div className="rounded-xl border border-white/70 bg-white px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Identificativo</p>
          <p className="mt-1 text-sm text-gray-800">
            {requestState ? `${requestState.identifierLabel}: ${requestState.identifier}` : "Codice fiscale o partita IVA mancanti"}
          </p>
        </div>
        <div className="rounded-xl border border-white/70 bg-white px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Profilo richiesta</p>
          <p className="mt-1 text-sm text-gray-800">Attualita · Sintetica</p>
        </div>
      </div>

      {error ? <p className="mt-4 text-sm text-red-600">{error}</p> : null}
      {hasRecentVisura && latestVisura ? (
        <p className="mt-4 text-sm text-amber-700">
          Esiste già una visura scaricata il {formatDateTime(latestVisura.created_at)}. Una nuova richiesta richiede conferma perché la visura ha meno di 7 giorni.
        </p>
      ) : null}
      {result ? (
        <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          <p>Richiesta visura avviata sul batch {result.name}.</p>
          {isEmbedded ? (
            <button
              className="btn-secondary mt-3"
              type="button"
              onClick={() => window.open(`/elaborazioni/batches/${result.id}`, "_blank", "noopener,noreferrer")}
            >
              Apri batch
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
