"use client";

import { useState } from "react";
import type { RegisterEligibility } from "@/types/notice-register";
import { panelClass, ReadState } from "./presentation";
import { useRegisterResource } from "./use-register-resource";

const REASONS: Record<string, string> = {
  posizioni_assenti: "Mancano le posizioni annuali.",
  documento_riconciliato: "Scheda riconciliata: consultare la destinazione.",
  collegamenti_mancanti: "Collegamenti agli avvisi incompleti.",
  annualita_discordante: "Annualita del registro e dell'avviso discordanti.",
  destinatario_discordante: "Codice fiscale del documento discordante.",
  destinatario_non_verificato: "Codice fiscale non verificato.",
  storico_non_verificato: "Manca uno storico collegato e verificato.",
  storici_da_collegare: "Altri documenti dello stesso CF sono ancora da collegare.",
  step_non_liberato: "Affidamento STEP presente o da verificare.",
  saldo_non_verificato: "Saldo non verificato.",
  saldo_non_esigibile: "Saldo non positivo o stato contabile non ammissibile.",
  gestione_esterna: "Annualita in gestione esterna.",
  generazione_non_abilitata: "Generazione non abilitata dalle regole correnti: verificare anche le politiche di calcolo.",
  posizione_bloccata: "Posizione sospesa, contestata o annullata.",
  invio_incass_da_riconciliare: "Invio inCASS da riconciliare.",
  poste_da_importare: "Raccomandata Poste non ancora importata nel registro.",
  invii_non_chiariti: "Tentativi presenti senza valutazione documentata dell'esito.",
  notifica_perfezionata: "Notifica gia perfezionata.",
  notifica_invio_in_corso: "Invio in corso.",
  notifica_da_verificare: "Notifica da verificare.",
};

function EligibilityResult({ token, documentId, revision }: { token: string; documentId: string; revision: number }) {
  const resource = useRegisterResource<RegisterEligibility>(token, `/${documentId}/ammissibilita`, revision);
  return <div className="space-y-3">
    <ReadState loading={resource.loading} error={resource.error} />
    {resource.data && <>
      <p className="font-semibold">{resource.data.eligible ? "Nessun blocco rilevato nella verifica corrente." : "Sono presenti blocchi o verifiche mancanti."}</p>
      <p className="text-xs text-gray-600">Verificato: {resource.data.checked_at} | Versione documento: {resource.data.version}</p>
      <ul className="list-disc space-y-1 pl-5">{resource.data.reasons.map((reason) => <li key={reason}>{REASONS[reason] ?? reason}</li>)}</ul>
      {resource.data.positions.map((position) => <article key={position.position_id} className="rounded-lg border p-3">
        <p className="font-medium">Annualita {position.tax_year}: {position.eligible ? "nessun blocco rilevato" : "da verificare"}</p>
        <ul className="list-disc pl-5">{position.reasons.map((reason) => <li key={reason}>{REASONS[reason] ?? reason}</li>)}</ul>
      </article>)}
    </>}
  </div>;
}

export function EligibilityPanel({ token, documentId }: { token: string; documentId: string }) {
  const [revision, setRevision] = useState(0);
  return <section aria-label="Verifica ammissibilita" className={`${panelClass} space-y-3`}>
    <h3 className="text-lg font-semibold">Verifica ammissibilita</h3>
    <p className="text-sm">Controlla saldo, storico, notifica, STEP e collegamenti. Il risultato e consultivo: non prenota e non autorizza un invio. I dati possono cambiare dopo la verifica.</p>
    <button className="btn-secondary" onClick={() => setRevision((value) => value + 1)}>Verifica dati aggiornati</button>
    {revision > 0 && <EligibilityResult token={token} documentId={documentId} revision={revision} />}
  </section>;
}
