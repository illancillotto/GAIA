import type { GateMobileConsoleRole } from "./api/client";

export const GATE_MOBILE_CONSOLE_ROLE_OPTIONS: Array<{ value: GateMobileConsoleRole; label: string }> = [
  { value: "console_admin", label: "Console admin" },
  { value: "device_manager", label: "Device manager" },
  { value: "team_manager", label: "Team manager" },
  { value: "viewer", label: "Viewer" },
  { value: "hr_manager", label: "Risorse umane · tutte le aree" },
];

export function gateMobileConsoleRoleLabel(role: GateMobileConsoleRole | null | undefined): string {
  return GATE_MOBILE_CONSOLE_ROLE_OPTIONS.find(option => option.value === role)?.label ?? "Non assegnato";
}
