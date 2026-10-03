"use client";

import { usePathname } from "next/navigation";
import type { PropsWithChildren } from "react";

const platformGuides = [
  {
    title: "Windows",
    steps: [
      "Chiedi al CED il pacchetto della nuova CA GAIA e la sua impronta SHA-256, comunicata tramite un canale separato.",
      "Usa l’EXE amd64 sui PC Intel/AMD oppure arm64 sui PC Windows ARM. Avvialo, autorizza la richiesta di amministratore e conferma solo se l’impronta coincide.",
      "Chiudi e riapri Edge o Chrome. Se SmartScreen o una policy bloccano il file, contatta il CED: non disattivare le protezioni.",
    ],
  },
  {
    title: "macOS",
    steps: [
      "Richiedi al CED il pacchetto approvato della nuova CA GAIA e l’impronta SHA-256. Estrai tutta la cartella.",
      "Apri Installa-CA-macOS.command per verificare il certificato. Il doppio clic verifica soltanto: per installare nel portachiavi Sistema segui le istruzioni CED con un account amministratore, oppure usa il profilo MDM aziendale.",
      "Confronta l’impronta prima dell’installazione, poi chiudi e riapri Safari o Chrome. Non modificare le impostazioni di sicurezza per aggirare un blocco.",
    ],
  },
  {
    title: "Linux",
    steps: [
      "Richiedi al CED il pacchetto approvato della nuova CA GAIA e l’impronta SHA-256. Estrai tutta la cartella.",
      "Esegui bash installa-ca-linux.sh --verify. Per installare, confronta l’impronta e segui il comando sudo riportato nelle istruzioni CED.",
      "Sono supportati Debian/Ubuntu e RHEL/Fedora con i rispettivi strumenti di gestione certificati. Riavvia il browser; per altre distribuzioni chiedi al CED.",
    ],
  },
];

export function HttpsAccessGuide({ children }: PropsWithChildren) {
  const pathname = usePathname();
  if (pathname !== "/" && pathname !== "/login") return <>{children}</>;

  return (
    <>
      {children}
      <section aria-label="Guida accesso HTTPS" className="mx-auto mb-8 w-full max-w-5xl px-4 sm:px-6">
        <details className="rounded-2xl border border-outline-variant/30 bg-surface-container-low p-5 sm:p-6">
          <summary className="cursor-pointer font-semibold text-primary">
            Accedere a GAIA in HTTPS · Windows, macOS e Linux
          </summary>
          <div className="mt-5 space-y-6 text-sm leading-relaxed text-on-surface">
            <div role="note" className="rounded-xl border border-outline-variant/30 bg-surface p-4">
              <h2 className="font-semibold">Attivazione HTTPS in preparazione</h2>
              <p className="mt-2">La nuova CA GAIA deve essere creata e approvata dal CED. I precedenti pacchetti con la CA Kiosk sono sospesi: non installarli. Nessun download è disponibile in questa guida.</p>
              <p className="mt-2">L’indirizzo interno previsto è <code>https://gaia.lan</code>. Usalo per accedere solo dopo la conferma del CED che certificato, rete e servizio HTTPS sono attivi.</p>
            </div>
            <div>
              <h2 className="font-semibold">Prima di iniziare</h2>
              <p className="mt-2">Collegati alla rete aziendale o alla VPN autorizzata. Ricevi il pacchetto dal CED: questa guida non ti chiede password di amministratore, chiavi private o passphrase della CA.</p>
            </div>
            <div className="grid gap-5 lg:grid-cols-3">
              {platformGuides.map((platform) => (
                <article key={platform.title} className="rounded-xl bg-surface p-4">
                  <h3 className="text-base font-semibold">{platform.title}</h3>
                  <ol className="mt-3 list-decimal space-y-3 pl-5">
                    {platform.steps.map((step) => <li key={step}>{step}</li>)}
                  </ol>
                </article>
              ))}
            </div>
            <div>
              <h2 className="font-semibold">Accedi e verifica la connessione</h2>
              <p className="mt-2">Dopo l’attivazione apri <code>https://gaia.lan/login</code>, verifica nelle informazioni del sito che la connessione sia sicura e inserisci le normali credenziali GAIA. Aggiorna il preferito: le sessioni HTTP e HTTPS sono separate, quindi può essere necessario un nuovo login.</p>
              <p className="mt-2">Se compare un avviso di certificato, non scegliere «Procedi comunque» e non inserire credenziali. Contatta il CED indicando sistema operativo, browser, indirizzo e messaggio di errore, senza inviare password o token.</p>
              <p className="mt-2">Se il nome non viene risolto, verifica rete/VPN con il CED: installare la CA non configura il DNS. Firefox e alcune applicazioni usano archivi certificati separati: serve la policy aziendale. Non rimuovere la CA Kiosk.</p>
            </div>
          </div>
        </details>
      </section>
    </>
  );
}
