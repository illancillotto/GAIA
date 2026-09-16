"use client";

import { useEffect, useState } from "react";

import type { PresenzeWhatsAppConfig, PresenzeWhatsAppConfigUpdate } from "@/types/api";

type Props = {
  configuration: PresenzeWhatsAppConfig | null;
  busy: boolean;
  onSave: (payload: PresenzeWhatsAppConfigUpdate) => Promise<void>;
};

type UpdateForm = <K extends keyof PresenzeWhatsAppConfig>(
  key: K,
  value: PresenzeWhatsAppConfig[K],
) => void;

const numberValue = (value: string): number => Number.parseInt(value, 10);

const CHANNEL_OPTIONS = [
  {
    value: "",
    title: "Disattivato",
    description: "Non prepara e non invia messaggi.",
  },
  {
    value: "dry_run",
    title: "Modalita di prova",
    description: "Prepara i messaggi e li registra, ma non li invia.",
    badge: "Consigliato per iniziare",
  },
  {
    value: "waha",
    title: "Invio attivo",
    description: "Invia davvero i promemoria tramite WhatsApp.",
  },
] as const;

export function WhatsAppConfiguration({ configuration, busy, onSave }: Props) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<PresenzeWhatsAppConfig | null>(configuration);
  const [apiKey, setApiKey] = useState("");
  const [hmacKey, setHmacKey] = useState("");
  const [clearApiKey, setClearApiKey] = useState(false);
  const [clearHmacKey, setClearHmacKey] = useState(false);

  useEffect(() => setForm(configuration), [configuration]);
  if (!configuration || !form) return null;

  function update<K extends keyof PresenzeWhatsAppConfig>(
    key: K,
    value: PresenzeWhatsAppConfig[K],
  ) {
    setForm((current) => ({ ...current!, [key]: value }));
  }

  async function submit(event: React.FormEvent, currentForm: PresenzeWhatsAppConfig) {
    event.preventDefault();
    try {
      await onSave({
        ...configurableValues(currentForm),
        waha_api_key: apiKey || null,
        waha_hmac_key: hmacKey || null,
        clear_api_key: clearApiKey,
        clear_hmac_key: clearHmacKey,
      });
    } catch {
      return;
    }
    setApiKey("");
    setHmacKey("");
    setClearApiKey(false);
    setClearHmacKey(false);
    setOpen(false);
  }

  return (
    <section className="rounded-[28px] border border-emerald-900/15 bg-white p-5 shadow-sm sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-emerald-700">
            Solo super admin
          </p>
          <h2 className="mt-1 text-xl font-semibold">Configurazione canale</h2>
          <p className="mt-1 text-sm text-slate-500">
            Modalita, collegamento WAHA, pianificazione e protezioni di invio.
          </p>
        </div>
        <button className="btn-secondary" type="button" onClick={() => setOpen(true)}>
          Configura WhatsApp
        </button>
      </div>
      {open ? (
        <ConfigurationDialog
          configuration={configuration}
          form={form}
          busy={busy}
          apiKey={apiKey}
          hmacKey={hmacKey}
          clearApiKey={clearApiKey}
          clearHmacKey={clearHmacKey}
          update={update}
          setApiKey={setApiKey}
          setHmacKey={setHmacKey}
          setClearApiKey={setClearApiKey}
          setClearHmacKey={setClearHmacKey}
          onClose={() => setOpen(false)}
          onSubmit={(event) => void submit(event, form)}
        />
      ) : null}
    </section>
  );
}

function configurableValues(form: PresenzeWhatsAppConfig) {
  return {
    provider: form.provider,
    waha_url: form.waha_url,
    waha_session: form.waha_session,
    reminder_cron: form.reminder_cron,
    lookback_days: form.lookback_days,
    include_missing_punches: form.include_missing_punches,
    max_per_run: form.max_per_run,
    min_delay_seconds: form.min_delay_seconds,
    max_delay_seconds: form.max_delay_seconds,
    send_start_hour: form.send_start_hour,
    send_end_hour: form.send_end_hour,
  };
}

type DialogProps = {
  configuration: PresenzeWhatsAppConfig;
  form: PresenzeWhatsAppConfig;
  busy: boolean;
  apiKey: string;
  hmacKey: string;
  clearApiKey: boolean;
  clearHmacKey: boolean;
  update: UpdateForm;
  setApiKey: (value: string) => void;
  setHmacKey: (value: string) => void;
  setClearApiKey: (value: boolean) => void;
  setClearHmacKey: (value: boolean) => void;
  onClose: () => void;
  onSubmit: (event: React.FormEvent) => void;
};

function ConfigurationDialog(props: DialogProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/55 p-2 sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="whatsapp-config-title"
    >
      <form
        className="flex max-h-[calc(100vh-16px)] w-[calc(100vw-16px)] max-w-6xl flex-col overflow-hidden rounded-[30px] bg-[#f7faf7] shadow-2xl sm:max-h-[calc(100vh-32px)]"
        onSubmit={props.onSubmit}
      >
        <DialogHeader onClose={props.onClose} />
        <div className="flex-1 space-y-5 overflow-y-auto p-5 sm:p-7">
          <ModeSection form={props.form} update={props.update} />
          <ScheduleSection form={props.form} update={props.update} />
          <AdvancedSection {...props} />
        </div>
        <DialogFooter busy={props.busy} />
      </form>
    </div>
  );
}

function DialogHeader({ onClose }: { onClose: () => void }) {
  return (
    <header className="flex items-start justify-between border-b border-slate-200 bg-white px-5 py-4 sm:px-8">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-emerald-700">
          Solo super admin
        </p>
        <h2 id="whatsapp-config-title" className="mt-1 text-2xl font-semibold">
          Configura i promemoria WhatsApp
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Scegli prima se fare una prova o attivare gli invii reali.
        </p>
      </div>
      <button className="btn-secondary" type="button" onClick={onClose}>
        Chiudi
      </button>
    </header>
  );
}

function ModeSection({ form, update }: { form: PresenzeWhatsAppConfig; update: UpdateForm }) {
  return (
    <fieldset className="rounded-3xl border border-emerald-900/10 bg-white p-5">
      <legend className="px-2 text-base font-semibold text-slate-900">1. Cosa vuoi fare?</legend>
      <div className="grid gap-3 md:grid-cols-3">
        {CHANNEL_OPTIONS.map((option) => (
          <label
            key={option.value}
            className={`relative cursor-pointer rounded-2xl border p-4 transition ${form.provider === option.value ? "border-emerald-700 bg-emerald-50 ring-2 ring-emerald-700/10" : "border-slate-200 bg-white hover:border-emerald-700/40"}`}
          >
            <input
              className="sr-only"
              type="radio"
              name="provider"
              value={option.value}
              checked={form.provider === option.value}
              onChange={() => update("provider", option.value)}
            />
            <span className="flex items-center gap-2 font-semibold text-slate-900">
              <span className={`h-3 w-3 rounded-full ${form.provider === option.value ? "bg-emerald-700" : "bg-slate-300"}`} />
              {option.title}
            </span>
            <span className="mt-2 block text-sm leading-5 text-slate-600">{option.description}</span>
            {"badge" in option ? <span className="mt-3 inline-flex rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-800">{option.badge}</span> : null}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function ScheduleSection({ form, update }: { form: PresenzeWhatsAppConfig; update: UpdateForm }) {
  return (
    <fieldset className="rounded-3xl border border-emerald-900/10 bg-white p-5">
      <legend className="px-2 text-base font-semibold text-slate-900">2. Quando e quanto inviare</legend>
      <p className="mb-4 text-sm text-slate-600">GAIA controlla le giornate chiuse e invia solo nella fascia oraria scelta.</p>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <NumberField label="Controlla gli ultimi giorni" value={form.lookback_days} min={1} max={31} onValue={(value) => update("lookback_days", value)} />
        <NumberField label="Massimo messaggi per volta" value={form.max_per_run} min={1} max={100} onValue={(value) => update("max_per_run", value)} />
        <NumberField label="Non inviare prima delle" value={form.send_start_hour} min={0} max={23} onValue={(value) => update("send_start_hour", value)} />
        <NumberField label="Non inviare dopo le" value={form.send_end_hour} min={1} max={24} onValue={(value) => update("send_end_hour", value)} />
      </div>
      <label className="mt-4 flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm">
        <input className="mt-0.5" type="checkbox" checked={form.include_missing_punches} onChange={(event) => update("include_missing_punches", event.target.checked)} />
        <span><strong className="block text-slate-900">Avvisa anche chi non ha nessuna timbratura</strong><span className="text-slate-600">Lascia disattivato se vuoi segnalare solo ingressi o uscite incomplete.</span></span>
      </label>
    </fieldset>
  );
}

function AdvancedSection(props: DialogProps) {
  return (
    <details className="group rounded-3xl border border-slate-200 bg-white">
      <summary className="cursor-pointer list-none px-5 py-4 font-semibold text-slate-800 marker:hidden">
        <span className="flex items-center justify-between gap-3">
          <span><span className="block">Impostazioni avanzate</span><span className="mt-1 block text-sm font-normal text-slate-500">Collegamento tecnico, orario automatico e pause di sicurezza.</span></span>
          <span aria-hidden="true" className="text-xl text-emerald-800 transition group-open:rotate-45">+</span>
        </span>
      </summary>
      <div className="border-t border-slate-200 p-5">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <TextField label="Indirizzo del servizio WAHA" value={props.form.waha_url} onValue={(value) => props.update("waha_url", value)} />
          <TextField label="Nome della sessione WhatsApp" value={props.form.waha_session} onValue={(value) => props.update("waha_session", value)} />
          <TextField label="Programmazione automatica (cron)" value={props.form.reminder_cron} onValue={(value) => props.update("reminder_cron", value)} />
          <SecretField label="Chiave di accesso WAHA" configured={props.configuration.api_key_configured} value={props.apiKey} clear={props.clearApiKey} onValue={props.setApiKey} onClear={props.setClearApiKey} />
          <SecretField label="Chiave di sicurezza webhook" configured={props.configuration.hmac_key_configured} value={props.hmacKey} clear={props.clearHmacKey} onValue={props.setHmacKey} onClear={props.setClearHmacKey} />
          <div className="grid grid-cols-2 gap-3">
            <NumberField label="Pausa minima" value={props.form.min_delay_seconds} min={0} max={3600} suffix="secondi" onValue={(value) => props.update("min_delay_seconds", value)} />
            <NumberField label="Pausa massima" value={props.form.max_delay_seconds} min={0} max={3600} suffix="secondi" onValue={(value) => props.update("max_delay_seconds", value)} />
          </div>
        </div>
        <p className="mt-4 rounded-2xl bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-900">Non modificare questi valori se il collegamento funziona. Le chiavi salvate restano cifrate e non vengono mai mostrate.</p>
      </div>
    </details>
  );
}

function DialogFooter({ busy }: { busy: boolean }) {
  return (
    <footer className="flex items-center justify-between gap-4 border-t border-slate-200 bg-white px-5 py-4 sm:px-8">
      <p className="text-xs text-slate-500">
        Il salvataggio non invia messaggi subito. Le modifiche valgono dal prossimo controllo.
      </p>
      <button className="btn-primary" disabled={busy} type="submit">
        {busy ? "Salvataggio..." : "Salva configurazione"}
      </button>
    </footer>
  );
}

type TextFieldProps = { label: string; value: string; onValue: (value: string) => void };

function TextField({ label, value, onValue }: TextFieldProps) {
  return (
    <label className="text-sm font-medium">
      {label}
      <input
        className="field mt-2 w-full"
        value={value}
        onChange={(event) => onValue(event.target.value)}
      />
    </label>
  );
}

type NumberFieldProps = {
  label: string;
  value: number;
  min: number;
  max: number;
  suffix?: string;
  onValue: (value: number) => void;
};

function NumberField({ label, value, min, max, suffix, onValue }: NumberFieldProps) {
  return (
    <label className="text-sm font-medium">
      {label}
      <input
        className="field mt-2 w-full"
        type="number"
        min={min}
        max={max}
        value={value}
        onChange={(event) => onValue(numberValue(event.target.value))}
      />
      {suffix ? <span className="mt-1 block text-xs font-normal text-slate-500">{suffix}</span> : null}
    </label>
  );
}

type SecretFieldProps = {
  label: string;
  configured: boolean;
  value: string;
  clear: boolean;
  onValue: (value: string) => void;
  onClear: (value: boolean) => void;
};

function SecretField(props: SecretFieldProps) {
  return (
    <div>
      <label className="text-sm font-medium">
        {props.label}
        <input
          className="field mt-2 w-full"
          type="password"
          autoComplete="new-password"
          value={props.value}
          onChange={(event) => props.onValue(event.target.value)}
          placeholder={props.configured ? "Configurato - inserisci per sostituire" : "Non configurato"}
        />
      </label>
      <label className="mt-2 flex items-center gap-2 text-xs text-slate-500">
        <input
          type="checkbox"
          checked={props.clear}
          onChange={(event) => props.onClear(event.target.checked)}
        />
        Rimuovi il segreto salvato
      </label>
    </div>
  );
}
