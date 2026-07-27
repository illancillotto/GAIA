import { request } from "@/lib/api";
import type { PasswordResetConfirmResult, PasswordResetInfo, PasswordResetRequestResult } from "@/types/api";

export async function requestPasswordReset(identifier: string): Promise<PasswordResetRequestResult> {
  return request<PasswordResetRequestResult>("/auth/password-reset/request", {
    method: "POST",
    body: JSON.stringify({ identifier }),
  });
}

export async function getPasswordResetInfo(token: string): Promise<PasswordResetInfo> {
  return request<PasswordResetInfo>(`/auth/password-reset/${token}`);
}

export async function confirmPasswordReset(token: string, password: string): Promise<PasswordResetConfirmResult> {
  return request<PasswordResetConfirmResult>(`/auth/password-reset/${token}/confirm`, {
    method: "POST",
    body: JSON.stringify({ password }),
  });
}
