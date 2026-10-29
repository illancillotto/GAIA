# Invio solleciti con Posta Online — 2026-10-28

## Regola

GAIA prepara le bozze di **Raccomandata A/R online** sul conto contrattuale del
Consorzio e poi registra quello che risulta spedito. **INVIA lo preme sempre
l'operatore, a mano, su Poste** (decisione dell'utente del 2026-10-28).

GAIA non chiama mai `inserisciInvii.do`, cioè l'INVIA di Poste:

- non esiste un job, una route o un permesso di invio;
- il worker blocca in rete `inserisciInvii`, `paga`, `carrello`,
  `cancellaArchivio`, `modifica.do` e `hideInvii` in ogni fase, compreso il login;
- c'è un test che lo verifica per ogni fase.

Il contratto `notice_dispatch_contract.py`, pensato per un invio automatico,
resta scollegato. Anche `require_poste_submission_adapter()` continua a
rifiutare ogni invio.

## Procedura operativa

1. Da **Tributi → Solleciti → Invio con Posta Online**
   (`/ruolo/tributi/solleciti/poste`) scegliere fino a 50 solleciti generati in
   PDF e creare il lotto. GAIA copia il PDF e prende il destinatario dallo
   stesso payload che ha prodotto la lettera: nominativo, indirizzo, CAP,
   comune e provincia.
2. **Verifica indirizzi.** Il worker interroga lo stradario Poste
   (`autocomplete.do`). Accetta un indirizzo solo se via, civico, comune, CAP e
   provincia coincidono con un'unica proposta. In tutti gli altri casi l'avviso
   va in «Indirizzo da rivedere», con le proposte di Poste. Lì l'operatore può
   correggere il destinatario (e GAIA riverifica) oppure usare l'indirizzo
   manuale, che richiede CAP e provincia.
3. **Crea bozze su Poste.** Per ogni avviso il worker:
   - compila «Crea spedizione» con nome `GAIA <numero avviso>`, il PDF, il modulo
     Raccomandata A/R e un solo destinatario;
   - salva lo stato `draft_creating` prima di premere CONTINUA;
   - controlla la bozza in «Verifica e invia».

   Dopo 45 secondi rilegge prezzi e stati. Due bozze fallite di seguito fermano
   il lotto.
4. L'operatore apre **Verifica e invia** su Posta Online e controlla anteprime,
   destinatari e prezzi. Se tutto è corretto preme **INVIA**.
5. **Controlla Poste.** Il worker rilegge «Verifica e invia» e l'archivio. Per
   ogni bozza che non è più in «Verifica e invia»:
   - **la trova in archivio con il nome GAIA** (una sola spedizione): scarica il
     dettaglio, lo importa tra le raccomandate (`RuoloTributiRegisteredMail`),
     segna l'avviso «Spedito» con il numero di raccomandata e registra un
     tentativo di notifica (`NoticeAttempt`) nel Registro avvisi;
   - **non la trova nell'archivio letto per intero**: l'avviso diventa «Bozza
     scaduta o eliminata» e si può ricreare;
   - **trova più spedizioni con lo stesso nome**: segnala l'anomalia e non
     cambia stato;
   - **non riesce a leggere tutto l'archivio**: non conclude nulla.
6. **Annulla** su un avviso con bozza su Poste richiede l'eliminazione. **Elimina
   bozze annullate** la cancella con l'azione di quella riga (`DeleteInvio(id)`),
   mai con la selezione multipla condivisa del portale, e verifica che sia
   sparita.

La pagina avvisa se in «Verifica e invia» ci sono **bozze che non fanno parte
del lotto**: non è verificato se INVIA spedisca tutte le bozze presenti o solo
quelle selezionate. Segnala anche **bozze doppie**, cioè con lo stesso nome. Le
bozze scadono su Poste dopo 7 giorni, e la pagina mostra la prima scadenza.

## Stati dell'avviso nel lotto

| Stato | Significato | Uscite |
| --- | --- | --- |
| `address_pending` | da verificare nello stradario | `address_ok`, `address_review` |
| `address_review` | indirizzo da rivedere | correzione → `address_pending`; manuale → `address_ok` |
| `address_ok` | pronto per la bozza | `draft_creating`, `draft_error` |
| `draft_creating` | CONTINUA in corso (salvato prima del clic) | `draft_created`, `draft_priced`, `draft_uncertain` |
| `draft_created` / `draft_priced` | bozza su Poste, in lavorazione o prezzata | `sent`, `draft_missing`, `cancel_requested` |
| `draft_uncertain` | CONTINUA premuto senza bozza visibile | riconciliazione |
| `draft_error` | modulo fallito prima di CONTINUA: nessuna bozza | nuova creazione |
| `draft_missing` | bozza scaduta o eliminata, non spedita | nuova creazione |
| `cancel_requested` | annullato con bozza da eliminare | `cancelled` o `sent` |
| `cancelled` / `sent` | stati finali | — |

Ci sono due vincoli di unicità su `active_key` (nome spedizione) e su
`active_source_key` (sollecito). Un sollecito sta in un solo lotto attivo, e un
sollecito spedito non si può rimettere in un lotto. L'annullamento libera il
sollecito. Il PDF copiato viene cancellato alla spedizione o all'annullamento;
resta il suo SHA-256. Prima del caricamento GAIA ricalcola l'hash: un PDF
alterato non viene caricato.

## Componenti

- Backend `backend/app/modules/ruolo/`:
  - `poste_dispatch_models.py`: lotti, avvisi, eventi append-only; migration
    `20261028_1500`;
  - `poste_dispatch_schemas.py`, `routes/poste_dispatch_routes.py`;
  - `services/poste_dispatch.py`: comandi dell'operatore;
  - `services/poste_dispatch_state.py`: transizioni e audit;
  - `services/poste_dispatch_work.py`: esiti riportati dal worker;
  - `services/poste_dispatch_reconcile.py`: archivio e Registro;
  - `services/poste_dispatch_recipient.py`, `services/poste_dispatch_address.py`;
  - `services/poste_dispatch_views.py`.
- API `/ruolo/tributi/poste-dispatch`. La lettura richiede `ruolo.tributi.view`;
  i comandi richiedono `ruolo.tributi.manage_status`, lo stesso permesso di
  conferma ed export:

  | Metodo | Percorso | Uso |
  | --- | --- | --- |
  | GET | `/candidates` | solleciti generati in PDF e non in un lotto attivo |
  | GET, POST | `/lots` | elenco dei lotti, creazione |
  | GET | `/lots/{id}` | dettaglio del lotto |
  | POST | `/lots/{id}/jobs` | operazioni sul portale: `addresses`, `drafts`, `reconcile`, `delete` |
  | PUT | `/lots/{id}/items/{item}/recipient` | correzione del destinatario |
  | POST | `/lots/{id}/items/{item}/manual-address` | indirizzo manuale |
  | POST | `/lots/{id}/items/{item}/cancel` | annullamento |
  | GET | `/lots/{id}/items/{item}/document` | PDF copiato nel lotto |
- Worker `modules/elaborazioni/worker/`:
  - `posta_online_dispatch_portal.py`: guardia di rete e parsing;
  - `posta_online_dispatch.py`: azioni del browser;
  - `posta_online_dispatch_runner.py`: i quattro job.

  I job usano la coda esistente `posta_online_registered_mail_sync_jobs` con
  le modalità `poste_dispatch_*`, smistate da `posta_online_sync._job_runner`.
  Restano quindi un solo worker Poste, una credenziale alla volta e le fasce
  orarie. Si può avere un solo job attivo per lotto. Un job interrotto viene
  ripreso dal recovery esistente: rilegge «Verifica e invia» prima di agire e
  non ripete CONTINUA sugli avvisi in `draft_creating`.
- Frontend:
  - pagina `src/app/ruolo/tributi/solleciti/poste/page.tsx`;
  - componenti in `src/components/ruolo/poste-dispatch/`;
  - client `src/lib/ruolo-poste-dispatch-api.ts`;
  - link dalla pagina Solleciti.

## Scelte predefinite e limiti

- **Codice fiscale non compilato.** GAIA non usa ritiro digitale né avviso di
  ricevimento digitale.
- **Opzioni di stampa del portale.** Colore e fronte/retro restano quelli
  predefiniti di Poste: vanno controllati nell'anteprima e nel prezzo prima di
  INVIA. Il lotto lo registra in `postal_options.portal_defaults`.
- **Bollettino TD 896.** Resta da avere da Poste la conferma che accetta il
  bollettino stampato da loro, ed eventualmente a colori.
- **Solo lotti generati.** Entrano solo i solleciti dei lotti «generated» con
  PDF definitivo, che sono quelli usati in produzione. Le bozze private
  2022/2023 confermate passano ancora dall'export ZIP: il manifest dell'export
  dichiara `authorizes_dispatch: false`.
- **Limiti di Poste.** PDF fino a 7 MB, un destinatario per bozza, nome
  spedizione `GAIA <numero avviso>` di massimo 40 caratteri.
- **Collaudato sul portale reale:**
  - creazione ed eliminazione di una bozza con indirizzo dello stradario
    (bozza 12269236, prova del 2026-10-28);
  - lettura dell'archivio e del dettaglio.
- **Non ancora collaudato sul portale reale:**
  - l'**indirizzo manuale**, con i selettori presi dagli script del portale;
  - la cancellazione con `DeleteInvio(id)`.

  Il primo lotto va seguito sul portale.
- **Prima di usare il primo lotto vero.** L'operatore verifica con due bozze di
  prova se INVIA spedisce tutto «Verifica e invia» o solo le bozze selezionate.
- **Rilasciato sul CED il 2026-10-29** (release
  `poste-dispatch-20261029-05fa4a86`, database a `20261028_1500`).
  - Backend, frontend e worker Poste sono stati rilasciati insieme, perché il
    worker precedente non riconosceva i job `poste_dispatch_*`.
  - Il worker usa lo stesso `app/` del backend.
  - Verifiche, ripristino e vincoli sono in `PROGRESS_ruolo.md`, alla voce
    del 2026-10-28.

## Verifiche

- **Backend.** Test in `backend/tests/ruolo/test_poste_dispatch_*.py`:
  servizi, transizioni, riconciliazione reale con il Registro (tentativo e
  tracking), API, permessi, migration up/down. È incluso il caso che ha trovato
  un difetto: un `ValueError` del Registro interrompeva la riconciliazione, e
  ora viene riportato sull'avviso.
- **Worker.** Test in `tests/test_posta_online_dispatch*.py`:
  - guardia per ogni fase;
  - parsing della pagina reale di «Verifica e invia»;
  - azioni del browser con pagina finta;
  - runner: creazione unica, esito incerto, fermata dopo due errori, archivio
    incompleto, cancellazione.
- **Frontend.** `tests/unit/ruolo-poste-dispatch-*.test.ts(x)` e il link nel
  test della pagina Solleciti.
- **Coverage e complessità.** Il 100% su runtime nuovi e modificati e i
  risultati dei gate sono riportati in `PROGRESS_ruolo.md`, alla voce del
  2026-10-28.
