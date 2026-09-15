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
        className="flex h-[calc(100vh-16px)] w-[calc(100vw-16px)] max-w-[1500px] flex-col overflow-hidden rounded-[30px] bg-[#f7faf7] shadow-2xl sm:h-[calc(100vh-32px)]"
        onSubmit={props.onSubmit}
      >
        <DialogHeader onClose={props.onClose} />
        <div className="flex-1 overflow-y-auto p-5 sm:p-8">
          <div className="grid gap-5 lg:grid-cols-3">
            <ModeSection form={props.form} update={props.update} />
            <WahaSection {...props} />
            <ScheduleSection form={props.form} update={props.update} />
          </div>
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
          Configurazione protetta
        </p>
        <h2 id="whatsapp-config-title" className="mt-1 text-2xl font-semibold">
          Canale WhatsApp
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          I segreti salvati non vengono mai mostrati in chiaro.
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
    <fieldset className="rounded-3xl border border-slate-200 bg-white p-5">
      <legend className="px-2 font-semibold">1. Modalita</legend>
      <label className="text-sm font-medium">
        Stato del canale
        <select
          className="field mt-2 w-full"
          value={form.provider}
          onChange={(event) =>
            update("provider", event.target.value as PresenzeWhatsAppConfig["provider"])
          }
        >
          <option value="">Spento</option>
          <option value="dry_run">Prova senza invio</option>
          <option value="waha">WAHA, invio reale</option>
        </select>
      </label>
      <p className="mt-3 text-xs leading-5 text-slate-500">
        Usa prima &ldquo;Prova senza invio&rdquo; per verificare destinatari e testi nello storico.
      </p>
    </fieldset>
  );
}

function WahaSection(props: DialogProps) {
  return (
    <fieldset className="rounded-3xl border border-slate-200 bg-white p-5 lg:col-span-2">
      <legend className="px-2 font-semibold">2. Collegamento WAHA</legend>
      <div className="grid gap-4 sm:grid-cols-2">
        <TextField
          label="URL WAHA"
          value={props.form.waha_url}
          onValue={(value) => props.update("waha_url", value)}
        />
        <TextField
          label="Sessione"
          value={props.form.waha_session}
          onValue={(value) => props.update("waha_session", value)}
        />
        <SecretField
          label="API key WAHA"
          configured={props.configuration.api_key_configured}
          value={props.apiKey}
          clear={props.clearApiKey}
          onValue={props.setApiKey}
          onClear={props.setClearApiKey}
        />
        <SecretField
          label="Firma webhook HMAC"
          configured={props.configuration.hmac_key_configured}
          value={props.hmacKey}
          clear={props.clearHmacKey}
          onValue={props.setHmacKey}
          onClear={props.setClearHmacKey}
        />
      </div>
    </fieldset>
  );
}

function ScheduleSection({ form, update }: { form: PresenzeWhatsAppConfig; update: UpdateForm }) {
  return (
    <fieldset className="rounded-3xl border border-slate-200 bg-white p-5 lg:col-span-3">
      <legend className="px-2 font-semibold">3. Pianificazione e limiti</legend>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <TextField label="Cron (Europe/Rome)" value={form.reminder_cron} onValue={(value) => update("reminder_cron", value)} />
        <NumberField label="Giorni da controllare" value={form.lookback_days} min={1} max={31} onValue={(value) => update("lookback_days", value)} />
        <NumberField label="Massimo per esecuzione" value={form.max_per_run} min={1} max={100} onValue={(value) => update("max_per_run", value)} />
        <NumberField label="Pausa minima (secondi)" value={form.min_delay_seconds} min={0} max={3600} onValue={(value) => update("min_delay_seconds", value)} />
        <NumberField label="Pausa massima (secondi)" value={form.max_delay_seconds} min={0} max={3600} onValue={(value) => update("max_delay_seconds", value)} />
        <NumberField label="Invii dalle ore" value={form.send_start_hour} min={0} max={23} onValue={(value) => update("send_start_hour", value)} />
        <NumberField label="Invii fino alle ore" value={form.send_end_hour} min={1} max={24} onValue={(value) => update("send_end_hour", value)} />
        <label className="flex items-center gap-3 rounded-2xl border border-slate-200 px-4 py-3 text-sm font-medium">
          <input type="checkbox" checked={form.include_missing_punches} onChange={(event) => update("include_missing_punches", event.target.checked)} />
          Includi giornate senza timbrature
        </label>
      </div>
    </fieldset>
  );
}

function DialogFooter({ busy }: { busy: boolean }) {
  return (
    <footer className="flex items-center justify-between gap-4 border-t border-slate-200 bg-white px-5 py-4 sm:px-8">
      <p className="text-xs text-slate-500">
        Le modifiche diventano effettive entro un minuto, senza deploy.
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
  onValue: (value: number) => void;
};

function NumberField({ label, value, min, max, onValue }: NumberFieldProps) {
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
