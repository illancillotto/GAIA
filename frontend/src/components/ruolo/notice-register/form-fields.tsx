import { Field, inputClass, NOTIFICATIONS, RECOVERIES } from "./presentation";
import { EvidencePicker } from "./evidence-picker";

export type FormKind = "document" | "position" | "evidence" | "notification" | "recovery";
type InputField = { name: string; label: string; type?: string; required?: boolean; maxLength?: number; min?: number; max?: number; step?: string; options?: Record<string, string> };

const FIELDS: Record<FormKind, InputField[]> = {
  document: [
    { name: "document_number", label: "Numero documento", required: true, maxLength: 100 },
    { name: "tax_code", label: "Codice fiscale destinatario", maxLength: 20 },
    { name: "issued_on", label: "Data emissione", type: "date" },
  ],
  position: [
    { name: "source_namespace", label: "Sistema di origine del riferimento", required: true, maxLength: 40 },
    { name: "source_reference", label: "Riferimento annuale originale", required: true, maxLength: 100 },
    { name: "tax_year", label: "Annualita", type: "number", required: true, min: 1900, max: 9999 },
  ],
  evidence: [
    { name: "kind", label: "Tipo evidenza", required: true, maxLength: 60 },
    { name: "reference", label: "Riferimento ricevuta o documento", required: true },
    { name: "occurred_on", label: "Data evento", type: "date" },
  ],
  notification: [
    { name: "state", label: "Valutazione notifica", options: NOTIFICATIONS },
    { name: "notified_on", label: "Data perfezionamento", type: "date" },
    { name: "evidence_id", label: "Evidenza del documento" },
  ],
  recovery: [
    { name: "state", label: "Valutazione STEP", options: RECOVERIES },
    { name: "case_reference", label: "Pratica STEP", maxLength: 200 },
    { name: "verified_on", label: "Data verifica STEP", type: "date" },
    { name: "evidence_reference", label: "Riferimento verifica STEP" },
    { name: "amount", label: "Importo affidato (non modifica il debito)", type: "number", min: 0, step: "0.01" },
  ],
};
export const FORM_HELP: Record<FormKind, string> = {
  document: "Registra o correggi lo storico, senza creare debiti. Le correzioni rimettono la notifica in verifica.",
  position: "Mantieni gli zeri iniziali. Correggere un riferimento rimuove il collegamento precedente e rimette notifica e STEP in verifica.",
  evidence: "Registra un riferimento verificabile. Una nuova evidenza non perfeziona automaticamente la notifica.",
  notification: "Per Perfezionata sono obbligatorie data ed evidenza di questo documento. Nessuna evidenza non equivale ad autorizzazione all'invio.",
  recovery: "La notifica non implica STEP. Una verifica richiede data e documento; affidato, revocato e chiuso richiedono anche la pratica.",
};

export function FormFields({ kind, initial, token, path }: { kind: FormKind; initial: Record<string, unknown>; token: string; path: string }) {
  return <>{FIELDS[kind].map(({ name, label, options, ...attributes }) => <Field key={name} label={label}>
    {name === "evidence_id" ? <EvidencePicker token={token} documentPath={path.replace(/\/notifica$/, "")} initial={String(initial[name] ?? "")} /> : options ? <select className={inputClass} name={name} defaultValue={String(initial[name] ?? "da_verificare")}>
      {Object.entries(options).map(([value, text]) => <option key={value} value={value}>{text}</option>)}
    </select> : <input className={inputClass} name={name} defaultValue={String(initial[name] ?? "")} {...attributes} />}
  </Field>)}</>;
}

export function formPayload(kind: FormKind, form: FormData): Record<string, unknown> {
  const data: Record<string, unknown> = {};
  for (const field of FIELDS[kind]) {
    const value = String(form.get(field.name)).trim();
    data[field.name] = value === "" ? null : value;
  }
  if (kind === "position") data.tax_year = Number(data.tax_year);
  if (kind === "notification" && data.state !== "perfezionata") data.notified_on = null;
  return data;
}
