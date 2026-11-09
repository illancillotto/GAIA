# PEC ed email per aziende e persone fisiche — 4 novembre 2026

> Stato successivo: registro recapiti pubblicato il 5 novembre 2026, liste PEC 47 / email 1. Vedere [CONTACT_RELEASE_2026-11-05](CONTACT_RELEASE_2026-11-05.md). Le indicazioni «non rilasciato» sotto descrivono il 4 novembre.

## Stato reale

Implementazione nel checkout, non rilasciata. Migrazione e classificazioni proposte
non applicate in produzione. L'importazione dei 158 recapiti nel campo email
eseguita precedentemente resta distinta: questo intervento non modifica quei dati,
i 14 discordanti, le posizioni tributarie o le evidenze inCASS. Nessun invio.

## Problema e soluzione

La selezione originaria usava `ana_companies.email_pec` per PEC e
`ana_persons.email` per email. Le persone fisiche con PEC erano escluse dalla
scheda PEC; importazioni storiche possono avere mescolato i canali nei due campi.

Il registro `ana_electronic_contacts`, nel dominio Utenze, collega ogni indirizzo
all'`ana_subjects.id` esistente: non crea un'altra anagrafica. Tipi: `pec`, `email`,
`unclassified`. Stati: `active`, `review`, `revoked`. Provenienza, riferimento della
verifica, versione, operatore e audit permettono di ricostruire la classificazione.
Il tipo è una classificazione amministrativa documentata, non una prova automatica
di titolarità, raggiungibilità della casella o validità della notifica.

`contact_columns` / `contact_values` forniscono la stessa selezione a elenco,
filtri server-side e fingerprint della bozza. Entrambi i canali sono disponibili
per entrambi i tipi di soggetto. Un unico indirizzo attivo del canale viene
proposto; più indirizzi attivi danno esito ambiguo, senza scelta arbitraria.
Un indirizzo in revisione, non classificato o revocato non viene selezionato.

Per compatibilità, il vecchio campo è utilizzato finché non è presente una
classificazione per quell'indirizzo o per quel canale. Una classificazione PEC
impedisce che il medesimo valore legacy della persona venga proposto come email.
La compatibilità **non certifica** il tipo del dato storico: la migrazione da sola
non risolve la qualità dei dati. È necessario applicare il piano di classificazione
validato prima di usare le nuove liste in produzione.

Il compositore conserva la possibilità esistente di indicare un recapito manuale,
con checklist e autorizzazione individuali. Questo intervento riguarda la selezione
da anagrafica; non introduce verifica del possesso di una casella. La variazione
del recapito risolto invalida il fingerprint della precedente autorizzazione.

## API amministrative

Nel namespace Communications esistente, con amministratore attivo, modulo Ruolo
e sezione `ruolo.tributi.view`:

- `GET /communications/admin/subjects/{subject_id}/contacts`: recapiti registrati
  e indirizzi risolti per i due canali; nessuna attività di rete.
- `PUT /communications/admin/subjects/{subject_id}/contacts`: classificazione
  versionata di un indirizzo. `expected_version=0` crea, il valore corrente modifica.
  Versione errata o anagrafica inattiva: 409; anagrafica inesistente: 404;
  payload invalido: 422. Un semplice compositore non può classificare.

Payload sintetico:

```json
{
  "address": "destinatario@example.org",
  "channel": "pec",
  "state": "active",
  "source": "verifica_ufficio",
  "evidence_reference": "Riferimento alla verifica del recapito e del canale",
  "expected_version": 0
}
```

Non usare il dominio come unica prova. La funzione pura `contact_assessment.assess`
accetta soltanto il tipo esplicito `PEC`/`EMAIL` delle fonti archiviate, normalizzato
per spazi e maiuscole. Richiede attività documentata; revoca prevalente, fonte non
attiva o tipo contraddittorio impediscono l'attivazione automatica. Nessuna verifica
SMTP, invio di prova o interrogazione di elenchi esterni è stata effettuata.

## Migrazione e concorrenza

`20261104_1400_electronic_contacts.py`, parent `20261103_1200`, crea esclusivamente
la tabella, FK, unicità soggetto/indirizzo e check su tipo, stato e versione.
Nessun backfill automatico. La registrazione ORM è in `app/db/base.py`.

Su PostgreSQL installa i trigger `gaia_notice_revision_row` e
`gaia_notice_revision_truncate`, entrambi ENABLE ALWAYS, riusando la funzione di
revisione esistente. I cambi di classificazione partecipano al fence dei documenti.
La scrittura serializza sull'anagrafica con `FOR UPDATE`, verifica la versione e
registra `electronic_contact_classified` nell'audit nella stessa transazione.

Il downgrade elimina i recapiti classificati: esportarli prima e preservare
l'audit. Non applicare un downgrade come semplice rollback del frontend. Non
rilasciare il nuovo codice senza la tabella: i processi web e worker che usano
il resolver richiedono lo stesso schema.

## Verifica reale dei dati 2021

Snapshot in sola lettura del database CED, 04/11/2026, e file
`Avvisi_2021_residuo_oltre_30_ver.01_con_pec.xlsx`, SHA-256
`466db773a49346c6baa5c1122adc20b5d9306effab084bb7d021b99d4183cca3`.
Il perimetro sono i lotti con `years_json=[2021]`, non l'intero archivio fiscale:

- 1.151 righe di lotto, 1.008 numeri avviso distinti: i lotti contengono ripetizioni.
- 984 anagrafiche collegate: 931 persone fisiche, 53 aziende; una riga senza legame.
- 256 recapiti distinti per anagrafica, includendo quelli delle fonti archiviate.
- 738 anagrafiche senza alcun recapito nel perimetro consultato.
- 41 PEC con tipo e attività documentati, non sospese per i discordanti Excel:
  29 persone fisiche e 12 aziende. Non sono 41 spedizioni automaticamente autorizzate.
- Una email con tipo e attività documentati, non sospesa per discordanza.
- 11 PEC e 7 email da rivedere; una PEC revocata.
- 195 recapiti non classificati/in revisione, incluso un indirizzo sintatticamente
  invalido. I 14 soggetti discordanti restano da verificare dai colleghi; il report
  distingue stato della fonte e stato proposto, senza nascondere le revoche.

Il confronto con tutte le 942 righe avviso dell'Excel trova 940 corrispondenze
contemporanee CF/numero; due restano senza corrispondenza. I 224 recapiti compilati
sono tutti collegati. Una verifica della sintassi o del tipo nella fonte non
certifica l'esistenza attuale della casella.

Report privato, non versionato perché contiene dati personali:
`/home/cbo/Desktop/2021/Verifica_PEC_Email_GAIA_2021_20261104_134636.xlsx`.
Include riepilogo, recapiti, casi da verificare, soggetti senza recapito, avviso
senza anagrafica e confronto delle 942 righe Excel. Il piano JSON per il registro
è conservato in `/tmp/gaia-contact-classification-20261104/classification-plan.json`;
non è stato eseguito. Riacquisire i dati prima di applicarlo, per evitare di usare
uno snapshot superato. Un indirizzo invalido non viene proposto per l'importazione.

## Matrice comportamento → test

| Comportamento | Verifica |
| --- | --- |
| PEC/email per persone e aziende, valori e filtro coerenti | `test_both_channels_for_both_subject_types_and_filters`, quattro combinazioni |
| Compatibilità legacy, separazione dei canali | `test_legacy_fields_preserved_until_classified` |
| Revocati, sconosciuti, sospesi esclusi; nessun fallback improprio | `test_revoked_unknown_and_pending_do_not_fall_back_to_legacy` |
| Due indirizzi attivi richiedono revisione | `test_multiple_addresses_require_review_and_can_be_resolved` |
| Validazione sintassi, header injection, tipo, fonte, versione | `test_invalid_classification_rejected_without_writes` |
| RBAC admin/modulo/sezione, utente inattivo | `test_classification_is_admin_only` |
| Identità inesistente/inattiva, replay e versione obsoleta; errore DB non esposto | `test_missing_inactive_replay_stale_and_database_error` |
| Variazione recapito blocca l'autorizzazione precedente | `test_contact_change_invalidates_prior_authorization` |
| Tipi espliciti, revoche, inattività, conflitti; nessuna inferenza dal dominio | `test_assessment_uses_explicit_type_and_activity`, `test_assessment_never_guesses_from_domain_or_uses_unrelated_contacts` |
| Registrazione ORM, unicità, FK e check | `test_schema_registration_and_database_constraints` |
| Migrazione senza classificazioni implicite e downgrade SQLite | `test_migration_roundtrip_no_automatic_classification` |
| PostgreSQL reale: schema uguale al modello, due scrittori, revisione e revoca | `test_typed_contact_migration_concurrency_and_revision` |

## Collaudo e quality gate

Suite Communications: **169 PASS, zero skip**, di cui nove prove PostgreSQL su
database locale isolato `communications_test`. Dati di test sintetici; nessuna
connessione ai provider. Coverage integrale dei nove file runtime/migrazione
nuovi o modificati: **407 statement e 72 branch, 100%**. Nessuna esclusione nuova.
Ruff e formato dei file nuovi PASS. Due warning `runpy` preesistenti nella suite.

Regressione anagrafica/parser inCASS/revisione avvisi: **193 PASS distinti, zero
skip nella verifica completata**. La prima corsa senza `GAIA_TEST_POSTGRES_URL`
aveva 69 PASS e 124 SKIP. Configurato poi il medesimo PostgreSQL locale isolato,
la suite revisione avvisi ha eseguito tutti i 125 test senza skip (uno già passato
prima), con JUnit: zero errori/failure, 162,717 secondi. Le nove prove PG
Communications restano distinte da questa regressione. Frontend,
build e E2E browser non modificati né rieseguiti in questa change backend.

Metriche sui callable preesistenti: nessun incremento rispetto ai sorgenti
all'inizio del lavoro. `ruolo_source`: Cyc 100→95, Cog 110→105, LOC 288→284;
admin: Cyc 18→18, Cog 3→3; due righe aggiunte per l'integrazione del router.
Nessuna nuova violation error-level nei file nuovi.

Rettifica della diagnosi del ratchet durante la verifica preview: i sette finding
in `_document` e `_positions` provengono dalla scansione limitata a un sottoinsieme
di file. La scansione completa autorevole `complexity.py ratchet --base-ref
origin/main`, ripetuta sul checkout iniziale `2115dd7b` e sul working tree, passa
con zero finding. I log limitati restano nelle evidenze, ma non descrivono un
blocco del ratchet completo. Nessun deploy del registro contatti è stato eseguito.

Evidenze locali: `/tmp/gaia-contact-classification-20261104/`, inclusi log dei
primi tentativi e correzioni (FROM SQL esplicito e permessi modulo/sezione).
Graphify codice backend/Utenze aggiornato con i target Make dedicati; artefatti
non versionati. Primo aggiornamento docs completo (`chunk 1/1 done`), 13.882 token
in ingresso e 2.204 in uscita, costo stimato $0,0091. Refresh finale dopo la chiusura
della regressione documentato nelle evidenze locali.

## Residui prima della produzione

1. Completare il pacchetto di rilascio del registro e la verifica della baseline;
   usare il ratchet completo, evitando il confronto con un corpus incompleto.
2. Rilasciare codice e migrazione in una finestra coordinata per backend/worker,
   con backup e trasporti disabilitati, quindi applicare il piano riacquisito.
3. Riesaminare i 14 discordanti, revoche, indirizzo invalido, due avvisi Excel
   senza corrispondenza e anagrafica non collegata; nessuna correzione implicita.
4. Classificare tramite fonte o verifica operatore i recapiti sconosciuti.
   Il dominio non basta; non spostare automaticamente le 158 email importate in PEC.
5. L'automazione dei sync legacy verso il nuovo registro e una UI di gestione
   della classificazione in Utenze restano evoluzioni: l'API admin è funzionante,
   ma questo intervento non dichiara implementate quelle superfici aggiuntive.
