import type { RegisterDetail, RegisterPosition } from "@/types/notice-register";

export function noticeFixture(overrides: Partial<RegisterDetail> = {}): RegisterDetail {
  return {
    id: "doc-1", document_number: "CUM-2022-2023", tax_code: "TESTCF",
    source_system: "manual", source_key: "source-1", issued_on: "2024-06-01",
    created_at: "2026-09-17T10:00:00Z", version: 1, notification_state: "da_verificare",
    reconciled_into_id: null,
    position_count: 0, unlinked_count: 0, conflicting_count: 0, recovery_review_count: 0,
    anomalies: ["posizioni_assenti", "notifica_da_verificare"], original_json: { source: "archivio" },
    notification: { state: "da_verificare", notified_on: null, evidence_id: null }, positions: [],
    ...overrides,
  };
}

export function positionFixture(overrides: Partial<RegisterPosition> = {}): RegisterPosition {
  return {
    id: "pos-1", source_namespace: "incass", source_reference: "020220001834880", tax_year: 2022,
    avviso_id: null, avviso: null,
    recovery: { state: "da_verificare", case_reference: null, verified_on: null, evidence_reference: null, amount: null },
    ...overrides,
  };
}

export const candidateFixture = {
  id: "avviso-1", codice_cnc: "CNC-2022-001", anno_tributario: 2022, codice_fiscale_raw: "TESTCF",
  nominativo_raw: "Contribuente Test", subject_id: null, importo_totale_euro: "123.45", already_linked: false,
};
export const evidenceFixture = {
  id: "evidence-1", source_system: "manual", source_key: "evidence-source", attempt_id: null,
  kind: "Ricevuta", occurred_on: "2024-06-29", reference: "Fascicolo 42", original_json: { raw_date: "29/06/204" },
};
export function jsonResponse(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });
}
