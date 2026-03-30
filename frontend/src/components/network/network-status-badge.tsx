import { Badge } from "@/components/ui/badge";

type NetworkStatusBadgeProps = {
  status: string;
};

const variantMap: Record<string, "success" | "danger" | "warning" | "info" | "neutral"> = {
  online: "success",
  offline: "danger",
  open: "danger",
  acknowledged: "neutral",
  resolved: "success",
  ignored: "neutral",
  completed: "success",
  warning: "warning",
  info: "info",
  danger: "danger",
  new: "warning",
  missing: "danger",
  changed: "info",
};

export function NetworkStatusBadge({ status }: NetworkStatusBadgeProps) {
  return <Badge variant={variantMap[status] ?? "neutral"}>{status.replace("_", " ")}</Badge>;
}
