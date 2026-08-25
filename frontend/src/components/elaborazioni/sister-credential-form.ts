"use client";

import { useState } from "react";

import { defaultSisterSchedule } from "@/components/elaborazioni/sister-availability-schedule";
import type { ElaborazioneCredential } from "@/types/api";


const DEFAULT_UFFICIO = "ORISTANO Territorio";

export type SisterCredentialFormState = {
  id: string | null;
  label: string;
  sister_username: string;
  sister_password: string;
  convenzione: string;
  codice_richiesta: string;
  ufficio_provinciale: string;
  active: boolean;
  is_default: boolean;
  schedule_enabled: boolean;
  availability_schedule: NonNullable<ElaborazioneCredential["availability_schedule"]>;
};

export function defaultSisterCredentialForm(): SisterCredentialFormState {
  return {
    id: null,
    label: "",
    sister_username: "",
    sister_password: "",
    convenzione: "",
    codice_richiesta: "",
    ufficio_provinciale: DEFAULT_UFFICIO,
    active: true,
    is_default: false,
    schedule_enabled: false,
    availability_schedule: defaultSisterSchedule(),
  };
}

export function useSisterCredentialForm() {
  const [formState, setFormState] = useState(defaultSisterCredentialForm);
  const resetForm = () => setFormState(defaultSisterCredentialForm());
  const applyCredential = (credential: ElaborazioneCredential) => {
    setFormState(sisterCredentialFormFromCredential(credential));
  };
  return { formState, setFormState, resetForm, applyCredential };
}

export function sisterCredentialFormFromCredential(credential: ElaborazioneCredential): SisterCredentialFormState {
  return {
    id: credential.id,
    label: credential.label,
    sister_username: credential.sister_username,
    sister_password: "",
    convenzione: credential.convenzione ?? "",
    codice_richiesta: credential.codice_richiesta ?? "",
    ufficio_provinciale: credential.ufficio_provinciale,
    active: credential.active,
    is_default: credential.is_default,
    schedule_enabled: credential.schedule_enabled ?? false,
    availability_schedule: credential.availability_schedule ?? defaultSisterSchedule(),
  };
}

export function sisterCredentialUpdatePayload(form: SisterCredentialFormState) {
  return {
    label: form.label,
    sister_username: form.sister_username,
    sister_password: form.sister_password.trim().length > 0 ? form.sister_password : undefined,
    convenzione: form.convenzione || null,
    codice_richiesta: form.codice_richiesta || null,
    ufficio_provinciale: form.ufficio_provinciale,
    active: form.active,
    is_default: form.is_default,
    schedule_enabled: form.schedule_enabled,
    availability_schedule: form.availability_schedule,
  };
}

export function sisterCredentialCreatePayload(form: SisterCredentialFormState) {
  return {
    label: form.label,
    sister_username: form.sister_username,
    sister_password: form.sister_password,
    convenzione: form.convenzione || undefined,
    codice_richiesta: form.codice_richiesta || undefined,
    ufficio_provinciale: form.ufficio_provinciale,
    active: form.active,
    is_default: form.is_default,
    schedule_enabled: form.schedule_enabled,
    availability_schedule: form.availability_schedule,
  };
}
