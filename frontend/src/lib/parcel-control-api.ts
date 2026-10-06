import { getApiBaseUrl } from "@/lib/api";

export async function parcelControlRequest<Result>(token: string, path: string, data?: unknown): Promise<Result> {
  const response = await fetch(`${getApiBaseUrl()}/ruolo/particelle/controllo${path}`, {
    method: data === undefined ? "GET" : "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    ...(data === undefined ? {} : { body: JSON.stringify(data) }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Errore di comunicazione" }));
    throw new Error(typeof payload.detail === "string" ? payload.detail : "Richiesta non valida");
  }
  return response.json() as Promise<Result>;
}

export function controlCommand(reason: string, data: Record<string, unknown>, version = 1) {
  return { command_id: crypto.randomUUID(), reason, data, expected_version: version };
}
