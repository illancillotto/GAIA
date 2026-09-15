import type {
  PresenzeWhatsAppDashboardSummary,
  PresenzeWhatsAppConfig,
  PresenzeWhatsAppConfigUpdate,
  PresenzeWhatsAppMessageList,
  PresenzeWhatsAppOptOut,
  PresenzeWhatsAppPreview,
} from "@/types/api";

import { request } from "./core";

const BASE = "/presenze/whatsapp";
const auth = (token: string) => ({ Authorization: `Bearer ${token}` });

export function getPresenzeWhatsAppDashboard(token: string): Promise<PresenzeWhatsAppDashboardSummary> {
  return request(`${BASE}/dashboard`, { headers: auth(token) });
}

export function getPresenzeWhatsAppConfiguration(token: string): Promise<PresenzeWhatsAppConfig> {
  return request(`${BASE}/configuration`, { headers: auth(token) });
}

export function updatePresenzeWhatsAppConfiguration(
  token: string,
  payload: PresenzeWhatsAppConfigUpdate,
): Promise<PresenzeWhatsAppConfig> {
  return request(`${BASE}/configuration`, {
    method: "PUT",
    headers: auth(token),
    body: JSON.stringify(payload),
  });
}
export function listPresenzeWhatsAppMessages(
  token: string,
  params: { status?: string; q?: string; page?: number; pageSize?: number } = {},
): Promise<PresenzeWhatsAppMessageList> {
  const query = new URLSearchParams();
  if (params.status) query.set("status", params.status);
  if (params.q) query.set("q", params.q);
  if (params.page) query.set("page", String(params.page));
  if (params.pageSize) query.set("page_size", String(params.pageSize));
  const suffix = query.size ? `?${query}` : "";
  return request(`${BASE}/messages${suffix}`, { headers: auth(token) });
}

export function getPresenzeWhatsAppPreview(token: string): Promise<PresenzeWhatsAppPreview> {
  return request(`${BASE}/preview`, { headers: auth(token) });
}

export function listPresenzeWhatsAppOptOuts(token: string): Promise<PresenzeWhatsAppOptOut[]> {
  return request(`${BASE}/opt-outs`, { headers: auth(token) });
}

export function restorePresenzeWhatsAppUser(token: string, userId: number): Promise<void> {
  return request(`${BASE}/opt-outs/${userId}`, { method: "DELETE", headers: auth(token) });
}

export function updatePresenzeWhatsAppPhone(token: string, userId: number, phone: string): Promise<{ application_user_id: number; phone: string | null }> {
  return request(`${BASE}/users/${userId}/phone`, {
    method: "PATCH",
    headers: auth(token),
    body: JSON.stringify({ phone }),
  });
}

export function reconcilePresenzeWhatsAppMessage(
  token: string,
  messageId: string,
  payload: { sent: boolean; evidence: string; provider_message_id?: string | null },
): Promise<void> {
  return request(`${BASE}/messages/${messageId}/reconcile`, {
    method: "POST",
    headers: auth(token),
    body: JSON.stringify(payload),
  });
}
