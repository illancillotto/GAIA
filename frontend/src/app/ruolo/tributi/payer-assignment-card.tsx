"use client";

import { FormEvent, useEffect, useState } from "react";

import { getStoredAccessToken } from "@/lib/auth";
import { getAvvisoPayer, removeAvvisoPayer, setAvvisoPayer } from "@/lib/ruolo-payer-api";
import type { RuoloPayerAssignment, RuoloPayerAssignmentRequest, RuoloPayerAssignments, RuoloPayerReason } from "@/types/ruolo-payer";
import { ActionCard, ActionField } from "./action-card";

const REASON_OPTIONS: Array<{ value: RuoloPayerReason; label: string }> = [
  { value: "decesso", label: "Decesso: paga l'erede" },
  { value: "vendita", label: "Vendita o voltura: paga l'acquirente" },
  { value: "ufficio", label: "Indicazione dell'ufficio" },
];
const INPUT_CLASS = "w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:border-[#8CB39D]";

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Operazione non riuscita";
}

function formatDay(value: string): string {
  return new Date(value).toLocaleDateString("it-IT");
}

function PayerSummary({ payer }: { payer: RuoloPayerAssignment }) {
  return (
    <div className="rounded-xl border border-amber-200 bg-white px-3 py-2 text-sm leading-5 text-gray-700">
      <p className="font-semibold text-gray-900">
        Paga: {payer.payer_name ?? "-"} <span className="font-mono text-xs text-gray-600">{payer.payer_tax_code}</span>
      </p>
      <p>{payer.payer_address ?? "Indirizzo non presente in anagrafica"}</p>
      <p className="text-xs text-gray-500">
        {payer.reason_label} · dal {formatDay(payer.created_at)}
        {payer.notes ? ` · ${payer.notes}` : ""}
      </p>
    </div>
  );
}

type VoidedPayer = RuoloPayerAssignment & { voided_at: string };

function readPayerForm(form: HTMLFormElement): RuoloPayerAssignmentRequest {
  const data = new FormData(form);
  return {
    payer_tax_code: String(data.get("payer_tax_code") || "").trim().toUpperCase(),
    reason: String(data.get("reason")) as RuoloPayerReason,
    notes: String(data.get("notes") || "").trim() || null,
  };
}

function PayerForm({ replacing, onSubmit }: { replacing: boolean; onSubmit: (event: FormEvent<HTMLFormElement>) => void }) {
  return (
    <form className="space-y-3" onSubmit={onSubmit}>
      <ActionField htmlFor="tributi-payer-tax-code" label="CF / P.IVA di chi paga">
        <input id="tributi-payer-tax-code" name="payer_tax_code" placeholder="Deve essere già in anagrafica" className={INPUT_CLASS} />
      </ActionField>
      <ActionField htmlFor="tributi-payer-reason" label="Motivo">
        <select id="tributi-payer-reason" name="reason" defaultValue="decesso" className={INPUT_CLASS}>
          {REASON_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>
      </ActionField>
      <ActionField htmlFor="tributi-payer-notes" label="Nota">
        <input id="tributi-payer-notes" name="notes" placeholder="Es. erede unico, atto di vendita del..." className={INPUT_CLASS} />
      </ActionField>
      <button type="submit" className="btn-secondary w-full">{replacing ? "Sostituisci pagatore" : "Collega pagatore"}</button>
    </form>
  );
}

function PayerHistory({ rows }: { rows: VoidedPayer[] }) {
  if (!rows.length) return null;
  return (
    <details className="text-xs text-gray-500">
      <summary>Storico ({rows.length})</summary>
      <ul className="mt-1 space-y-1">
        {rows.map((row) => (
          <li key={row.id}>
            {row.payer_name ?? "-"} ({row.payer_tax_code}) · {row.reason_label} · {formatDay(row.created_at)} → {formatDay(row.voided_at)}
          </li>
        ))}
      </ul>
    </details>
  );
}

export function PayerAssignmentCard({ avvisoId }: { avvisoId: string }) {
  const [state, setState] = useState<RuoloPayerAssignments | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    setState(null);
    setMessage(null);
    getAvvisoPayer(token, avvisoId).then(setState, (error: unknown) => setMessage(errorMessage(error)));
  }, [avvisoId]);

  async function run(action: (token: string) => Promise<RuoloPayerAssignments>, done: string) {
    const token = getStoredAccessToken();
    if (!token) return;
    try {
      setState(await action(token));
      setMessage(done);
    } catch (error) {
      setMessage(errorMessage(error));
    }
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = readPayerForm(event.currentTarget);
    if (!payload.payer_tax_code) {
      setMessage("Indica il codice fiscale o la partita IVA di chi paga.");
      return;
    }
    void run((token) => setAvvisoPayer(token, avvisoId, payload), "Pagatore collegato all'avviso.");
  }

  const active = state?.active ?? null;
  const voided = state?.history.filter((row): row is VoidedPayer => Boolean(row.voided_at)) ?? [];

  return (
    <ActionCard
      eyebrow="Chi paga"
      title="Pagatore diverso dall'intestatario"
      description="Per deceduti o vendite: il sollecito di questo avviso viene intestato e spedito a chi paga, con il riferimento all'intestatario."
      tone="amber"
    >
      <div className="space-y-3">
        {active ? <PayerSummary payer={active} /> : <p className="text-sm text-gray-600">Paga l&apos;intestatario dell&apos;avviso.</p>}
        <PayerForm replacing={Boolean(active)} onSubmit={onSubmit} />
        {active ? (
          <button type="button" className="btn-secondary w-full" onClick={() => void run((token) => removeAvvisoPayer(token, avvisoId), "Pagatore rimosso: paga l'intestatario.")}>
            Rimuovi pagatore
          </button>
        ) : null}
        {message ? <p className="text-sm text-gray-700" role="status">{message}</p> : null}
        <PayerHistory rows={voided} />
      </div>
    </ActionCard>
  );
}
