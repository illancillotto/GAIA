# Pagina Visure Elaborazioni

## Scopo

La pagina `/elaborazioni/visure` consente consultazione stato visure, esiti, scarti, retry e artefatti prodotti.
In `Scelta del flusso` l'ordine delle modalità è `AutoSync a ruolo`, `Batch recenti`, `Import batch`, `Visura singola`.

## Navigazione dettaglio

L'azione `Apri` nella tabella dei batch recenti apre il dettaglio batch in modale workspace, senza uscire da `/elaborazioni/visure`.
La modale mantiene il contesto operativo della pagina e offre comunque il fallback `Apri pagina` per aprire il dettaglio completo in una nuova tab.

## Cosa puo fare l'operatore

- leggere stato di una visura singola o batch
- interpretare esiti e scarti
- capire se serve retry o intervento
- trovare artefatti generati dal job
- aprire il dettaglio batch in modale restando nella pagina visure

## Dati utili

- ID visura o batch
- stato job (in corso, errore, completato)
- tipo visura

## CAPTCHA SISTER via Agent

Il worker visure puo risolvere i CAPTCHA SISTER tramite Cursor Agent in modalita headless.
La configurazione runtime e server-specifica:

- `CAPTCHA_AGENT_HOME`: home host montata nel container, es. `/home/ced` su server CED.
- `CAPTCHA_LLM_AGENT_CMD`: binario Agent montato, es. `/home/ced/.local/bin/agent`.
- `CAPTCHA_LLM_AGENT_MODEL`: default `auto`.
- `CAPTCHA_LLM_AGENT_OUTPUT_FORMAT`: default `text`.
- `CURSOR_AUTH_TOKEN_FILE`: file auth Cursor montato read-only; il worker ne legge il token senza stamparlo.

Il flusso operativo e: il worker salva l'immagine CAPTCHA, chiama Agent con prompt a risposta secca,
normalizza il token alfanumerico e lo invia a SISTER. Se Agent restituisce testo non valido o SISTER rifiuta
la soluzione, il worker ricarica il CAPTCHA entro il numero di tentativi configurato prima del fallback manuale.

Durante troubleshooting non stampare mai token Cursor, password SISTER o connection string; verificare solo
stato batch/richieste e log sanitizzati.

## Prossimi passi

Indica ID visura o stato che cerchi e ti spiego come leggere esito e prossimi passi operativi.
