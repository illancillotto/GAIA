"use client";

import { useEffect, useState } from "react";

import { RiordinoConfirmDialog } from "@/components/riordino/shared/confirm-dialog";
import { catastoPatchMeterReading, catastoValidateMeterReading } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatMeterReading } from "@/types/catasto";

function formatRecordType(value: string | null): string {
  const normalized = value?.trim().toUpperCase();
  if (normalized === "CHIUSURA_IDRANTE") return "Chiusura idrante";
  if (normalized === "PREDISPOSIZIONE") return "Predisposizione";
  if (normalized === "CONT_NO_TES") return "Lettura contatore";
  if (normalized === "CONT_TESSER") return "Lettura contatore tessera";
  return value || "—";
}

type EditState = {
  punto_consegna: string;
  matricola: string;
  record_type: string;
  tipologia_idrante: string;
  codice_fiscale: string;
  intervento_da_eseguire: string;
  note: string;
  change_note: string;
};

function buildEditState(reading: CatMeterReading): EditState {
  return {
    punto_consegna: reading.punto_consegna ?? "",
    matricola: reading.matricola ?? "",
    record_type: reading.record_type ?? "",
    tipologia_idrante: reading.tipologia_idrante ?? "",
    codice_fiscale: reading.codice_fiscale ?? "",
    intervento_da_eseguire: reading.intervento_da_eseguire ?? "",
    note: reading.note ?? "",
    change_note: "",
  };
}

function formatFieldLabel(field: string): string {
  const labels: Record<string, string> = {
    punto_consegna: "Punto consegna",
    matricola: "Matricola",
    record_type: "Tipo record",
    tipologia_idrante: "Tipologia apparato",
    codice_fiscale: "Codice fiscale",
    intervento_da_eseguire: "Intervento da eseguire",
    note: "Note",
  };
  return labels[field] ?? field.replaceAll("_", " ");
}

function formatAuditValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.map((item) => formatAuditValue(item)).join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function getChangedFieldNames(reading: CatMeterReading): string[] {
  return Object.keys(reading.manual_corrections ?? {});
}

export function MeterReadingDetailDrawer({
  reading,
  onClose,
  onUpdated,
}: {
  reading: CatMeterReading | null;
  onClose: () => void;
  onUpdated: (reading: CatMeterReading) => void;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [form, setForm] = useState<EditState | null>(null);
  const [showValidateConfirm, setShowValidateConfirm] = useState(false);

  useEffect(() => {
    if (!reading) {
      setIsEditing(false);
      setForm(null);
      setSaveError(null);
      setShowValidateConfirm(false);
      return;
    }
    setForm(buildEditState(reading));
    setSaveError(null);
  }, [reading]);

  if (!reading || !form) return null;
  const currentReading = reading;
  const currentForm = form;

  async function submitEdits() {
    const token = getStoredAccessToken();
    if (!token) return;
    try {
      setSaving(true);
      setSaveError(null);
      const updated = await catastoPatchMeterReading(token, currentReading.id, {
        punto_consegna: currentForm.punto_consegna,
        matricola: currentForm.matricola,
        record_type: currentForm.record_type,
        tipologia_idrante: currentForm.tipologia_idrante,
        codice_fiscale: currentForm.codice_fiscale,
        intervento_da_eseguire: currentForm.intervento_da_eseguire,
        note: currentForm.note,
        change_note: currentForm.change_note || null,
      });
      setIsEditing(false);
      setForm(buildEditState(updated));
      onUpdated(updated);
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Salvataggio correzione fallito");
    } finally {
      setSaving(false);
    }
  }

  async function submitValidation() {
    const token = getStoredAccessToken();
    if (!token) return;
    try {
      setSaving(true);
      setSaveError(null);
      const updated = await catastoValidateMeterReading(token, currentReading.id);
      setShowValidateConfirm(false);
      setForm(buildEditState(updated));
      onUpdated(updated);
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Validazione lettura fallita");
    } finally {
      setSaving(false);
    }
  }

  const canValidate = !isEditing && currentReading.validation_status === "warning";

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-slate-950/35">
      <button aria-label="Chiudi dettaglio lettura" className="flex-1" onClick={onClose} type="button" />
      <aside className="h-full w-full max-w-xl overflow-y-auto bg-white p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="section-title">Dettaglio lettura</p>
            <p className="section-copy">
              {currentReading.punto_consegna} · anno {currentReading.anno}
            </p>
          </div>
          <div className="flex gap-2">
            {canValidate ? (
              <button
                className="btn-primary bg-blue-600 hover:bg-blue-700 focus-visible:ring-blue-300"
                disabled={saving}
                onClick={() => setShowValidateConfirm(true)}
                type="button"
              >
                Valida lettura
              </button>
            ) : null}
            <button
              className={isEditing ? "btn-secondary" : "btn-primary bg-sky-600 hover:bg-sky-700 focus-visible:ring-sky-300"}
              onClick={() => setIsEditing((value) => !value)}
              type="button"
            >
              {isEditing ? "Annulla modifica" : "Correggi lettura"}
            </button>
            <button className="btn-secondary" onClick={onClose} type="button">
              Chiudi
            </button>
          </div>
        </div>

        {currentReading.manual_override_updated_at ? (
          <div className="mt-4 rounded-2xl border border-sky-100 bg-sky-50 px-4 py-3 text-sm text-sky-900">
            Correzione manuale presente · ultimo aggiornamento {new Date(currentReading.manual_override_updated_at).toLocaleString("it-IT")}
          </div>
        ) : null}
        {saveError ? <div className="mt-4 rounded-2xl border border-rose-100 bg-rose-50 px-4 py-3 text-sm text-rose-800">{saveError}</div> : null}

        {isEditing ? (
          <div className="mt-6 space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block text-sm font-medium text-slate-700">
                Punto consegna
                <input className="form-control mt-1" value={currentForm.punto_consegna} onChange={(event) => setForm({ ...currentForm, punto_consegna: event.target.value })} />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Matricola
                <input className="form-control mt-1" value={currentForm.matricola} onChange={(event) => setForm({ ...currentForm, matricola: event.target.value })} />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Tipo record
                <input className="form-control mt-1" value={currentForm.record_type} onChange={(event) => setForm({ ...currentForm, record_type: event.target.value })} />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Tipologia apparato
                <input className="form-control mt-1" value={currentForm.tipologia_idrante} onChange={(event) => setForm({ ...currentForm, tipologia_idrante: event.target.value })} />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Codice fiscale
                <input className="form-control mt-1" value={currentForm.codice_fiscale} onChange={(event) => setForm({ ...currentForm, codice_fiscale: event.target.value })} />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Intervento da eseguire
                <input
                  className="form-control mt-1"
                  value={currentForm.intervento_da_eseguire}
                  onChange={(event) => setForm({ ...currentForm, intervento_da_eseguire: event.target.value })}
                />
              </label>
            </div>
            <label className="block text-sm font-medium text-slate-700">
              Note
              <textarea className="form-control mt-1 min-h-24" value={currentForm.note} onChange={(event) => setForm({ ...currentForm, note: event.target.value })} />
            </label>
            <label className="block text-sm font-medium text-slate-700">
              Nota operatore
              <textarea
                className="form-control mt-1 min-h-20"
                placeholder="Motivo della correzione"
                value={currentForm.change_note}
                onChange={(event) => setForm({ ...currentForm, change_note: event.target.value })}
              />
            </label>
            <div className="flex justify-end">
              <button className="btn-primary" disabled={saving} onClick={() => void submitEdits()} type="button">
                {saving ? "Salvataggio..." : "Salva correzione"}
              </button>
            </div>
          </div>
        ) : (
          <div className="mt-6 grid gap-3 sm:grid-cols-2">
              {[
              ["Matricola", currentReading.matricola],
              ["Sigillo", currentReading.sigillo],
              ["Tipo record", formatRecordType(currentReading.record_type)],
              ["Classe record", currentReading.record_kind],
              ["Stato operativo", currentReading.operational_state],
              ["Tipologia apparato", currentReading.tipologia_idrante],
              ["Codice fiscale", currentReading.codice_fiscale_normalizzato ?? currentReading.codice_fiscale],
              ["Soggetto", currentReading.subject_display_name],
              ["Lettura iniziale", currentReading.lettura_iniziale],
              ["Lettura finale", currentReading.lettura_finale],
              ["Consumo mc", currentReading.consumo_mc],
              ["Data lettura", currentReading.data_lettura],
              ["Operatore", currentReading.operatore_lettura],
              ["Coltura", currentReading.coltura],
              ["Tariffa", currentReading.tariffa],
              ["Telefono", currentReading.telefono],
              ["Intervento da eseguire", currentReading.intervento_da_eseguire],
              ["Note", currentReading.note],
            ].map(([label, value]) => (
              <div key={label} className="rounded-xl border border-slate-200 px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
                <p className="mt-2 text-sm text-slate-900">{value || "—"}</p>
              </div>
            ))}
          </div>
        )}

        {currentReading.validation_messages.length > 0 ? (
          <div className="mt-6">
            <p className="section-title">Validazione</p>
            <div className="mt-3 space-y-2">
              {currentReading.validation_messages.map((message) => (
                <div
                  key={`${message.code}-${message.field ?? "none"}`}
                  className={`rounded-xl px-4 py-3 text-sm ${
                    message.level === "error"
                      ? "bg-rose-50 text-rose-800"
                      : message.level === "warning"
                        ? "bg-amber-50 text-amber-800"
                        : "bg-slate-100 text-slate-700"
                  }`}
                >
                  <span className="font-semibold">{message.code}</span> · {message.message}
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {currentReading.manual_audits.length > 0 ? (
          <div className="mt-6">
            <div className="flex items-center justify-between gap-3">
              <p className="section-title">Storico correzioni</p>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                {currentReading.manual_audits.length} eventi
              </span>
            </div>
            {getChangedFieldNames(currentReading).length > 0 ? (
              <p className="mt-2 text-xs text-slate-500">
                Override attivi: {getChangedFieldNames(currentReading).map((field) => formatFieldLabel(field)).join(", ")}
              </p>
            ) : null}
            <div className="mt-3 space-y-3">
              {currentReading.manual_audits.map((audit) => {
                const previousValues = audit.previous_values && !Array.isArray(audit.previous_values) ? audit.previous_values : {};
                const newValues = audit.new_values && !Array.isArray(audit.new_values) ? audit.new_values : {};
                const changedFields = Object.keys(newValues).filter((field) => previousValues[field] !== newValues[field]);
                return (
                  <div key={audit.id} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-slate-900">{audit.changed_by_display_name ?? "Operatore non identificato"}</p>
                        <p className="mt-1 text-xs text-slate-500">{new Date(audit.changed_at).toLocaleString("it-IT")}</p>
                      </div>
                      <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-700">
                        {changedFields.length} campi
                      </span>
                    </div>
                    {audit.change_note ? <p className="mt-3 rounded-xl bg-white px-3 py-2 text-sm text-slate-700">{audit.change_note}</p> : null}
                    <div className="mt-3 space-y-2">
                      {changedFields.map((field) => (
                        <div key={field} className="rounded-xl bg-white px-3 py-3">
                          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{formatFieldLabel(field)}</p>
                          <div className="mt-2 grid gap-2 sm:grid-cols-2">
                            <div>
                              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">Prima</p>
                              <p className="mt-1 text-sm text-slate-700">{formatAuditValue(previousValues[field])}</p>
                            </div>
                            <div>
                              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">Dopo</p>
                              <p className="mt-1 text-sm font-medium text-slate-900">{formatAuditValue(newValues[field])}</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}
      </aside>
      <RiordinoConfirmDialog
        open={showValidateConfirm}
        title="Confermare validazione lettura?"
        description="La lettura verrà marcata come valida e i warning correnti saranno chiusi. L'operazione resterà tracciata nello storico correzioni."
        confirmLabel="Valida lettura"
        busy={saving}
        onCancel={() => setShowValidateConfirm(false)}
        onConfirm={submitValidation}
      />
    </div>
  );
}
