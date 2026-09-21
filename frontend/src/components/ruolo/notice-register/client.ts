import { ApiError, request } from "@/lib/api/core";
import type { RegisterMutationResult } from "@/types/notice-register";

const BASE = "/ruolo/tributi/registro-avvisi";

export function registerGet<T>(token: string, path: string, signal: AbortSignal): Promise<T> {
  return request<T>(`${BASE}${path}`, { headers: { Authorization: `Bearer ${token}` }, signal });
}

export type RegisterCommand = {
  path: string; method: "POST" | "PUT"; version: number;
  data: Record<string, unknown>; reason: string;
};

export function registerWrite(token: string, command: RegisterCommand): Promise<RegisterMutationResult> {
  return request(`${BASE}${command.path}`, {
    method: command.method, headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ expected_version: command.version, data: command.data, reason: command.reason }),
  });
}

export function registerError(error: unknown): string {
  if (error instanceof ApiError && error.status === 409) {
    return "Conflitto: il registro e cambiato o il riferimento e duplicato. Ricarica e verifica prima di riprovare.";
  }
  return error instanceof Error ? error.message : "Operazione non riuscita. Riprova.";
}

export function queryString(values: Record<string, string>): string {
  return new URLSearchParams(Object.entries(values).filter(([, value]) => value.trim() !== "")).toString();
}
