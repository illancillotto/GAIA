import { describe, expect, test } from "vitest";

import {
  buildPaymentNoticeSummary,
  getPaymentNoticeStatus,
  isPaidLikeStatus,
  parseNoticeAmount,
} from "@/lib/utenze-payment-notices-summary";
import type { AnagraficaPaymentNotice } from "@/types/api";

function notice(overrides: Partial<AnagraficaPaymentNotice>): AnagraficaPaymentNotice {
  return {
    id: "notice-1",
    subject_id: "subject-1",
    source_system: "incass",
    source_notice_id: "020250001",
    source_internal_id: null,
    codice_fiscale: null,
    partita_iva: null,
    display_name: null,
    anno: "2025",
    stato_code: null,
    stato_label: null,
    data_scadenza: null,
    data_pagamento: null,
    tipo_anagrafica: null,
    ultimo_invio: null,
    lista_id: null,
    lista_descrizione: null,
    indirizzo: null,
    cap: null,
    citta: null,
    provincia: null,
    importo_carico: null,
    importo_sgravio: null,
    importo_riscosso: null,
    importo_residuo: null,
    importo_riporto: null,
    importo_rateizzato: null,
    importo_annullato: null,
    detail_url: null,
    detail_info_text: null,
    pdf_links: [],
    synced_at: null,
    created_at: null,
    updated_at: null,
    ...overrides,
  };
}

describe("utenze payment notices summary", () => {
  test.each([
    [[], "unpaid", "Nessun avviso", "Nessun avviso inCASS sincronizzato."],
    [["unpaid"], "unpaid", "Non pagatore", "1 non pagati, 0 parziali, 0 pagati."],
    [["paid"], "partial", "Pagamenti parziali", "0 non pagati, 0 parziali, 1 pagati."],
    [["partial"], "partial", "Pagamenti parziali", "0 non pagati, 1 parziali, 0 pagati."],
    [["paid", "partial", "unpaid"], "partial", "Pagamenti parziali", "1 non pagati, 1 parziali, 1 pagati."],
  ] as const)("preserves summary for explicit statuses %j", (statuses, status, label, description) => {
    const items = statuses.map((payment_status) => notice({ payment_status, importo_residuo: "10" }));
    const original = structuredClone(items);
    const summary = buildPaymentNoticeSummary(items);
    expect(summary).toEqual({
      totalResiduo: statuses.length * 10,
      paidCount: statuses.filter((value) => value === "paid").length,
      partialCount: statuses.filter((value) => value === "partial").length,
      unpaidCount: statuses.filter((value) => value === "unpaid").length,
      noticesCount: statuses.length, status, label, description,
    });
    expect(items).toEqual(original);
  });

  test.each(["-1", "0", "0.0049", "0.005", "0.0051"])(
    "preserves the strict residual threshold for %s", (residual) => {
      const summary = buildPaymentNoticeSummary([notice({ payment_status: "unpaid", importo_residuo: residual })]);
      const paid = Number(residual) <= 0.005;
      expect(summary.status).toBe(paid ? "paid" : "unpaid");
      expect(summary.totalResiduo).toBe(Number(residual));
      expect(summary.label).toBe(paid ? "Pagatore regolare" : "Non pagatore");
      expect(summary.description).toBe(paid ? "Nessun residuo aperto sugli avvisi sincronizzati." : "1 non pagati, 0 parziali, 0 pagati.");
    },
  );

  test.each(["paid", "partial", "unpaid"] as const)(
    "preserves explicit %s status over contradictory derived states", (status) => {
      for (const overrides of [
        { importo_residuo: "0", data_pagamento: "2026-10-02", stato_label: "Pagato" },
        { importo_carico: "100", importo_residuo: "60", importo_riscosso: "40" },
        { importo_carico: "100", importo_residuo: "100", stato_label: "Non pagato" },
      ]) {
        const item = notice({ ...overrides, payment_status: status });
        const original = structuredClone(item);
        expect(getPaymentNoticeStatus(item)).toBe(status);
        expect(item).toEqual(original);
      }
    },
  );

  test.each([undefined, null, "", "PAID", " paid", "pending", "toString", "__proto__"])(
    "preserves derived classification for unrecognized explicit status %s", (status) => {
      for (const [overrides, expected] of [
        [{ importo_residuo: "0" }, "paid"],
        [{ importo_carico: "100", importo_residuo: "60" }, "partial"],
        [{ importo_carico: "100", importo_residuo: "100" }, "unpaid"],
      ] as const) {
        const item = notice({ ...overrides, payment_status: status as AnagraficaPaymentNotice["payment_status"] });
        const original = structuredClone(item);
        expect(getPaymentNoticeStatus(item)).toBe(expected);
        expect(item).toEqual(original);
      }
    },
  );

  test("parses decimal-dot amounts with long fractional tails as decimals", () => {
    expect(parseNoticeAmount("1499.7100000000000")).toBe(1499.71);
    expect(parseNoticeAmount("1.499,71")).toBe(1499.71);
    expect(parseNoticeAmount("1499,71")).toBe(1499.71);
    expect(parseNoticeAmount("1.499.710")).toBe(1499710);
    expect(parseNoticeAmount("1.499.7100")).toBe(1499.71);
    expect(parseNoticeAmount("1499.71")).toBe(1499.71);
    expect(parseNoticeAmount("1499")).toBe(1499);
    expect(parseNoticeAmount("")).toBeNull();
    expect(parseNoticeAmount("--")).toBeNull();
    expect(parseNoticeAmount("bad")).toBeNull();
  });

  test("builds subject payment status summary", () => {
    const summary = buildPaymentNoticeSummary([
      notice({ importo_carico: "100.00", importo_residuo: "0.00", stato_label: "Pagato" }),
      notice({ importo_carico: "100.00", importo_riscosso: "40.00", importo_residuo: "60.00" }),
      notice({ importo_carico: "80.00", importo_residuo: "80.00", stato_label: "Non pagato" }),
    ]);

    expect(getPaymentNoticeStatus(notice({ importo_residuo: "0.0000000000000" }))).toBe("paid");
    expect(summary.totalResiduo).toBe(140);
    expect(summary.paidCount).toBe(1);
    expect(summary.partialCount).toBe(1);
    expect(summary.unpaidCount).toBe(1);
    expect(summary.label).toBe("Pagamenti parziali");
  });

  test("classifies paid by payment date and closed residual summary", () => {
    const summary = buildPaymentNoticeSummary([
      notice({ data_pagamento: "2026-07-22", importo_residuo: "0.00" }),
    ]);

    expect(getPaymentNoticeStatus(notice({ data_pagamento: "2026-07-22", importo_residuo: "10.00" }))).toBe("paid");
    expect(summary.status).toBe("paid");
    expect(summary.label).toBe("Pagatore regolare");
    expect(summary.description).toBe("Nessun residuo aperto sugli avvisi sincronizzati.");
  });

  test("does not classify missing notices as debtor", () => {
    expect(buildPaymentNoticeSummary([]).label).toBe("Nessun avviso");
  });

  test("classifies fully open notices as non payer", () => {
    const summary = buildPaymentNoticeSummary([
      notice({ importo_residuo: null, stato_label: "Non pagato" }),
      notice({ importo_carico: "80.00", importo_residuo: "80.00", stato_label: "Non pagato" }),
    ]);

    expect(summary.status).toBe("unpaid");
    expect(summary.label).toBe("Non pagatore");
    expect(summary.totalResiduo).toBe(80);
  });

  test("does not classify partial payment label as fully paid", () => {
    expect(getPaymentNoticeStatus(notice({ importo_carico: "100,00", importo_residuo: "60,00", stato_label: "Parzialmente pagato" }))).toBe("partial");
  });

  test("covers explicit payment statuses and paid-like labels", () => {
    expect(getPaymentNoticeStatus(notice({ payment_status: "partial", importo_residuo: "0" }))).toBe("partial");
    expect(isPaidLikeStatus(null)).toBe(false);
    expect(isPaidLikeStatus("Pagato")).toBe(true);
    expect(isPaidLikeStatus("Pagato in parte")).toBe(false);
    expect(isPaidLikeStatus("Senza pagamenti")).toBe(false);
  });
});
