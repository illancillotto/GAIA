"use client";

import { MetricCard } from "@/components/ui/metric-card";

export function KpiCard({
  label,
  value,
  sub,
  variant,
}: {
  label: string;
  value: string | number;
  sub?: string;
  variant?: "default" | "success" | "danger" | "warning" | "info";
}) {
  return <MetricCard label={label} value={value} sub={sub} variant={variant} />;
}

