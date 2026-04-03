"use client";

import { useId, useState } from "react";

const SISTER_LOCKED_URL = "https://sister3.agenziaentrate.gov.it/Servizi/error_locked.jsp";
const SISTER_LOCKED_MESSAGE =
  "Utente SISTER bloccato sul portale Agenzia delle Entrate. Verificare se esiste gia' una sessione attiva su un'altra postazione o browser.";

type ElaborazioneOperationMessageProps = {
  value: string | null;
  className?: string;
};

export function ElaborazioneOperationMessage({ value, className }: ElaborazioneOperationMessageProps) {
  const [showDiagnostics, setShowDiagnostics] = useState(false);
  const diagnosticsId = useId();

  if (!value) {
    return <>—</>;
  }

  if (value.includes(SISTER_LOCKED_URL)) {
    return (
      <div className={className}>
        <span>{SISTER_LOCKED_MESSAGE} </span>
        <a className="text-[#1D4E35] underline" href={SISTER_LOCKED_URL} rel="noreferrer" target="_blank">
          Apri pagina di blocco
        </a>
        <div className="mt-2">
          <button
            aria-controls={diagnosticsId}
            aria-expanded={showDiagnostics}
            className="text-xs font-medium text-[#1D4E35] underline underline-offset-2 transition hover:text-[#143726]"
            onClick={() => setShowDiagnostics((current) => !current)}
            type="button"
          >
            {showDiagnostics ? "Nascondi diagnostica" : "Apri diagnostica"}
          </button>
        </div>
        {showDiagnostics ? (
          <div
            className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900"
            id={diagnosticsId}
          >
            <p>Il worker ha gia&apos; tentato il recovery automatico della sessione SISTER.</p>
            <p className="mt-1">
              Se il blocco persiste, chiudere eventuali sessioni aperte su altre postazioni o browser e poi usare
              Riprova.
            </p>
            <p className="mt-1">I dettagli tecnici restano nei log del worker e negli artifact di debug.</p>
          </div>
        ) : null}
      </div>
    );
  }

  return <span className={className}>{value}</span>;
}
