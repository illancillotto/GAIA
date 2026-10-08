import {
  ApiError,
  createBonificaOristaneseCredential,
  createCapacitasCredential,
  updateBonificaOristaneseCredential,
  updateCapacitasCredential,
} from "@/lib/api";
import { buildCapacitasDiagnosis } from "@/lib/elaborazioni-credential-diagnostics";
import type {
  BonificaOristaneseCredential,
  CapacitasCredential,
  CapacitasCredentialTestResult,
} from "@/types/api";

type ProviderForm = { id: number | null; password: string };
type BonificaForm = ProviderForm & Pick<BonificaOristaneseCredential, "label" | "login_identifier" | "remember_me" | "active">;
type CapacitasForm = ProviderForm & Pick<CapacitasCredential, "label" | "username" | "active" | "allowed_hours_start" | "allowed_hours_end">;

function replacementPassword(password: string): string | undefined {
  return password.trim().length > 0 ? password : undefined;
}

export function saveBonificaCredentialForm(token: string, form: BonificaForm): Promise<BonificaOristaneseCredential> {
  const payload = {
    label: form.label.trim(),
    login_identifier: form.login_identifier.trim(),
    password: form.password,
    remember_me: form.remember_me,
    active: form.active,
  };
  if (form.id == null) {
    return createBonificaOristaneseCredential(token, payload);
  }
  return updateBonificaOristaneseCredential(token, form.id, { ...payload, password: replacementPassword(form.password) });
}

export function saveCapacitasCredentialForm(token: string, form: CapacitasForm): Promise<CapacitasCredential> {
  const payload = {
    label: form.label.trim(),
    username: form.username.trim(),
    password: form.password,
    active: form.active,
    allowed_hours_start: form.allowed_hours_start,
    allowed_hours_end: form.allowed_hours_end,
  };
  if (form.id == null) {
    return createCapacitasCredential(token, payload);
  }
  return updateCapacitasCredential(token, form.id, { ...payload, password: replacementPassword(form.password) });
}

export function providerSaveMessage(provider: "Bonifica" | "Capacitas", isEditing: boolean): string {
  return `Credenziale ${provider} ${isEditing ? "aggiornata" : "creata"}.`;
}

export function providerCommandError(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

export function capacitasProbeFailure(error: unknown): {
  message: string;
  statusCode: number | null;
  backendDetail: string;
} {
  const message = providerCommandError(error, "Errore test credenziale Capacitas");
  if (!(error instanceof ApiError)) {
    return { message, statusCode: null, backendDetail: message };
  }
  const statusCode = error.status ?? null;
  let backendDetail = message;
  if (typeof error.detailData === "string") {
    backendDetail = error.detailData;
  } else if (error.detailData != null) {
    backendDetail = JSON.stringify(error.detailData, null, 2);
  }
  return { message, statusCode, backendDetail };
}

export function capacitasProbeCompletion(result: CapacitasCredentialTestResult, success: boolean) {
  if (success) {
    return {
      phase: "success" as const,
      title: "Test Capacitas completato",
      summary: "Autenticazione completata con successo e sessione rilevata dal backend.",
      backendDetail: result.error ?? "Login completato senza errori.",
      diagnosis: "Il backend ha ottenuto una sessione valida. Puoi usare questa credenziale per ricerca e diagnostica inVOLTURE.",
    };
  }
  return {
    phase: "error" as const,
    title: "Test Capacitas fallito",
    summary: "Il backend ha risposto, ma il test non ha restituito una sessione valida.",
    backendDetail: result.error ?? null,
    diagnosis: buildCapacitasDiagnosis(result.error ?? null, 200),
  };
}
