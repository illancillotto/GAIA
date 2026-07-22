import { describe, expect, test } from "vitest";

import {
  buildCapacitasInCassHarvestPayload,
  buildCapacitasInCassSyncPayload,
} from "@/lib/api/capacitas-incass-payload";

describe("capacitas inCass payload builders", () => {
  test("builds sync payload with mailing flags and numeric fields", () => {
    expect(
      buildCapacitasInCassSyncPayload({
        credential_id: "3",
        limit: "25",
        include_details: true,
        include_partitario: false,
        include_mailing_list: true,
        download_mailing_receipts: true,
        continue_on_error: false,
        throttle_ms: "75",
      }),
    ).toEqual({
      credential_id: 3,
      limit: 25,
      include_details: true,
      include_partitario: false,
      include_mailing_list: true,
      download_mailing_receipts: true,
      continue_on_error: false,
      throttle_ms: 75,
    });
  });

  test("uses sync defaults for blank optional fields", () => {
    expect(
      buildCapacitasInCassSyncPayload({
        credential_id: "",
        limit: " ",
        include_details: false,
        include_partitario: false,
        include_mailing_list: false,
        download_mailing_receipts: false,
        continue_on_error: true,
        throttle_ms: "",
      }),
    ).toEqual({
      credential_id: undefined,
      limit: undefined,
      include_details: false,
      include_partitario: false,
      include_mailing_list: false,
      download_mailing_receipts: false,
      continue_on_error: true,
      throttle_ms: 250,
    });
  });

  test("ignores non-numeric sync fields", () => {
    expect(
      buildCapacitasInCassSyncPayload({
        credential_id: "not-a-number",
        limit: "bad",
        include_details: true,
        include_partitario: true,
        include_mailing_list: true,
        download_mailing_receipts: false,
        continue_on_error: true,
        throttle_ms: "bad",
      }),
    ).toMatchObject({
      credential_id: undefined,
      limit: undefined,
      throttle_ms: 250,
    });
  });

  test("builds harvest payload with batch and mailing options", () => {
    expect(
      buildCapacitasInCassHarvestPayload({
        credential_id: "9",
        anno: "2025",
        chunk_size: "50",
        limit_subjects: "1000",
        exclude_synced_subjects: true,
        include_details: true,
        include_partitario: true,
        include_mailing_list: true,
        download_mailing_receipts: false,
        continue_on_error: true,
        throttle_ms: "125",
      }),
    ).toEqual({
      credential_id: 9,
      anno: 2025,
      chunk_size: 50,
      limit_subjects: 1000,
      exclude_synced_subjects: true,
      include_details: true,
      include_partitario: true,
      include_mailing_list: true,
      download_mailing_receipts: false,
      continue_on_error: true,
      throttle_ms: 125,
    });
  });

  test("uses harvest defaults for blank optional fields", () => {
    expect(
      buildCapacitasInCassHarvestPayload({
        credential_id: "",
        anno: "",
        chunk_size: "",
        limit_subjects: "",
        exclude_synced_subjects: false,
        include_details: false,
        include_partitario: false,
        include_mailing_list: false,
        download_mailing_receipts: false,
        continue_on_error: false,
        throttle_ms: "",
      }),
    ).toEqual({
      credential_id: undefined,
      anno: undefined,
      chunk_size: 100,
      limit_subjects: undefined,
      exclude_synced_subjects: false,
      include_details: false,
      include_partitario: false,
      include_mailing_list: false,
      download_mailing_receipts: false,
      continue_on_error: false,
      throttle_ms: 250,
    });
  });
});
