# Rollback e ripristino

## Cancellazione template — rilascio 7 novembre 2026

Rollback software in `/opt/gaia/releases/template-delete-20261107`:
`backend.rollback.json` e `frontend.rollback.json`, soltanto se i servizi sono
ancora sulle immagini `b259894c1ad4` e `bf73b599a3e8`. Ripristinare i soli
servizi omonimi con `--no-deps --no-build --pull never`, verificare health,
quindi `nginx -t` e reload. Preservare eventuali rilasci successivi.
Non modificare worker, schema o righe template; le cancellazioni degli
operatori restano auditabili e non vanno annullate tramite restore DB.
Dettagli: [TEMPLATE_DELETION_RELEASE_2026-11-07.md](TEMPLATE_DELETION_RELEASE_2026-11-07.md).

## Piano iniziale della piattaforma

Pausa globale, trasporto false, arresto cooperativo worker. Registrare job attivi
e Message-ID; un SMTP già accettato non può essere richiamato con rollback.

Preferire ritiro frontend/worker lasciando tabelle, trigger e prenotazioni.
Preservare snapshot, MIME/EML, autorizzazioni, eventi e Registro. Non eseguire
downgrade su dati popolati: distrugge archivio e coordinamento fra canali.

Roundtrip upgrade/downgrade/upgrade testato soltanto su schema PostgreSQL
isolato senza evidenze reali. Non autorizza perdita di dati in produzione.
Con una release precedente impedire nuove prenotazioni Poste sugli avvisi
coinvolti fino alla riconciliazione.

Restore consistente dell'intero DB (Registro incluso); trust e secret separati.
Trasporto false dopo restore: il backup potrebbe precedere un SMTP già accettato.
Job sending o potenzialmente trasmessi richiedono riconciliazione/manual review
prima di riprendere. Mai replay automatico dal backup.

Verificare conteggi/hash di allegati, MIME/EML, autorizzazioni, eventi e active_key.
Il ripristino non cambia gli effetti giuridici: valutazione dell'ufficio competente.

## Artefatti del rilascio autorizzato del 4 novembre

Nel CED la directory protetta
`/opt/gaia/releases/communications-20261104-1d26140c` contiene `rollback.json`
e la configurazione precedente. L'immagine backend di rollback conserva il
codice applicativo precedente e aggiunge soltanto il file della revisione
Alembic `20261103_1200`: il bootstrap precedente riconosce così la nuova head
senza eseguire downgrade. Il frontend torna all'immagine precedente effettiva.

Fermare soltanto `communications-worker`; applicare `rollback.json` ai soli
servizi backend/frontend con `up -d --no-deps --no-build`, quindi verificare
health e ricaricare nginx dopo `nginx -t`. Non usare `down` o riavvii globali,
non riattivare Poste e non eliminare dati Communications.
La verifica realmente eseguita degli artefatti e lo stato operativo sono nel
[report del rilascio](DEPLOYMENT_REPORT_2026-11-04.md).

## Registro contatti — addendum 04/11/2026

La migrazione predisposta `20261104_1400` non modifica i campi legacy. Il downgrade
elimina però il registro tipizzato e può riattivare i vecchi fallback: non usarlo
come rollback ordinario. Disabilitare trasporti, conservare prima esportazione e
audit, coordinare la versione backend/worker e verificare la revisione documentale.
L'audit `electronic_contact_classified` resta tracciato; non cancellarlo per
simulare che le classificazioni non siano avvenute. Nessun downgrade eseguito.

## Registro recapiti 05/11/2026

Rollback applicativo tramite configurazione congelata della release CED
`communications-contacts-20261105-2`, limitato a backend e worker Communications.
Preservare migrazione additiva, 256 classificazioni/quarantene e audit; nessun
downgrade distruttivo o restore globale per annullare il solo codice.
Verificare assenza di release concorrenti e health, quindi ricaricare nginx.
Backup, checksum e dettagli: [CONTACT_RELEASE_2026-11-05](CONTACT_RELEASE_2026-11-05.md).
