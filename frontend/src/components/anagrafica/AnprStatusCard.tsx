"use client";

import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/cn";
import { getCurrentUser, getUtenzeAnprStatus, syncUtenzeAnprSubject } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type { AnprSubjectStatus, AnprSyncResult, CurrentUser } from "@/types/api";

type AnprStatusCardProps = {
  subjectId: string;
  initialStatus?: AnprSubjectStatus;
};

type ToastState = {
  tone: "success" | "danger";
  message: string;
} | null;

function buildStatusFromSyncResult(current: AnprSubjectStatus | null, result: AnprSyncResult): AnprSubjectStatus {
  return {
    subject_id: result.subject_id,
    anpr_id: result.anpr_id,
    stato_anpr:
      result.esito === "not_found"
        ? "not_found_anpr"
        : result.esito === "cancelled"
          ? "cancelled_anpr"
          : result.esito === "alive" || result.esito === "deceased" || result.esito === "error"
            ? result.esito
            : current?.stato_anpr ?? "unknown",
    data_decesso: result.data_decesso,
    luogo_decesso_comune: current?.luogo_decesso_comune ?? null,
    last_anpr_check_at: new Date().toISOString(),
    last_c030_check_at: current?.last_c030_check_at ?? null,
  };
}

function getStatusMeta(status: AnprSubjectStatus["stato_anpr"]) {
  switch (status) {
    case "alive":
      return { label: "Vivo", variant: "success" as const };
    case "deceased":
      return { label: "Attenzione: deceduto", variant: "danger" as const };
    case "not_found_anpr":
      return { label: "Non trovato in ANPR", variant: "warning" as const };
    case "cancelled_anpr":
      return { label: "Cancellato in ANPR", variant: "warning" as const };
    case "error":
      return { label: "Errore ANPR", variant: "danger" as const };
    case "unknown":
    default:
      return { label: "Stato ANPR sconosciuto", variant: "neutral" as const };
  }
}

export function AnprStatusCard({ subjectId, initialStatus }: AnprStatusCardProps) {
  const [status, setStatus] = useState<AnprSubjectStatus | null>(initialStatus ?? null);
  const [token, setToken] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(!initialStatus);
  const [syncing, setSyncing] = useState(false);
  const [toast, setToast] = useState<ToastState>(null);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  useEffect(() => {
    if (!token) {
      return;
    }
    const currentToken = token;

    async function loadStatus() {
      try {
        const [user, nextStatus] = await Promise.all([
          getCurrentUser(currentToken),
          getUtenzeAnprStatus(currentToken, subjectId),
        ]);
        setCurrentUser(user);
        setStatus(nextStatus);
      } catch {
        try {
          const user = await getCurrentUser(currentToken);
          setCurrentUser(user);
        } catch {
          setCurrentUser(null);
        }
      } finally {
        setLoadingStatus(false);
      }
    }

    void loadStatus();
  }, [subjectId, token]);

  useEffect(() => {
    if (!toast) {
      return;
    }
    const timeoutId = window.setTimeout(() => setToast(null), 3500);
    return () => window.clearTimeout(timeoutId);
  }, [toast]);

  const canSync = useMemo(() => {
    return currentUser?.role === "admin" || currentUser?.role === "reviewer" || currentUser?.role === "super_admin";
  }, [currentUser]);

  const statusMeta = getStatusMeta(status?.stato_anpr ?? null);

  async function handleSync() {
    if (!token) {
      setToast({ tone: "danger", message: "Sessione non disponibile. Effettua di nuovo il login." });
      return;
    }

    setSyncing(true);
    try {
      const result = await syncUtenzeAnprSubject(token, subjectId);
      setStatus((current) => buildStatusFromSyncResult(current, result));
      setToast({ tone: result.success ? "success" : "danger", message: result.message });
      try {
        const refreshed = await getUtenzeAnprStatus(token, subjectId);
        setStatus(refreshed);
      } catch {
        // Keep optimistic local state when the refresh fails.
      }
    } catch (error) {
      setToast({
        tone: "danger",
        message: error instanceof Error ? error.message : "Errore durante la verifica ANPR",
      });
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="rounded-2xl border border-[#d8e2d8] bg-[#f8fbf7] p-4 md:col-span-2">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-sm font-semibold text-[#1D4E35]">Verifica ANPR</p>
          <p className="mt-1 text-sm text-gray-600">Stato di riscontro anagrafico su PDND/ANPR per il soggetto selezionato.</p>
        </div>
        {canSync ? (
          <button className="btn-primary min-w-36" type="button" onClick={() => void handleSync()} disabled={syncing || loadingStatus}>
            {syncing ? "Verifica in corso..." : "Verifica ANPR"}
          </button>
        ) : null}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Badge variant={statusMeta.variant}>
          {status?.stato_anpr === "deceased" ? "⚠️ " : ""}
          {statusMeta.label}
        </Badge>
        {status?.anpr_id ? <span className="text-xs font-medium uppercase tracking-[0.14em] text-gray-500">idANPR {status.anpr_id}</span> : null}
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="rounded-xl border border-white/70 bg-white px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Ultimo controllo</p>
          <p className="mt-1 text-sm text-gray-800">
            {loadingStatus ? "Caricamento..." : status?.last_anpr_check_at ? formatDateTime(status.last_anpr_check_at) : "Mai verificato"}
          </p>
        </div>
        <div className="rounded-xl border border-white/70 bg-white px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Esito decesso</p>
          <p className="mt-1 text-sm text-gray-800">
            {status?.data_decesso ? `Data decesso: ${status.data_decesso}` : "Nessuna data decesso disponibile"}
          </p>
          {status?.luogo_decesso_comune ? <p className="mt-1 text-xs text-gray-500">Comune: {status.luogo_decesso_comune}</p> : null}
        </div>
      </div>

      {toast ? (
        <div
          className={cn(
            "mt-4 rounded-xl border px-4 py-3 text-sm",
            toast.tone === "success"
              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
              : "border-red-200 bg-red-50 text-red-700",
          )}
        >
          {toast.message}
        </div>
      ) : null}
    </div>
  );
}
