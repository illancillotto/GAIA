import type { EffectivePermission, EffectivePermissionPreview, PermissionEntryInput, PermissionUserInput, Review, SyncApplyResult, SyncCapabilities, SyncJob, SyncPreview, SyncPreviewRequest, SyncRun } from "@/types/api";
import { request } from "./core";

export async function getReviews(token: string): Promise<Review[]> {
  return request<Review[]>("/reviews", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getSyncCapabilities(token: string): Promise<SyncCapabilities> {
  return request<SyncCapabilities>("/sync/capabilities", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function previewSync(
  token: string,
  payload: SyncPreviewRequest,
): Promise<SyncPreview> {
  return request<SyncPreview>("/sync/preview", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function applySync(
  token: string,
  payload: SyncPreviewRequest,
): Promise<SyncApplyResult> {
  return request<SyncApplyResult>("/sync/apply", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function createSyncJob(
  token: string,
  profile: "quick" | "full" = "quick",
): Promise<SyncJob> {
  return request<SyncJob>("/sync/jobs", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ profile }),
  });
}

export async function getSyncRuns(token: string): Promise<SyncRun[]> {
  return request<SyncRun[]>("/sync-runs", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getSyncJobs(token: string): Promise<SyncJob[]> {
  return request<SyncJob[]>("/sync/jobs", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function retrySyncJob(token: string, jobId: number): Promise<SyncJob> {
  return request<SyncJob>(`/sync/jobs/${jobId}/retry`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function cancelSyncJob(token: string, jobId: number): Promise<SyncJob> {
  return request<SyncJob>(`/sync/jobs/${jobId}/cancel`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getEffectivePermissions(token: string): Promise<EffectivePermission[]> {
  return request<EffectivePermission[]>("/effective-permissions", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function calculatePermissionPreview(
  token: string,
  users: PermissionUserInput[],
  permissionEntries: PermissionEntryInput[],
): Promise<EffectivePermissionPreview[]> {
  return request<EffectivePermissionPreview[]>("/permissions/calculate-preview", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      users,
      permission_entries: permissionEntries,
    }),
  });
}
