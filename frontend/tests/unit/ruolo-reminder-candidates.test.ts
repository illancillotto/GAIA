import { describe, expect, test } from "vitest";

import {
  reminderCandidateKey,
  reminderNeedsArchive,
  reminderSelectionCount,
} from "@/app/ruolo/tributi/reminder-candidates";
import type { RuoloTributiReminderCandidateResponse } from "@/types/ruolo";

function candidate(code: string): RuoloTributiReminderCandidateResponse {
  return {
    codice_fiscale: code,
    display_name: "Original recipient",
    comune: null,
    years: [2024],
    avvisi_count: 1,
    due_amount: 100,
    paid_amount: 0,
    saldo_amount: 100,
    subject_id: null,
    nas_folder_path: null,
    has_nas_folder: false,
    annuality_managers: [],
    avvisi: [{
      id: "original",
      codice_cnc: "123456789012345",
      anno_tributario: 2024,
      importo_totale_euro: 100,
      paid_amount: 0,
      saldo_amount: 100,
      payment_status: "unpaid",
      capacitas_url: null,
      annuality_manager_key: "gaia",
      annuality_manager_label: "GAIA",
      calculation_policy: "internal_gaia",
    }],
  };
}

describe("reminder recipient presentation", () => {
  test.each(["00048250955", "RSSMRA80A01H501U"])("keeps the valid recipient %s grouped", (code) => {
    const item = candidate(` ${code.toLowerCase()} `);
    expect(reminderCandidateKey(item)).toBe(code);
    expect(reminderNeedsArchive(item)).toBe(true);
    expect(reminderNeedsArchive({ ...item, has_nas_folder: true })).toBe(false);
  });

  test.each(["C", "S", "01234567890"])("keeps the invalid code %s tied to its avviso", (code) => {
    expect(reminderCandidateKey(candidate(code))).toBe("avviso:original");
    expect(reminderNeedsArchive(candidate(code))).toBe(false);
  });

  test("counts separate avvisi and manually added tax codes", () => {
    expect(reminderSelectionCount([candidate("C"), candidate("C")], ["C", "MANUAL"])).toBe(3);
    expect(reminderSelectionCount([], [])).toBe(0);
  });
});
