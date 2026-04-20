"use client";

import { Badge } from "@/components/ui/badge";
import type { CatImportBatchStatus } from "@/types/catasto";

const statusVariant: Record<string, "info" | "success" | "danger" | "warning" | "neutral"> = {
  processing: "info",
  completed: "success",
  failed: "danger",
  replaced: "warning",
};

const statusLabel: Record<string, string> = {
  processing: "In lavorazione",
  completed: "Completato",
  failed: "Fallito",
  replaced: "Sostituito",
};

export function ImportStatusBadge({ status }: { status: CatImportBatchStatus | string }) {
  const variant = statusVariant[status] ?? "neutral";
  const label = statusLabel[status] ?? status;
  return <Badge variant={variant}>{label}</Badge>;
}

