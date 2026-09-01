import { describe, expect, test } from "vitest";

import {
  formatDateTime,
  formatHaFromMq,
  formatHectares,
  formatIndice,
  formatUtenzaPartita,
  getUtenzaSubjectLabel,
  normalizeIdentifier,
  particellaReference,
  renderResolutionLabel,
  resolveUtenzaCertContext,
} from "@/app/catasto/particelle/[id]/particella-detail-helpers";
import type { CatParticellaConsorzio, CatParticellaDetail, CatUtenzaIrrigua } from "@/types/catasto";

const utenza = {
  id: "utenza-1",
  cco: "123",
  cod_frazione: "4",
  codice_fiscale: " RSS MR A ",
  subject_display_name: " Mario Rossi ",
  denominazione: "Denominazione",
} as CatUtenzaIrrigua;

function occupancy(overrides: Record<string, unknown> = {}) {
  return {
    id: "occupancy",
    utenza_id: utenza.id,
    com: "001",
    pvc: "002",
    fra: "3",
    ccs: "4",
    is_current: false,
    valid_from: "2025-01-01",
    updated_at: "2025-01-01T00:00:00Z",
    ...overrides,
  };
}

function consorzio(occupancies: ReturnType<typeof occupancy>[]): CatParticellaConsorzio {
  return { particella_id: "parcel", units: [{ occupancies }] } as CatParticellaConsorzio;
}

describe("particella detail helpers", () => {
  test("formats cadastral values and defensive fallbacks", () => {
    expect(formatHaFromMq("10000")).toBe("1,00");
    expect(formatHaFromMq(20_000)).toBe("2,00");
    expect(formatHaFromMq("not-a-number")).toBe("0,00");
    expect(formatIndice(null)).toBe("—");
    expect(formatIndice("bad")).toBe("—");
    expect(formatIndice(1.2)).toBe("1,20");
    expect(formatHectares(undefined)).toBe("—");
    expect(formatHectares("bad")).toBe("—");
    expect(formatHectares("1.25")).toBe("1,25 ha");
    expect(formatHectares(2.5)).toBe("2,50 ha");
    expect(formatDateTime(null)).toBe("Mai");
    expect(formatDateTime("invalid-date")).toBe("invalid-date");
    expect(formatDateTime("2026-01-02T10:00:00Z")).toBe(new Date("2026-01-02T10:00:00Z").toLocaleString("it-IT"));
  });

  test.each([
    ["swapped_arborea_terralba", "Comune corretto da GAIA (Arborea/Terralba)"],
    ["source_match", "Comune sorgente confermato"],
    ["resolved_from_particella", "Comune risolto dalla particella GAIA"],
    ["source_only", "Solo sorgente Capacitas"],
    ["custom", "custom"],
    [null, "—"],
  ])("renders resolution mode %s", (mode, expected) => {
    expect(renderResolutionLabel(mode)).toBe(expected);
  });

  test("normalizes identifiers and builds parcel references", () => {
    expect(normalizeIdentifier(" rss mr a ")).toBe("RSSMRA");
    expect(normalizeIdentifier("   ")).toBeNull();
    expect(normalizeIdentifier(null)).toBeNull();
    expect(particellaReference(null)).toBe("Particella");
    expect(particellaReference({ foglio: "14", particella: "82", subalterno: null } as CatParticellaDetail)).toBe("Fg.14 Part.82");
    expect(particellaReference({ foglio: "14", particella: "82", subalterno: "3" } as CatParticellaDetail)).toBe("Fg.14 Part.82 Sub.3");
  });

  test("selects the best complete occupancy for a certificate", () => {
    expect(resolveUtenzaCertContext(null, utenza)).toEqual({});
    expect(resolveUtenzaCertContext(consorzio([occupancy({ utenza_id: "other" }), occupancy({ com: null })]), utenza)).toEqual({});

    const current = occupancy({ id: "current", is_current: true, valid_from: "2024-01-01" });
    expect(resolveUtenzaCertContext(consorzio([occupancy({ valid_from: "2026-01-01" }), current]), utenza)).toEqual({ com: "001", pvc: "002", fra: "3", ccs: "4" });

    const newestValidity = occupancy({ id: "valid", valid_from: "2026-01-01", ccs: null });
    expect(resolveUtenzaCertContext(consorzio([occupancy(), newestValidity]), utenza)).toEqual({ com: "001", pvc: "002", fra: "3", ccs: undefined });

    const newestUpdate = occupancy({ id: "updated", updated_at: "2026-02-01T00:00:00Z", com: null });
    const completeNewestUpdate = occupancy({ id: "updated-complete", updated_at: "2026-02-01T00:00:00Z", com: "009" });
    expect(resolveUtenzaCertContext(consorzio([occupancy(), newestUpdate, completeNewestUpdate]), utenza).com).toBe("009");
    expect(resolveUtenzaCertContext(consorzio([
      occupancy({ id: "null-dates", valid_from: null, updated_at: null }),
      occupancy({ id: "dated", valid_from: null, updated_at: "2026-01-01" }),
    ]), utenza).com).toBe("001");
    expect(resolveUtenzaCertContext(consorzio([
      occupancy({ id: "null-update-1", updated_at: null }),
      occupancy({ id: "null-update-2", updated_at: null }),
    ]), utenza).com).toBe("001");
  });

  test("formats Capacitas account references and subject labels", () => {
    expect(formatUtenzaPartita(null, { ...utenza, cco: null })).toBeNull();
    expect(formatUtenzaPartita(null, { ...utenza, cco: " " })).toBeNull();
    expect(formatUtenzaPartita(null, { ...utenza, cod_frazione: null })).toBe("000000123");
    expect(formatUtenzaPartita(null, utenza)).toBe("000000123/04/00000");
    expect(formatUtenzaPartita(consorzio([occupancy()]), utenza)).toBe("000000123/03/00004");
    expect(getUtenzaSubjectLabel(utenza)).toBe("Mario Rossi");
    expect(getUtenzaSubjectLabel({ ...utenza, subject_display_name: " " })).toBe("Denominazione");
    expect(getUtenzaSubjectLabel({ ...utenza, subject_display_name: null, denominazione: null })).toBeNull();
  });
});
