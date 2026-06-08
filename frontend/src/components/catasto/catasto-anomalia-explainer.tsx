"use client";

import { useEffect, useState } from "react";

import { describeCatastoAnomalia, explainCatastoAnomalia } from "@/lib/catasto-anomalie";

type AnomaliaLike = {
  tipo: string;
  descrizione?: string | null;
  dati_json?: Record<string, unknown> | null;
};

type CatastoAnomaliaExplainerProps = {
  anomalia: AnomaliaLike;
  buttonClassName?: string;
  buttonLabel?: string;
};

export function CatastoAnomaliaExplainer({
  anomalia,
  buttonClassName = "text-xs font-medium text-[#1D4E35] underline underline-offset-2",
  buttonLabel = "Approfondisci",
}: CatastoAnomaliaExplainerProps) {
  const [open, setOpen] = useState(false);
  const explanation = explainCatastoAnomalia(anomalia);

  useEffect(() => {
    if (!open) return;

    function handleKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  return (
    <>
      <button type="button" className={buttonClassName} onClick={() => setOpen(true)}>
        {buttonLabel}
      </button>

      {open ? (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-sm">
          <button
            aria-label="Chiudi approfondimento anomalia"
            className="absolute inset-0 cursor-default"
            onClick={() => setOpen(false)}
            type="button"
          />
          <div className="relative z-10 flex max-h-[92vh] w-full max-w-3xl flex-col overflow-hidden rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
            <div className="border-b border-gray-100 px-6 py-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Approfondimento anomalia</p>
                  <h2 className="mt-2 text-2xl font-semibold text-gray-900">{explanation.title}</h2>
                  <p className="mt-2 text-sm text-gray-500">{anomalia.descrizione ?? anomalia.tipo}</p>
                </div>
                <button className="btn-secondary" type="button" onClick={() => setOpen(false)}>
                  Chiudi
                </button>
              </div>
            </div>

            <div className="space-y-5 overflow-y-auto bg-[#f6f8f6] px-6 py-6">
              <section className="rounded-2xl border border-[#d9dfd6] bg-white p-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#5f7d68]">Spiegazione semplice</p>
                <p className="mt-2 text-base font-semibold text-slate-950">{explanation.summary}</p>
                <p className="mt-3 text-sm leading-6 text-slate-600">{explanation.whyItHappened}</p>
              </section>

              <section className="rounded-2xl border border-[#d9dfd6] bg-white p-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#5f7d68]">Dettaglio rilevato</p>
                <p className="mt-2 text-sm leading-6 text-slate-700">{describeCatastoAnomalia(anomalia)}</p>
              </section>

              {explanation.calculations.length > 0 ? (
                <section className="rounded-2xl border border-[#d9dfd6] bg-white p-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#5f7d68]">Numeri del controllo</p>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    {explanation.calculations.map((item) => (
                      <div key={item.label} className="rounded-2xl bg-slate-50 p-4">
                        <p className="text-xs uppercase tracking-[0.16em] text-slate-400">{item.label}</p>
                        <p className="mt-2 text-xl font-semibold text-slate-950">{item.value}</p>
                      </div>
                    ))}
                  </div>
                </section>
              ) : null}

              <section className="rounded-2xl border border-[#d9dfd6] bg-white p-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#5f7d68]">Cosa verificare</p>
                <div className="mt-4 space-y-3">
                  {explanation.checks.map((check) => (
                    <div key={check} className="rounded-2xl bg-emerald-50/70 px-4 py-3 text-sm text-slate-700">
                      {check}
                    </div>
                  ))}
                </div>
              </section>

              {explanation.resolutionTips.length > 0 ? (
                <section className="rounded-2xl border border-[#d9dfd6] bg-white p-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#5f7d68]">Come si risolve di solito</p>
                  <div className="mt-4 space-y-3">
                    {explanation.resolutionTips.map((tip) => (
                      <div key={tip} className="rounded-2xl bg-amber-50/70 px-4 py-3 text-sm text-slate-700">
                        {tip}
                      </div>
                    ))}
                  </div>
                </section>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
