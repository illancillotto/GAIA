import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { RuoloAvvisiSection } from "@/components/ruolo/ruolo-avvisi-section";
import type { RuoloAvvisoListItemResponse } from "@/types/ruolo";

const getAvvisiBySubject = vi.fn();

vi.mock("@/lib/ruolo-api", () => ({
  getAvvisiBySubject: (...args: unknown[]) => getAvvisiBySubject(...args),
}));

function buildAvviso(overrides: Partial<RuoloAvvisoListItemResponse> = {}): RuoloAvvisoListItemResponse {
  return {
    id: "avviso-1",
    codice_cnc: "CNC-001",
    anno_tributario: 2025,
    subject_id: "subject-1",
    codice_fiscale_raw: "RSSMRA80A01H501Z",
    nominativo_raw: "ROSSI MARIO",
    codice_utenza: "UT-1",
    importo_totale_0648: 100,
    importo_totale_0985: 50,
    importo_totale_0668: 0,
    importo_totale_euro: 150,
    display_name: "ROSSI MARIO",
    is_linked: true,
    digital_delivery: null,
    registered_mail: null,
    created_at: "2026-06-16T09:00:00Z",
    updated_at: "2026-06-16T09:00:00Z",
    ...overrides,
  };
}

describe("RuoloAvvisiSection", () => {
  beforeEach(() => {
    getAvvisiBySubject.mockReset();
  });

  test("renders notification evidence on the corresponding ruolo", async () => {
    getAvvisiBySubject.mockResolvedValue([
      buildAvviso({
        digital_delivery: {
          source_notice_id: "INCASS-1",
          pec_recipient: "rossi@example.pec.it",
          delivery_status: "Consegnata",
          delivered_at: "2025-12-17T10:00:00Z",
          accepted_at: null,
          receipt_documents_count: 1,
        },
        registered_mail: {
          source_shipment_id: "POSTA-1",
          service: "Raccomandata A/R",
          status_label: "Consegnata",
          sent_at: "2025-12-18T09:30:00Z",
          tracking_number: "619608197350",
        },
      }),
      buildAvviso({
        id: "avviso-2",
        codice_cnc: "CNC-002",
        anno_tributario: 2024,
        subject_id: null,
        codice_utenza: null,
        display_name: null,
        nominativo_raw: "BIANCHI LUCA",
        importo_totale_euro: null,
      }),
      buildAvviso({
        id: "avviso-3",
        codice_cnc: "CNC-003",
        anno_tributario: 2023,
        codice_utenza: null,
        display_name: null,
        nominativo_raw: null,
        importo_totale_euro: 0,
      }),
    ]);

    render(<RuoloAvvisiSection subjectId="subject-1" token="token" />);

    expect(await screen.findByText("Avvisi collegati al soggetto selezionato.")).toBeInTheDocument();
    expect(getAvvisiBySubject).toHaveBeenCalledWith("token", "subject-1");
    expect(screen.getByText(/Digitale\/PEC.*Consegnata.*rossi@example\.pec\.it/)).toBeInTheDocument();
    expect(screen.getByLabelText("Notifiche ruolo CNC-001")).toHaveTextContent(/Associata al ruolo\..*tracking 619608197350/);
    expect(screen.getAllByText("Nessuna PEC o raccomandata associata al ruolo.")).toHaveLength(2);
    expect(screen.getByText("BIANCHI LUCA")).toBeInTheDocument();
    expect(screen.getByText("Nominativo non disponibile")).toBeInTheDocument();
    expect(screen.getByText("Orfano")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Apri dettaglio" })[0]).toHaveAttribute("href", "/ruolo/avvisi/avviso-1");
  });

  test("renders singular summaries", async () => {
    getAvvisiBySubject.mockResolvedValue([buildAvviso()]);

    render(<RuoloAvvisiSection subjectId="subject-1" token="token" />);

    expect(await screen.findByText("1 avviso associato al soggetto corrente.")).toBeInTheDocument();
    expect(screen.getByText("1 avviso trovato sul soggetto.")).toBeInTheDocument();
  });

  test.each([
    { result: [], label: "empty response" },
    { result: new Error("Errore API"), label: "api error" },
    { result: new Error("403 Module access"), label: "forbidden module" },
    { result: new Error("Module access"), label: "module access" },
    { result: "Errore stringa", label: "string error" },
  ])("keeps the optional section hidden for $label", async ({ result }) => {
    if (result instanceof Error || typeof result === "string") {
      getAvvisiBySubject.mockRejectedValue(result);
    } else {
      getAvvisiBySubject.mockResolvedValue(result);
    }

    const { container } = render(<RuoloAvvisiSection subjectId="subject-1" token="token" />);

    await waitFor(() => expect(getAvvisiBySubject).toHaveBeenCalled());
    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });
});
