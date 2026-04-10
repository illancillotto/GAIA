# GAIA Elaborazioni

Area documentale dedicata al runtime operativo delle lavorazioni catastali.

Ambito runtime attuale:
- visure per immobile
- visure per soggetto PF/PNF
- gestione CAPTCHA
- report e artifact diagnostici batch/richiesta
- pool credenziali SISTER con profilo default per worker e test connessione
- diagnostica login Capacitas con dump HTML/metadata del tentativo quando il token SSO non viene estratto
- provider iniziale `Bonifica Oristanese` con pool credenziali cifrato, test login HTTP su `https://login.bonificaoristanese.it/login` e base sessione pronta per lo scraping autenticato

## Dashboard operativa

La pagina `/elaborazioni` usa una struttura a sezioni stabili:
- barra superiore con azioni rapide in linea
- colonna `Agenzia delle Entrate (SISTER)` per credenziali, visure, batch, documenti e CAPTCHA
- colonna `Capacitas` per pool account e monitor del servizio
- spazio predisposto per il provider `Bonifica Oristanese`, oggi limitato alla gestione credenziali e al test di autenticazione
- spazio riservato all'aggiunta futura di altri provider/processi senza rimescolare i flussi esistenti
- i workspace rapidi della dashboard si aprono in modale, con fallback a pagina completa quando serve approfondire o condividere il link
- anche i punti di uscita frequenti nei workspace interni (`archivio batch/documenti`, `Capacitas`) riusano il pattern modale per ridurre i salti di pagina
- i workspace principali (`nuova richiesta`, `archivio batch`, `dettaglio batch`, `Capacitas`) sono renderizzati nativamente in overlay React; l'`iframe` resta solo come fallback per percorsi non ancora convertiti
- anche `Credenziali` e il viewer dei documenti catastali sono ora componenti nativi riusabili, quindi l'overlay non dipende piu dall'`iframe` nei percorsi operativi principali del modulo
- nel workspace `Credenziali` i blocchi `SISTER` e `Capacitas` sono collassabili, cosi la modale puo comprimere i pannelli non necessari senza perdere il contesto operativo
- il workspace `Credenziali` gestisce ora piu credenziali SISTER per utente: ogni profilo puo essere attivo/disattivo, editabile e impostato come `default`; il worker usa il profilo default attivo, oppure il primo profilo attivo disponibile

## Struttura

- `docs/`: documentazione canonica del modulo `elaborazioni`
- `GAIA_VISURE_PROMPT_1_ANALISI.md`
- `GAIA_VISURE_PROMPT_2_IMPLEMENTAZIONE.md`
- `GAIA_VISURE_PROMPT_3_REVIEW.md`

## Nota operativa

I tre file `GAIA_VISURE_PROMPT_*` restano volutamente nella root di `domain-docs/elaborazioni/`:

- non sono ancora consolidati come documentazione canonica
- restano input di lavoro e implementazione ancora da completare
- non devono essere spostati o riscritti finché la relativa implementazione non è chiusa

La documentazione stabile del modulo vive invece in `domain-docs/elaborazioni/docs/`.
