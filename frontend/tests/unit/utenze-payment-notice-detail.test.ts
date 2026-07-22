import { describe, expect, test } from "vitest";

import {
  buildNoticeResidualNotes,
  extractNoticeDetailFields,
  extractNoticeRateDetails,
  extractTokenSegment,
  normalizeNoticeDetailText,
} from "@/lib/utenze-payment-notice-detail";

describe("utenze payment notice detail helpers", () => {
  test("extracts fields, rates and residual notes from inCASS detail text", () => {
    const detailText = `
      inCass server noise
      Codice fiscale RSSMRA80A01H501Z Dati anagrafici ROSSI MARIO Partita P-1 Avviso 020250001
      Anno 2025 Totale imposta € 100,00 Totale residuo € 60,00 Totale sgravio € 0,00
      Ultimo invio PEC Ruolo R2025 Lista Lista 2025 Rate Rata tot. 31/05/2026 € 60,00 Trib. 0648
      Raggruppamento colonne Nota utile da mostrare.
    `;

    const fields = extractNoticeDetailFields(detailText);
    expect(normalizeNoticeDetailText(" a\n b   c ")).toBe("a b c");
    expect(extractTokenSegment("A start value end", "missing", ["end"])).toBeNull();
    expect(extractTokenSegment("A start end", "start", ["end"])).toBeNull();
    expect(fields.find((field) => field.label === "Codice fiscale")?.value).toBe("RSSMRA80A01H501Z");
    expect(fields.find((field) => field.label === "Avviso")?.value).toBe("020250001");
    expect(extractNoticeRateDetails(detailText)[0]).toEqual({
      label: "Rata tot.",
      dueDate: "31/05/2026",
      amount: "€ 60,00",
    });
    expect(buildNoticeResidualNotes(detailText, fields)).toContain("Nota utile da mostrare.");
  });

  test("handles missing optional rate parts and fully cleaned notes", () => {
    expect(extractNoticeDetailFields("nessun token utile")).toEqual([]);
    expect(extractNoticeRateDetails("Rata 1")).toEqual([{ label: "Rata 1", dueDate: null, amount: null }]);
    expect(buildNoticeResidualNotes("Codice fiscale RSSMRA80A01H501Z", [{ label: "Codice fiscale", value: "RSSMRA80A01H501Z" }])).toEqual([]);
  });
});
