import { Badge } from "@/components/ui/badge";

export type PermissionLevel = "rw" | "read" | "none" | "deny";

type PermissionBadgeProps = {
  level: PermissionLevel;
};

export function PermissionBadge({ level }: PermissionBadgeProps) {
  if (level === "rw") {
    return <Badge variant="success">R+W</Badge>;
  }

  if (level === "read") {
    return <Badge variant="info">Lettura</Badge>;
  }

  if (level === "deny") {
    return <Badge variant="danger">Negato</Badge>;
  }

  return <Badge variant="neutral">Nessun accesso</Badge>;
}
