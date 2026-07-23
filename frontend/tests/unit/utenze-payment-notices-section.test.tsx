import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { UtenzePaymentNoticesSection } from "@/components/utenze/utenze-payment-notices-section";
import type { AnagraficaPaymentNotice } from "@/types/api";

const getUtenzeSubjectPaymentNotices = vi.fn();
const createCapacitasInCassSyncJob = vi.fn();

vi.mock("@/lib/api", () => ({
  createCapacitasInCassSyncJob: (...args: unknown[]) => createCapacitasInCassSyncJob(...args),
  getUtenzeSubjectPaymentNotices: (...args: unknown[]) => getUtenzeSubjectPaymentNotices(...args),
}));

function buildNotice(overrides: Partial<AnagraficaPaymentNotice>): AnagraficaPaymentNotice {
  const overrideValue = <K extends keyof AnagraficaPaymentNotice>(key: K, fallback: AnagraficaPaymentNotice[K]): AnagraficaPaymentNotice[K] =>
    Object.prototype.hasOwnProperty.call(overrides, key) ? overrides[key] as AnagraficaPaymentNotice[K] : fallback;

  return {
    id: overrideValue("id", crypto.randomUUID()),
    subject_id: overrideValue("subject_id", "subject-1"),
    source_system: overrideValue("source_system", "incass"),
    source_notice_id: overrideValue("source_notice_id", "020250001616640"),
    source_internal_id: overrideValue("source_internal_id", null),
    codice_fiscale: overrideValue("codice_fiscale", null),
    partita_iva: overrideValue("partita_iva", null),
    display_name: overrideValue("display_name", "Societa Test"),
    anno: overrideValue("anno", "2025"),
    stato_code: overrideValue("stato_code", null),
    stato_label: overrideValue("stato_label", null),
    data_scadenza: overrideValue("data_scadenza", null),
    data_pagamento: overrideValue("data_pagamento", null),
    tipo_anagrafica: overrideValue("tipo_anagrafica", null),
    ultimo_invio: overrideValue("ultimo_invio", null),
    lista_id: overrideValue("lista_id", null),
    lista_descrizione: overrideValue("lista_descrizione", null),
    indirizzo: overrideValue("indirizzo", null),
    cap: overrideValue("cap", null),
    citta: overrideValue("citta", null),
    provincia: overrideValue("provincia", null),
    importo_carico: overrideValue("importo_carico", null),
    importo_sgravio: overrideValue("importo_sgravio", null),
    importo_riscosso: overrideValue("importo_riscosso", null),
    importo_residuo: overrideValue("importo_residuo", null),
    importo_riporto: overrideValue("importo_riporto", null),
    importo_rateizzato: overrideValue("importo_rateizzato", null),
    importo_annullato: overrideValue("importo_annullato", null),
    payment_status: overrideValue("payment_status", null),
    detail_url: overrideValue("detail_url", null),
    detail_info_text: overrideValue("detail_info_text", null),
    pdf_links: overrideValue("pdf_links", []),
    synced_at: overrideValue("synced_at", "2026-05-27T11:42:04Z"),
    created_at: overrideValue("created_at", "2026-05-27T11:42:04Z"),
    updated_at: overrideValue("updated_at", "2026-05-27T11:42:04Z"),
  };
}

describe("UtenzePaymentNoticesSection", () => {
  beforeEach(() => {
    getUtenzeSubjectPaymentNotices.mockReset();
    createCapacitasInCassSyncJob.mockReset();
  });

  test("formats decimal-dot residuals correctly and does not count 'Non pagato' as paid", async () => {
    getUtenzeSubjectPaymentNotices.mockResolvedValue([
      buildNotice({
        source_notice_id: "020250001616640",
        stato_label: "Non pagato",
        importo_residuo: "73744.3700000000000",
        importo_carico: "73744.3700000000000",
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
      expect(paidCard?.textContent).toContain("0");
    });
  });

  test("renders compact details, links, pdfs and extracted info", async () => {
    getUtenzeSubjectPaymentNotices.mockResolvedValue([
      buildNotice({
        source_notice_id: "020250009999999",
        display_name: null,
        anno: null,
        stato_label: null,
        data_scadenza: null,
        lista_id: null,
        lista_descrizione: "Lista digitale",
        importo_residuo: "0.00",
        importo_carico: null,
        importo_riscosso: null,
        importo_rateizzato: null,
        detail_url: "https://incass.local/detail",
        pdf_links: [{ url: "https://incass.local/avviso.pdf", filename: "avviso.pdf", label: null, download_url: "/utenze/documents/doc-1/download" }],
        detail_info_text: [
          "Codice fiscale RSSMRA80A01H501Z Dati anagrafici ROSSI MARIO Partita P-1 Avviso 020250009999999",
          "Anno 2025 Totale imposta € 10,00 Totale residuo € 0,00 Totale sgravio € 0,00",
          "Ultimo invio PEC Ruolo R2025 Lista Lista 2025 Rate Rata 1 31/05/2026 € 10,00 Trib. 0648",
          "Raggruppamento colonne Nota interna utile.",
        ].join(" "),
      }),
    ]);

    render(<UtenzePaymentNoticesSection subjectId="subject-1" token="token" compact />);

    expect(await screen.findByText("Avvisi di pagamento")).toBeInTheDocument();
    expect(screen.getByText("Intestatario non disponibile")).toBeInTheDocument();
    expect(screen.getByText("Lista — · Lista digitale")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Apri dettaglio/ })).toHaveAttribute("href", "https://incass.local/detail");
    expect(screen.getByRole("link", { name: "PDF" })).toHaveAttribute("href", "/utenze/documents/doc-1/download");
    expect(screen.getByText("Dettagli informativi")).toBeInTheDocument();
    expect(screen.getByText("RSSMRA80A01H501Z")).toBeInTheDocument();
    expect(screen.getByText("Rate e scadenze")).toBeInTheDocument();
    expect(screen.getByText("Nota interna utile.")).toBeInTheDocument();
  });

  test("renders empty state after allowed access errors without blocking refresh success", async () => {
    getUtenzeSubjectPaymentNotices
      .mockRejectedValueOnce(new Error("403 Module access"))
      .mockResolvedValueOnce([buildNotice({ source_notice_id: "020250SYNC", importo_residuo: "0" })]);
    createCapacitasInCassSyncJob.mockResolvedValue({ id: 42 });

    render(<UtenzePaymentNoticesSection subjectId="subject-1" token="token" />);

    expect(await screen.findByText(/Nessun avviso inCASS sincronizzato/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna da inCASS" }));

    expect(await screen.findByText("Job inCASS #42 accodato. I dati si aggiorneranno al completamento del worker.")).toBeInTheDocument();
    expect(await screen.findByText("Avviso 020250SYNC")).toBeInTheDocument();
    expect(createCapacitasInCassSyncJob).toHaveBeenCalledWith("token", {
      subject_ids: ["subject-1"],
      include_details: true,
      include_partitario: true,
      include_mailing_list: false,
      download_mailing_receipts: false,
      continue_on_error: true,
      throttle_ms: 250,
    });
  });

  test("shows load and refresh errors", async () => {
    getUtenzeSubjectPaymentNotices.mockRejectedValue(new Error("Errore caricamento"));
    createCapacitasInCassSyncJob.mockRejectedValue(new Error("Errore sync"));

    render(<UtenzePaymentNoticesSection subjectId="subject-1" token="token" />);

    expect(await screen.findByText("Errore caricamento")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna da inCASS" }));
    expect(await screen.findByText("Errore sync")).toBeInTheDocument();
  });

  test("covers optional detail fallbacks", async () => {
    getUtenzeSubjectPaymentNotices.mockResolvedValue([
      buildNotice({
        id: "notice-invalid-money",
        source_notice_id: "020250INVALID",
        data_scadenza: "31/12/2026",
        importo_residuo: "non disponibile",
        detail_info_text: "abc",
        synced_at: null,
      }),
      buildNotice({
        id: "notice-rate-fallback",
        source_notice_id: "020250RATE",
        payment_status: "partial",
        importo_residuo: "1",
        detail_info_text: "Rata 1 senza importo",
        synced_at: null,
      }),
    ]);

    render(<UtenzePaymentNoticesSection subjectId="subject-1" token="token" />);

    expect(await screen.findByText("Avviso 020250INVALID")).toBeInTheDocument();
    expect(screen.getByText("Societa Test · scadenza 31/12/2026")).toBeInTheDocument();
    expect(screen.getByText("non disponibile")).toBeInTheDocument();
    expect(screen.getByText("Parziale")).toBeInTheDocument();
    expect(screen.getByText("Rata 1")).toBeInTheDocument();
    expect(screen.getByText("Scadenza non disponibile")).toBeInTheDocument();
    expect(screen.getByText("Importo non disponibile")).toBeInTheDocument();
    expect(screen.queryByText("Sync")).not.toBeInTheDocument();
  });

  test("shows string load and refresh errors while sync is pending", async () => {
    getUtenzeSubjectPaymentNotices.mockRejectedValue("Errore stringa");
    let rejectSync!: (reason: string) => void;
    createCapacitasInCassSyncJob.mockReturnValue(new Promise((_resolve, reject) => {
      rejectSync = reject;
    }));

    render(<UtenzePaymentNoticesSection subjectId="subject-1" token="token" />);

    expect(await screen.findByText("Errore stringa")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna da inCASS" }));
    expect(await screen.findByRole("button", { name: "Accodo sync..." })).toBeDisabled();

    rejectSync("Errore sync stringa");

    expect(await screen.findByText("Errore sync stringa")).toBeInTheDocument();
  });
});
