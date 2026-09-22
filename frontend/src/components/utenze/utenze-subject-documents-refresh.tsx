"use client";

import { useState } from "react";

import { getUtenzeSubject, importUtenzeSubjectFromNas } from "@/lib/api";
import type { UtenzeSubjectDetail } from "@/types/api";

type Props = {
  token: string;
  subjectId: string;
  onRefreshed: (subject: UtenzeSubjectDetail) => void;
};

export function UtenzeSubjectDocumentsRefresh({ token, subjectId, onRefreshed }: Props) {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refreshSubjectDocumentsFromNas() {
    setIsRefreshing(true);
    setMessage(null);
    setError(null);
    try {
      const result = await importUtenzeSubjectFromNas(token, subjectId);
      onRefreshed(await getUtenzeSubject(token, subjectId));
      setMessage(
        `Documenti aggiornati: ${result.created_documents} nuovi, ${result.updated_documents} gia presenti aggiornati.`,
      );
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : "Errore aggiornamento documenti dal NAS");
    } finally {
      setIsRefreshing(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button className="btn-primary" disabled={isRefreshing} onClick={() => void refreshSubjectDocumentsFromNas()} type="button">
        {isRefreshing ? "Aggiornamento..." : "Aggiorna documenti"}
      </button>
      {message ? <p className="max-w-72 text-right text-xs text-[#1D4E35]">{message}</p> : null}
      {error ? <p className="max-w-72 text-right text-xs text-red-600">{error}</p> : null}
    </div>
  );
}
