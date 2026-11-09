import { describe, expect, it } from "vitest";
import { GATE_MOBILE_CONSOLE_ROLE_OPTIONS, gateMobileConsoleRoleLabel } from "@/features/operazioni/console-roles";

describe("GATE console role metadata", () => {
  it("offers the HR role explicitly alongside the existing roles", () => {
    expect(GATE_MOBILE_CONSOLE_ROLE_OPTIONS.map(option => option.value)).toEqual(["console_admin", "device_manager", "team_manager", "viewer", "hr_manager"]);
    for (const option of GATE_MOBILE_CONSOLE_ROLE_OPTIONS) expect(gateMobileConsoleRoleLabel(option.value)).toBe(option.label);
    expect(gateMobileConsoleRoleLabel("hr_manager")).toContain("tutte le aree");
  });
  it("keeps the unassigned fallback for missing roles", () => {
    expect(gateMobileConsoleRoleLabel(null)).toBe("Non assegnato");
    expect(gateMobileConsoleRoleLabel(undefined)).toBe("Non assegnato");
  });
});
