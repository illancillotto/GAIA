"use client";

import { Badge } from "@/components/ui/badge";
import type { CatAnomaliaSeverita } from "@/types/catasto";

const severityVariant: Record<string, "danger" | "warning" | "info" | "neutral"> = {
  error: "danger",
  warning: "warning",
  info: "info",
};

const severityLabel: Record<string, string> = {
  error: "Errore",
  warning: "Warning",
  info: "Info",
};

export function AnomaliaStatusBadge({ severita }: { severita: CatAnomaliaSeverita | string }) {
  const variant = severityVariant[severita] ?? "neutral";
  const label = severityLabel[severita] ?? severita;
  return <Badge variant={variant}>{label}</Badge>;
}

