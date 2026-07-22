import type {
  CapacitasInCassRuoloHarvestInput,
  CapacitasInCassSyncJobCreateInput,
} from "@/types/api";

export type CapacitasInCassSyncFormState = {
  credential_id: string;
  limit: string;
  include_details: boolean;
  include_partitario: boolean;
  include_mailing_list: boolean;
  download_mailing_receipts: boolean;
  continue_on_error: boolean;
  throttle_ms: string;
};

export type CapacitasInCassHarvestFormState = {
  credential_id: string;
  anno: string;
  chunk_size: string;
  limit_subjects: string;
  exclude_synced_subjects: boolean;
  include_details: boolean;
  include_partitario: boolean;
  include_mailing_list: boolean;
  download_mailing_receipts: boolean;
  continue_on_error: boolean;
  throttle_ms: string;
};

export function buildCapacitasInCassSyncPayload(
  form: CapacitasInCassSyncFormState,
): CapacitasInCassSyncJobCreateInput {
  return {
    credential_id: parseOptionalInteger(form.credential_id),
    limit: parseOptionalInteger(form.limit),
    include_details: form.include_details,
    include_partitario: form.include_partitario,
    include_mailing_list: form.include_mailing_list,
    download_mailing_receipts: form.download_mailing_receipts,
    continue_on_error: form.continue_on_error,
    throttle_ms: parseOptionalInteger(form.throttle_ms) ?? 250,
  };
}

export function buildCapacitasInCassHarvestPayload(
  form: CapacitasInCassHarvestFormState,
): CapacitasInCassRuoloHarvestInput {
  return {
    credential_id: parseOptionalInteger(form.credential_id),
    anno: parseOptionalInteger(form.anno),
    chunk_size: parseOptionalInteger(form.chunk_size) ?? 100,
    limit_subjects: parseOptionalInteger(form.limit_subjects),
    exclude_synced_subjects: form.exclude_synced_subjects,
    include_details: form.include_details,
    include_partitario: form.include_partitario,
    include_mailing_list: form.include_mailing_list,
    download_mailing_receipts: form.download_mailing_receipts,
    continue_on_error: form.continue_on_error,
    throttle_ms: parseOptionalInteger(form.throttle_ms) ?? 250,
  };
}

function parseOptionalInteger(value: string): number | undefined {
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  const parsed = Number.parseInt(trimmed, 10);
  return Number.isFinite(parsed) ? parsed : undefined;
}
