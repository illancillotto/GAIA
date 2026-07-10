"use client";

import type { CatIndiceRuoloReconciliation } from "@/types/catasto";

function formatInteger(value: number): string {
  return new Intl.NumberFormat("it-IT").format(value);
}

function formatHa(value: string): string {
  return new Intl.NumberFormat("it-IT", { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(Number(value));
}

function formatEuro(value: string): string {
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(Number(value));
}

function formatPercent(value: string | null): string {
  if (value == null) {
    return "—";
  }
  return new Intl.NumberFormat("it-IT", { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(Number(value)) + "%";
}

function percentOf(part: string, total: string): string {
  const totalNumber = Number(total);
  if (totalNumber <= 0) {
    return "—";
  }
  return formatPercent(String((Number(part) / totalNumber) * 100));
}

function ReconciliationMetric({
  label,
  value,
  sub,
  tone = "neutral",
}: {
  label: string;
  value: string;
  sub: string;
  tone?: "good" | "warning" | "neutral";
}) {
  const toneClass =
    tone === "good"
      ? "border-[#b9d8c3] bg-[#f2faf4] text-[#14532d]"
      : tone === "warning"
        ? "border-[#f3d7a2] bg-[#fff8e9] text-[#8a4f00]"
        : "border-[#d7e4da] bg-white text-slate-900";
  return (
    <div className={`rounded-3xl border p-4 shadow-sm ${toneClass}`}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] opacity-75">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight">{value}</p>
      <p className="mt-1 text-xs opacity-75">{sub}</p>
    </div>
  );
}

export function RuoloReconciliationCard({
  reconciliation,
  anno,
}: {
  reconciliation: CatIndiceRuoloReconciliation | null | undefined;
  anno: number | null | undefined;
}) {
  if (!reconciliation) {
    return null;
  }

  const excludedPercent = percentOf(reconciliation.importo_ruolo_escluso, reconciliation.importo_ruolo_totale);
  return (
    <article className="overflow-hidden rounded-[2rem] border border-[#c9ddcf] bg-gradient-to-br from-[#f6fbf7] via-white to-[#fff8ea] shadow-sm">
      <div className="border-b border-[#dbe8df] bg-white/70 px-5 py-4">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5f7d68]">Riconciliazione ruolo</p>
        <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-slate-950">Perché il totale ruolo non coincide sempre con gli indici</h2>
            <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600">
              Gli indici continuano a usare solo il catasto corrente Agenzia Entrate con distretto valorizzato. La riconciliazione parte invece
              da <span className="font-semibold text-slate-800">ruolo_particelle</span>: le righe senza aggancio territoriale affidabile restano fuori
              dai totali per Alta/Bassa/Canaletta e sono mostrate qui come differenza spiegata, non come attribuzione territoriale.
            </p>
          </div>
          <span className="rounded-full border border-[#d7e4da] bg-white px-4 py-2 text-xs font-semibold text-[#1d4e35]">
            Anno ruolo {anno ?? "—"}
          </span>
        </div>
      </div>

      <div className="grid gap-3 p-5 md:grid-cols-4">
        <ReconciliationMetric
          label="Incluso negli indici"
          value={formatEuro(reconciliation.importo_ruolo_incluso)}
          sub={`${formatInteger(reconciliation.particelle_ruolo_incluse_count)} particelle ruolo · ${formatPercent(reconciliation.coverage_percent)} del totale`}
          tone="good"
        />
        <ReconciliationMetric
          label="Escluso dagli indici"
          value={formatEuro(reconciliation.importo_ruolo_escluso)}
          sub={`${formatInteger(reconciliation.particelle_ruolo_escluse_count)} particelle ruolo · ${excludedPercent} del totale`}
          tone="warning"
        />
        <ReconciliationMetric
          label="Totale ruolo particellare"
          value={formatEuro(reconciliation.importo_ruolo_totale)}
          sub={`${formatInteger(reconciliation.righe_ruolo_totali_count)} righe ruolo da ruolo_particelle`}
        />
        <ReconciliationMetric
          label="Superficie esclusa"
          value={`${formatHa(reconciliation.superficie_irrigata_esclusa_ha)} ha`}
          sub="Ettari ruolo non attribuiti a un indice operativo"
        />
      </div>

      <div className="grid gap-4 border-t border-[#dbe8df] p-5 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="rounded-3xl border border-[#d7e4da] bg-white p-4">
          <p className="text-sm font-semibold text-slate-900">Regola di lettura</p>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Il dato principale resta il quadro per indice, perché è agganciato a particelle correnti e distretti del catasto AE. La differenza
            nasce quando il ruolo contiene particelle non più risolvibili nel catasto corrente, oppure particelle presenti ma prive di distretto.
          </p>
          <div className="mt-4 rounded-2xl bg-[#f7fbf8] p-3 text-xs leading-5 text-slate-600">
            Importi esclusi: manutenzione {formatEuro(reconciliation.importo_ruolo_escluso_manutenzione)} · irrigazione{" "}
            {formatEuro(reconciliation.importo_ruolo_escluso_irrigazione)} · istituzionale{" "}
            {formatEuro(reconciliation.importo_ruolo_escluso_istituzionale)}.
          </div>
        </div>

        <div className="rounded-3xl border border-[#d7e4da] bg-white p-4">
          <p className="text-sm font-semibold text-slate-900">Motivi della differenza</p>
          {reconciliation.reasons.length === 0 ? (
            <p className="mt-3 rounded-2xl border border-dashed border-[#d7e4da] bg-[#f7fbf8] px-4 py-6 text-sm text-slate-500">
              Nessuna riga ruolo esclusa dagli indici.
            </p>
          ) : (
            <div className="mt-3 space-y-3">
              {reconciliation.reasons.map((reason) => (
                <div key={reason.key} className="rounded-2xl border border-[#eef4ef] bg-[#fbfdfb] p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{reason.label}</p>
                      <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-500">{reason.description}</p>
                    </div>
                    <p className="text-right text-sm font-semibold text-[#8a4f00]">{formatEuro(reason.importo_ruolo)}</p>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-[11px] font-semibold text-slate-600">
                    <span className="rounded-full bg-white px-2.5 py-1 ring-1 ring-[#d7e4da]">
                      {formatInteger(reason.particelle_ruolo_distinte_count)} particelle ruolo
                    </span>
                    <span className="rounded-full bg-white px-2.5 py-1 ring-1 ring-[#d7e4da]">
                      {formatInteger(reason.righe_ruolo_count)} righe
                    </span>
                    <span className="rounded-full bg-white px-2.5 py-1 ring-1 ring-[#d7e4da]">
                      {formatHa(reason.superficie_irrigata_ha)} ha
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </article>
  );
}
