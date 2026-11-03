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
