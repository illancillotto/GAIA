import { describe, expect, test } from "vitest";

import { normalizeIdentity, parseOperatorRows, workbookEvidence } from "@/components/ruolo/registered-mail-workbook";
import type { RegisteredMailCampaignItem } from "@/types/registered-mail-campaign";

const pair: RegisteredMailCampaignItem = {
  mail_id: "mail-1", source_shipment_id: "shipment-1", recipient_name: "ROSSI MARIO", recipient_address: "VIA ROMA 1",
  tracking_number: null, legacy_avviso_id: null, classification: "proposed_pair", reasons: [], requires_operator_confirmation: true,
  register_document_id: null, register_avviso_ids: [],
  candidate_notices: [
    { avviso_id: "a22", subject_id: "subject", tax_year: 2022, codice_cnc: "cnc22", codice_fiscale: "RSSMRA80A01H501Z", nominativo: "ROSSI MARIO" },
    { avviso_id: "a23", subject_id: "subject", tax_year: 2023, codice_cnc: "cnc23", codice_fiscale: "RSSMRA80A01H501Z", nominativo: "ROSSI MARIO" },
  ],
};

function cells(): unknown[][] {
  const row = Array(57).fill("");
  row[2] = "02022"; row[3] = "02023"; row[13] = "Rossi Mario"; row[14] = "Via Roma 1";
  row[16] = "Uras"; row[20] = "RSSMRA80A01H501Z"; row[21] = "120242223"; row[56] = "2023";
  return [Array(57).fill(""), row];
}

describe("registered mail workbook", () => {
  test("keeps annual references and row provenance while excluding non-operative rows", () => {
    const input = cells();
    input.push(Array(57).fill(""));
    expect(parseOperatorRows(input)).toEqual([{ row: 2, ref2022: "02022", ref2023: "02023", name: "Rossi Mario", address: "Via Roma 1", city: "Uras", taxCode: "RSSMRA80A01H501Z", cumulativeNumber: "120242223" }]);
    expect(normalizeIdentity("R\u00F3ssi Mario / 1")).toBe("ROSSIMARIO1");
    expect(normalizeIdentity(null)).toBe("");
  });

  test("requires a unique row for a same-tax-code cross-year pair", () => {
    const rows = parseOperatorRows(cells());
    expect(workbookEvidence(pair, rows)).toEqual(rows[0]);
    expect(workbookEvidence(pair, [{ ...rows[0], ref2022: "---" }])).toBeNull();
    expect(workbookEvidence(pair, [{ ...rows[0], ref2023: "" }])).toBeNull();
    expect(workbookEvidence(pair, [...rows, rows[0]])).toBeNull();
    expect(workbookEvidence({ ...pair, candidate_notices: [pair.candidate_notices[0]] }, rows)).toBeNull();
    expect(workbookEvidence({ ...pair, candidate_notices: pair.candidate_notices.map((item) => ({ ...item, tax_year: 2022 })) }, rows)).toBeNull();
    expect(workbookEvidence({ ...pair, candidate_notices: [{ ...pair.candidate_notices[0], codice_fiscale: null }, pair.candidate_notices[1]] }, rows)).toBeNull();
    expect(workbookEvidence({ ...pair, candidate_notices: pair.candidate_notices.map((item) => ({ ...item, codice_fiscale: null })) }, rows)).toBeNull();
    expect(workbookEvidence(pair, [{ ...rows[0], ref2023: "" }])).toBeNull();
  });
});
