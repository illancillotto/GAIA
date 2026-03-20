import type {
  CurrentUser,
  DashboardSummary,
  EffectivePermission,
  LoginResponse,
  Review,
  Share,
  SyncCapabilities,
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

export async function getEffectivePermissions(token: string): Promise<EffectivePermission[]> {
  return request<EffectivePermission[]>("/effective-permissions", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}
