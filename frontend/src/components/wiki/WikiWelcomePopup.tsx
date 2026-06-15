"use client";

import { useEffect, useState } from "react";

const SESSION_KEY = "gaia.wiki_welcome_shown";
const PERSIST_KEY = "gaia.wiki_welcome_dismissed";

export function WikiWelcomePopup() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (localStorage.getItem(PERSIST_KEY) === "true") return;
    if (sessionStorage.getItem(SESSION_KEY) === "true") return;
    setVisible(true);
  }, []);

  function dismiss(permanent?: boolean) {
    sessionStorage.setItem(SESSION_KEY, "true");
    if (permanent) localStorage.setItem(PERSIST_KEY, "true");
    setVisible(false);
  }

  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-lg rounded-3xl bg-surface shadow-2xl overflow-hidden">
        {/* Header strip */}
        <div className="flex items-start gap-4 bg-[#e7f1ea] px-8 pb-6 pt-8">
          <div className="h-12 w-12 shrink-0 rounded-xl bg-[#d4e7da] flex items-center justify-center">
            <span className="material-symbols-outlined text-[#214534] text-2xl">menu_book</span>
          </div>
          <div>
            <p className="mb-1 text-[10px] font-label font-semibold uppercase tracking-[0.2em] text-[#426a57]">
              Novità disponibile
            </p>
            <h2 className="font-headline text-2xl font-bold leading-tight text-[#173627]">
              Assistente Wiki GAIA
            </h2>
          </div>
          <button
            type="button"
            onClick={() => dismiss()}
            aria-label="Chiudi"
            className="ml-auto text-[#426a57] transition-opacity hover:opacity-70"
          >
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        {/* Body */}
        <div className="px-8 py-6">
          <p className="text-on-surface-variant leading-relaxed text-sm mb-6">
            Il sistema mette a tua disposizione l&apos;assistente Wiki, accessibile in qualsiasi momento
            tramite l&apos;icona in basso a destra dello schermo. Puoi usarlo per:
          </p>

          <ul className="space-y-4 mb-8">
            <li className="flex items-start gap-3">
              <span className="material-symbols-outlined text-primary text-xl mt-0.5 shrink-0">help</span>
              <div>
                <p className="text-sm font-medium text-on-surface">Domande sui moduli e le procedure</p>
                <p className="text-xs text-outline leading-relaxed">
                  Chiedi all&apos;assistente come funzionano i flussi operativi, i moduli attivi e le funzionalità di GAIA.
                </p>
              </div>
            </li>
            <li className="flex items-start gap-3">
              <span className="material-symbols-outlined text-primary text-xl mt-0.5 shrink-0">add_circle</span>
              <div>
                <p className="text-sm font-medium text-on-surface">Richiesta di nuove funzionalità</p>
                <p className="text-xs text-outline leading-relaxed">
                  Hai bisogno di una funzione non ancora disponibile? Segnalala tramite la sezione Supporto della Wiki.
                </p>
              </div>
            </li>
            <li className="flex items-start gap-3">
              <span className="material-symbols-outlined text-primary text-xl mt-0.5 shrink-0">bug_report</span>
              <div>
                <p className="text-sm font-medium text-on-surface">Segnalazione di anomalie</p>
                <p className="text-xs text-outline leading-relaxed">
                  Riscontri un comportamento anomalo? Segnalalo direttamente dalla Wiki per la presa in carico.
                </p>
              </div>
            </li>
          </ul>

          {/* Actions */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => dismiss(true)}
              className="text-xs text-outline hover:text-on-surface transition-colors underline underline-offset-2"
            >
              Non mostrare più
            </button>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => dismiss()}
                className="px-5 py-2.5 rounded-lg text-sm font-medium text-on-surface-variant bg-surface-container hover:bg-surface-container-high transition-colors"
              >
                Chiudi
              </button>
              <button
                type="button"
                onClick={() => dismiss()}
                className="px-5 py-2.5 rounded-lg text-sm font-medium bg-primary text-on-primary hover:opacity-90 transition-opacity"
              >
                Procedi su GAIA
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
