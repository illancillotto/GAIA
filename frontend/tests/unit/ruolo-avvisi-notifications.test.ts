import { describe, expect, test } from "vitest";

import {
  buildRuoloAvvisoDigitalDeliveryLabel,
  buildRuoloAvvisoRegisteredMailLabel,
  formatRuoloAvvisoNotificationDate,
} from "@/lib/ruolo-avvisi-notifications";
import type { RuoloAvvisoListItemResponse } from "@/types/ruolo";

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

describe("ruolo avvisi notification labels", () => {
  test("formats empty, invalid and valid notification dates", () => {
    expect(formatRuoloAvvisoNotificationDate(null)).toBeNull();
    expect(formatRuoloAvvisoNotificationDate(undefined)).toBeNull();
    expect(formatRuoloAvvisoNotificationDate("17/12/2025 20:01:58")).toBe("17/12/2025 20:01:58");
    expect(formatRuoloAvvisoNotificationDate("2025-12-18T09:30:00")).toContain("18/12/25");
  });

  test("builds digital and registered mail labels only when payloads exist", () => {
    expect(buildRuoloAvvisoDigitalDeliveryLabel(buildAvviso())).toBeNull();
    expect(buildRuoloAvvisoRegisteredMailLabel(buildAvviso())).toBeNull();
    expect(
      buildRuoloAvvisoDigitalDeliveryLabel(
        buildAvviso({
          digital_delivery: {
            source_notice_id: null,
            pec_recipient: null,
            delivery_status: null,
            delivered_at: null,
            accepted_at: null,
            receipt_documents_count: 0,
          },
        }),
      ),
    ).toBe("Digitale/PEC");
    expect(
      buildRuoloAvvisoRegisteredMailLabel(
        buildAvviso({
          registered_mail: {
            source_shipment_id: null,
            service: null,
            status_label: null,
            sent_at: null,
            tracking_number: null,
          },
        }),
      ),
    ).toBe("Raccomandata");

    expect(
      buildRuoloAvvisoDigitalDeliveryLabel(
        buildAvviso({
          digital_delivery: {
            source_notice_id: "INCASS-1",
            pec_recipient: "rossi.mario@pec.example.it",
            delivery_status: "Consegnata",
            delivered_at: "17/12/2025 20:01:58",
            accepted_at: "17/12/2025 20:01:57",
            receipt_documents_count: 2,
          },
        }),
      ),
    ).toBe(
      "Digitale/PEC · Consegnata · accettata 17/12/2025 20:01:57 · consegnata 17/12/2025 20:01:58 · rossi.mario@pec.example.it",
    );

    const registeredLabel = buildRuoloAvvisoRegisteredMailLabel(
      buildAvviso({
        registered_mail: {
          source_shipment_id: "POSTA-1",
          service: "Raccomandata A/R",
          status_label: "Accettata da Poste",
          sent_at: "2025-12-18T09:30:00",
          tracking_number: "619608197350",
        },
      }),
    );

    expect(registeredLabel).toContain("Raccomandata");
    expect(registeredLabel).toContain("inviata 18/12/25");
    expect(registeredLabel).toContain("Accettata da Poste");
    expect(registeredLabel).toContain("tracking 619608197350");
  });
});
