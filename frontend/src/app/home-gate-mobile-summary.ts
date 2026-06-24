import { formatDateTime } from "@/lib/presentation";
import type { GateMobileSyncStatusResponse } from "@/types/api";

export type HomeGateMobileSummary = {
  value: string;
  copy: string;
};

export function buildHomeGateMobileSummary(status: GateMobileSyncStatusResponse | null): HomeGateMobileSummary {
  if (!status) {
    return {
      value: "Non disponibile",
      copy: "Monitor del canale tablet per letture contatori non caricato.",
    };
  }

  if (!status.sync_enabled) {
    return {
      value: "Disattiva",
      copy: "Flag runtime spento: i tablet contatori non ricevono aggiornamenti automatici.",
    };
  }

  if (!status.gateway_configured || !status.token_configured) {
    return {
      value: "Config mancante",
      copy: "Gateway pubblico o token tecnico per i tablet contatori non configurati.",
    };
  }

  const lastRun = status.last_run;
  if (!lastRun) {
    return {
      value: "Pronta",
      copy: "Canale tablet configurato per contatori, ma nessun run registrato.",
    };
  }

  if (lastRun.status === "running") {
    return {
      value: "In esecuzione",
      copy: `Aggiornamento tablet contatori avviato ${formatDateTime(lastRun.started_at)}.`,
    };
  }

  if (lastRun.status === "failed") {
    return {
      value: "Errore",
      copy: `Ultimo aggiornamento tablet contatori fallito ${formatDateTime(lastRun.finished_at ?? lastRun.started_at)}.`,
    };
  }

  if (lastRun.status === "skipped") {
    return {
      value: "Saltata",
      copy: `Ultimo aggiornamento tablet contatori saltato ${formatDateTime(lastRun.finished_at ?? lastRun.started_at)}.`,
    };
  }

  return {
    value: `${lastRun.operators_pushed}`,
    copy: `Operatori pubblicati verso i tablet letture ${formatDateTime(lastRun.finished_at ?? lastRun.started_at)}.`,
  };
}
