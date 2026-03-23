import type { EffectivePermission } from "@/types/api";

export function formatDateTime(value: string | null): string {
  if (!value) return "—";

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;

  return new Intl.DateTimeFormat("it-IT", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(parsed);
}

export function formatDuration(value: number | null): string {
  if (value == null) return "—";
  if (value < 1000) return `${value} ms`;

  return `${(value / 1000).toFixed(1)} s`;
}

export function getPermissionLevel(permission: Pick<EffectivePermission, "can_read" | "can_write" | "is_denied">): "deny" | "rw" | "read" | "none" {
  if (permission.is_denied) return "deny";
  if (permission.can_write) return "rw";
  if (permission.can_read) return "read";
  return "none";
}
