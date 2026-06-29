import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { UtenzePaymentNoticesSection } from "@/components/utenze/utenze-payment-notices-section";
import type { AnagraficaPaymentNotice } from "@/types/api";

const getUtenzeSubjectPaymentNotices = vi.fn();

vi.mock("@/lib/api", () => ({
  getUtenzeSubjectPaymentNotices: (...args: unknown[]) => getUtenzeSubjectPaymentNotices(...args),
}));

function buildNotice(overrides: Partial<AnagraficaPaymentNotice>): AnagraficaPaymentNotice {
  return {
    id: overrides.id ?? crypto.randomUUID(),
    subject_id: overrides.subject_id ?? "subject-1",
    source_system: overrides.source_system ?? "incass",
    source_notice_id: overrides.source_notice_id ?? "020250001616640",
    source_internal_id: overrides.source_internal_id ?? null,
    codice_fiscale: overrides.codice_fiscale ?? null,
    partita_iva: overrides.partita_iva ?? null,
    display_name: overrides.display_name ?? "Societa Test",
    anno: overrides.anno ?? "2025",
    stato_code: overrides.stato_code ?? null,
    stato_label: overrides.stato_label ?? null,
    data_scadenza: overrides.data_scadenza ?? null,
    data_pagamento: overrides.data_pagamento ?? null,
    tipo_anagrafica: overrides.tipo_anagrafica ?? null,
    ultimo_invio: overrides.ultimo_invio ?? null,
    lista_id: overrides.lista_id ?? null,
    lista_descrizione: overrides.lista_descrizione ?? null,
    indirizzo: overrides.indirizzo ?? null,
    cap: overrides.cap ?? null,
    citta: overrides.citta ?? null,
    provincia: overrides.provincia ?? null,
    importo_carico: overrides.importo_carico ?? null,
    importo_sgravio: overrides.importo_sgravio ?? null,
    importo_riscosso: overrides.importo_riscosso ?? null,
    importo_residuo: overrides.importo_residuo ?? null,
    importo_riporto: overrides.importo_riporto ?? null,
    importo_rateizzato: overrides.importo_rateizzato ?? null,
    importo_annullato: overrides.importo_annullato ?? null,
    detail_url: overrides.detail_url ?? null,
    detail_info_text: overrides.detail_info_text ?? null,
    pdf_links: overrides.pdf_links ?? [],
    synced_at: overrides.synced_at ?? "2026-05-27T11:42:04Z",
    created_at: overrides.created_at ?? "2026-05-27T11:42:04Z",
    updated_at: overrides.updated_at ?? "2026-05-27T11:42:04Z",
  };
}

describe("UtenzePaymentNoticesSection", () => {
  beforeEach(() => {
    getUtenzeSubjectPaymentNotices.mockReset();
  });

  test("formats decimal-dot residuals correctly and does not count 'Non pagato' as paid", async () => {
    getUtenzeSubjectPaymentNotices.mockResolvedValue([
      buildNotice({
        source_notice_id: "020250001616640",
        stato_label: "Non pagato",
        importo_residuo: "73744.37",
        importo_carico: "73744.37",
        importo_riscosso: "0",
        importo_rateizzato: "0",
      }),
      buildNotice({
        source_notice_id: "020240001804580",
        stato_label: "Rateizzato e pagato in parte",
        importo_residuo: "39716.19",
        importo_carico: "76666.25",
        importo_riscosso: "-39716.22",
        importo_rateizzato: "79432.41",
      }),
    ]);

    render(<UtenzePaymentNoticesSection subjectId="subject-1" token="token" />);

    expect(await screen.findByText("Avvisi di pagamento sincronizzati sul soggetto.")).toBeInTheDocument();
    expect(screen.getAllByText(/113\.460,56/).length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText(/73\.744,37/).length).toBeGreaterThanOrEqual(1);

    await waitFor(() => {
      const paidCard = screen.getByText("Con stato pagato").closest("div");
      expect(paidCard?.textContent).toContain("1");
    });
  });
});
