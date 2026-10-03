import { describe, expect, test } from "vitest";
import { custodyDate, statusLabel, typeLabel } from "@/features/dotazioni/presentation";

describe("Dotazioni Italian presentation", () => {
  test("labels statuses and types without changing extensible identifiers", () => {
    expect(statusLabel("in_use")).toBe("In custodia");
    expect(statusLabel("maintenance")).toBe("In manutenzione");
    expect(statusLabel("custom-state")).toBe("custom-state");
    expect(typeLabel("phone")).toBe("Telefono");
    expect(typeLabel("custom-tool")).toBe("custom-tool");
    expect(typeLabel("constructor")).toBe("constructor");
  });
  test("uses Rome timezone including summer and winter time", () => {
    expect(custodyDate("2026-10-01T07:15:00Z")).toBe("01/10/2026, 09:15");
    expect(custodyDate("2026-12-01T07:15:00Z")).toBe("01/12/2026, 08:15");
    expect(custodyDate(null)).toBe("—");
    expect(custodyDate("invalid-date")).toBe("Data non disponibile");
  });
});
