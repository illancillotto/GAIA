# Utenze — caratterizzazione raccolta documenti R103

La pagina dettaglio conserva il comportamento corrente. Ventisette nuovi casi
montano la pagina reale e verificano ordinamento per priorita/nome, raggruppamento
per categoria, confidenza, ricerca su dodici campi, conteggi e filtri, espansione
oltre cinque documenti e ripristino dei filtri.

Le opzioni categoria derivano dall'ordine originale dei risultati testuali; i
gruppi visualizzati derivano dal sottoinsieme ordinato. La selezione categoria
resta attiva anche quando la ricerca ne nasconde l'opzione. Tutti cancella solo
la categoria; Azzera filtri cancella anche testo ed espansione. Una ricerca di
soli spazi mantiene il collasso predefinito. Queste precedenze sono verificate,
non normalizzate attraverso modifiche funzionali.

Suite complessiva256PASS, nessun caso fallito/saltato o errore non gestito.
La coverage della pagina originale sale a561/576statement,563/610branch,
170/176funzioni e524/536righe; il gate100resta FAIL. Nessuna modifica runtime
o riduzione della complessita dichiarata. I confini API/auth/navigation sono
mock; questo non certifica portali esterni, database o sessioni browser reali.

Typecheck667root e lint mirato PASS. Ratchet autorevole contro main e verifiche
Graphify sono registrati nel handoff durevole del rapporto R103. Nessun commit,
push, merge main, aggiornamento baseline o riduzione della policy coverage.

Rapporto: `reports/code-quality/R103_UTENZE_DOCUMENT_COLLECTION_2026-10-15.md`.
Evidenze: directory esterna `r103-utenze-document-collection` sotto
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/`.
Campagna ancora attiva e incompleta; prossimo prerequisito distinto: audit log.
