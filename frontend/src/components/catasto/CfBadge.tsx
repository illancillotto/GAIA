"use client";

import { cn } from "@/lib/cn";

export function CfBadge({
  codiceFiscale,
  isValid,
  className,
}: {
  codiceFiscale: string | null | undefined;
  isValid: boolean | null | undefined;
  className?: string;
}) {
  const value = (codiceFiscale ?? "").trim();
  const showValue = value.length > 0 ? value : "—";
  const tone =
    isValid == null
      ? "bg-gray-100 text-gray-600"
      : isValid
        ? "bg-emerald-50 text-emerald-700"
        : "bg-red-50 text-red-700";

  return (
    <span className={cn("inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium", tone, className)}>
      <span className={cn("h-1.5 w-1.5 rounded-full", isValid == null ? "bg-gray-400" : isValid ? "bg-emerald-500" : "bg-red-500")} />
      <span className="font-mono">{showValue}</span>
    </span>
  );
}

