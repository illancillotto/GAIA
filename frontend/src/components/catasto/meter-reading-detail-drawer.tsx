"use client";

import type { CatMeterReading } from "@/types/catasto";

function formatRecordType(value: string | null): string {
  const normalized = value?.trim().toUpperCase();
  if (normalized === "CHIUSURA_IDRANTE") return "Chiusura idrante";
  if (normalized === "PREDISPOSIZIONE") return "Predisposizione";
  if (normalized === "CONT_NO_TES") return "Lettura contatore";
  if (normalized === "CONT_TESSER") return "Lettura contatore tessera";
  return value || "—";
}

export function MeterReadingDetailDrawer({
  reading,
  onClose,
}: {
  reading: CatMeterReading | null;
  onClose: () => void;
}) {
  if (!reading) return null;

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-slate-950/35">
      <button aria-label="Chiudi dettaglio lettura" className="flex-1" onClick={onClose} type="button" />
      <aside className="h-full w-full max-w-xl overflow-y-auto bg-white p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="section-title">Dettaglio lettura</p>
            <p className="section-copy">
              {reading.punto_consegna} · anno {reading.anno}
            </p>
          </div>
          <button className="btn-secondary" onClick={onClose} type="button">
            Chiudi
          </button>
        </div>

        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          {[
            ["Matricola", reading.matricola],
            ["Sigillo", reading.sigillo],
            ["Tipo record", formatRecordType(reading.record_type)],
            ["Classe record", reading.record_kind],
            ["Stato operativo", reading.operational_state],
            ["Tipologia apparato", reading.tipologia_idrante],
            ["Codice fiscale", reading.codice_fiscale_normalizzato ?? reading.codice_fiscale],
            ["Soggetto", reading.subject_display_name],
            ["Lettura iniziale", reading.lettura_iniziale],
            ["Lettura finale", reading.lettura_finale],
            ["Consumo mc", reading.consumo_mc],
            ["Data lettura", reading.data_lettura],
            ["Operatore", reading.operatore_lettura],
            ["Coltura", reading.coltura],
            ["Tariffa", reading.tariffa],
            ["Telefono", reading.telefono],
            ["Intervento da eseguire", reading.intervento_da_eseguire],
            ["Note", reading.note],
          ].map(([label, value]) => (
            <div key={label} className="rounded-xl border border-slate-200 px-4 py-3">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
              <p className="mt-2 text-sm text-slate-900">{value || "—"}</p>
            </div>
          ))}
        </div>

        {reading.validation_messages.length > 0 ? (
          <div className="mt-6">
            <p className="section-title">Validazione</p>
            <div className="mt-3 space-y-2">
              {reading.validation_messages.map((message) => (
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
      </aside>
    </div>
  );
}
