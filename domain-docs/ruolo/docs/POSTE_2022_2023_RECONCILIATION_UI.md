# Riconciliazione assistita Poste 2022-2023

La pagina `/ruolo/raccomandate` mostra una coda di revisione per la campagna
storica Poste 2022/2023, delimitata agli invii creati prima del
`2026-09-29T00:00:00+02:00`. La coda usa l'anteprima read-only del Registro e
non cambia alcuna associazione senza conferma individuale dell'operatore.

L'operatore seleziona il file Excel con il foglio `Dati`. Il browser legge le
righe operative e calcola lo SHA-256 del file; il contenuto completo non viene
caricato sul server. Per una coppia proposta la schermata mostra i dati Poste,
la riga cumulativa trovata per codice fiscale e i due avvisi annuali. La riga
deve essere unica e contenere entrambi i riferimenti C/D. L'endpoint
`POST /ruolo/tributi/raccomandate/{mail_id}/reference-check` verifica in
lettura che i riferimenti esistano in inCASS e concordino per soggetto e codice
fiscale con gli avvisi candidati.

Solo dopo tale verifica e la spunta esplicita dell'operatore si puo associare
la coppia. Il `PATCH /association` ripete la verifica e controlla che gli
avvisi selezionati coincidano con i candidati salvati. Nel payload della
associazione manuale e nell'audit persistente del Registro restano hash del
file, foglio, numero di riga, riferimenti annuali, utente e timestamp.
L'hash e la riga sono dichiarati dal client: il server non riceve l'Excel e
non puo verificarne i byte. La verifica server-side riguarda i riferimenti
inCASS e la coppia di avvisi, non l'autenticita del foglio.

Il foglio non contiene un ID invio o tracking Poste: concordanza di nominativo
e codice fiscale non dimostra da sola il contenuto della busta. La conferma
richiede quindi una verifica operativa dell'invio. L'associazione crea le
posizioni cumulative nel Registro con stato notifica `da_verificare`; non
certifica la notifica perfezionata. I casi senza coppia univoca o senza
riscontro inCASS restano nella coda e non sono associati da questa schermata.

## Verifica e rilascio

Prima del rilascio: 45 test backend passati, 6 test PostgreSQL esclusi dalla
selezione mirata; coverage dei cinque file runtime backend modificati al 100%
statement e branch. I 25 test frontend mirati passano con 100% statement,
branch, funzioni e righe sui sei file runtime modificati. Typecheck, ESLint
mirato, Ruff e complexity ratchet contro `origin/main` passano senza finding.
Graphify aggiornato con i target `graphify-ruolo-code`, `graphify-frontend` e
`graphify-ruolo-docs`. Il rilascio applicativo non avvia il job Poste 9 e non
esegue riconciliazioni massive: ogni associazione resta una decisione
individuale. Al momento della verifica locale non sono state modificate le
151 associazioni presenti nell'audit del 2026-09-29.
