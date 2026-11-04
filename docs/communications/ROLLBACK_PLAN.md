# Rollback e ripristino

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
