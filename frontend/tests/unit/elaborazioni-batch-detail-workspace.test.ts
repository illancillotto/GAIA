import { describe, expect, it } from "vitest";

import { isReleasedBatchDetail } from "@/components/elaborazioni/batch-detail-workspace";
import type { ElaborazioneBatchDetail } from "@/types/api";

function buildBatch(overrides: Partial<ElaborazioneBatchDetail> = {}): ElaborazioneBatchDetail {
  return {
    id: "batch-1",
    user_id: 1,
    name: "Batch",
    source_filename: null,
    status: "cancelled",
    total_items: 1,
    completed_items: 0,
    failed_items: 0,
    skipped_items: 1,
    not_found_items: 0,
    current_operation: "Release requested by user",
    created_at: "2026-05-21T10:00:00Z",
    started_at: "2026-05-21T10:01:00Z",
    completed_at: "2026-05-21T10:02:00Z",
    report_json_path: null,
    report_md_path: null,
    requests: [
      {
        id: "req-1",
        batch_id: "batch-1",
        user_id: 1,
        row_index: 1,
        search_mode: "immobile",
        comune: "Oristano",
        comune_codice: "G113#ORISTANO#5#5",
        catasto: "Terreni e Fabbricati",
        sezione: null,
        foglio: "1",
        particella: "101",
        subalterno: null,
        tipo_visura: "Completa",
        subject_kind: null,
        subject_id: null,
        request_type: null,
        intestazione: null,
        status: "skipped",
        current_operation: "Release requested by user",
        error_message: "Credenziale SISTER liberata su richiesta utente",
        attempts: 1,
        captcha_image_path: null,
        artifact_dir: null,
        document_id: null,
        created_at: "2026-05-21T10:00:00Z",
        processed_at: "2026-05-21T10:02:00Z",
        captcha_requested_at: null,
        captcha_expires_at: null,
        captcha_manual_solution: null,
        captcha_skip_requested: false,
      },
    ],
    ...overrides,
  };
}

describe("isReleasedBatchDetail", () => {
  it("returns true for batches cancelled by release request", () => {
    expect(isReleasedBatchDetail(buildBatch())).toBe(true);
  });

  it("returns false for manually cancelled batches", () => {
    expect(
      isReleasedBatchDetail(
        buildBatch({
          current_operation: "Cancelled by user",
          requests: [
            {
              ...buildBatch().requests[0],
              current_operation: "Cancelled",
              error_message: "Batch cancelled by user",
            },
          ],
        }),
      ),
    ).toBe(false);
  });
});
