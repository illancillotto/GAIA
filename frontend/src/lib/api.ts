import type {
  CurrentUser,
  DashboardSummary,
  EffectivePermission,
  EffectivePermissionPreview,
  LoginResponse,
  NasGroup,
  NasUser,
  PermissionEntryInput,
  PermissionUserInput,
  Review,
  Share,
  SyncApplyResult,
  SyncCapabilities,
  SyncLiveApplyResult,
  SyncPreview,
  SyncPreviewRequest,
  SyncRun,
} from "@/types/api";

const DEFAULT_API_BASE_URL = "http://localhost:8080/api";

function getApiBaseUrl(): string {
  const value = process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL;
  return value.replace(/\/+$/, "");
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    let detail = "Request failed";

    try {
      const payload = (await response.json()) as { detail?: string };
      detail = payload.detail ?? detail;
    } catch {
      detail = response.statusText || detail;
    }

    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function getCurrentUser(token: string): Promise<CurrentUser> {
  return request<CurrentUser>("/auth/me", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getDashboardSummary(token: string): Promise<DashboardSummary> {
  return request<DashboardSummary>("/dashboard/summary", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getShares(token: string): Promise<Share[]> {
  return request<Share[]>("/shares", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNasUsers(token: string): Promise<NasUser[]> {
  return request<NasUser[]>("/nas-users", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNasGroups(token: string): Promise<NasGroup[]> {
  return request<NasGroup[]>("/nas-groups", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

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

export async function applyLiveSync(token: string): Promise<SyncLiveApplyResult> {
  return request<SyncLiveApplyResult>("/sync/live-apply", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getSyncRuns(token: string): Promise<SyncRun[]> {
  return request<SyncRun[]>("/sync-runs", {
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
