# Riferimenti Poste Italiane per bollettini TD 896

Questa directory conserva le fonti usate per implementare e verificare i
bollettini postali `TD 896` generati da GAIA.

## Documenti

### Caratteristiche del bollettino

- File:
  [`poste-caratteristiche-bollettino-edizione-2020.pdf`](poste-caratteristiche-bollettino-edizione-2020.pdf)
- Edizione: 2020
- Pagine: 68
- SHA-256: `bb891f690a17b67ac9f1ac777a407147a8bd8258003ee8c9548c10301058b145`
- Contenuti rilevanti: modello CH8, codeline, codice cliente di 18 cifre,
  controcodice modulo 93, Code 128 tipo C, Data Matrix e dimensioni del
  bollettino `TD 896`.

Per il codice cliente, il documento riserva le prime 16 cifre al correntista e
impone nelle ultime due il resto della divisione delle prime 16 per 93. La
conformita e l'univocita riguardano il codice completo: le cifre finali di
controllo possono ripetersi tra avvisi diversi e non devono essere usate da sole
come identificativo.

### Autorizzazione generale alla stampa in proprio

- File:
  [`poste-manuale-autorizzazione-generale-stampa-in-proprio-edizione-2018.pdf`](poste-manuale-autorizzazione-generale-stampa-in-proprio-edizione-2018.pdf)
- Edizione: novembre 2018
- Pagine: 7
- SHA-256: `8c790bcbc3a04b50c315db8940918dd9d6dd5f0d49b2add16058d92e5f0488df`
- Contenuti rilevanti: richiesta dell'autorizzazione, stampa massiva cartacea o
  PDF e indicazioni operative per il servizio.

## Nota operativa

Queste copie documentano le fonti consultate durante lo sviluppo. Prima di una
nuova omologazione o di modifiche al formato di stampa, verificare con Poste
Italiane l'eventuale disponibilita di revisioni successive.
