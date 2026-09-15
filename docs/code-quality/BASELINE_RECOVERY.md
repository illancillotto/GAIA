# Recupero baseline globale

Audit del 2026-09-15 su `main@3596c36d`, con change dashboard Elaborazioni
preservata nel working tree. La baseline versionata dichiara come sorgente
`b1d4a988` del 2026-08-20. Il confronto per autorizzare nuove change deve
continuare a usare la baseline del merge-base.

## Dimensione del problema

Prima della prima slice: **200 rilievi su 38 file**, di cui 170 regressioni
di metriche callable, 20 violazioni di callable senza matching e 10 regressioni
file-level. Sono rilievi per metrica: non equivalgono a 200 funzioni difettose.
Il report complessivo contiene 4508 violazioni, 2043 error e 2465 warning;
questo debito assoluto include il legacy gia accettato e non coincide con
i 200 rilievi che impediscono la sincronizzazione.

Il CLI stampa soltanto `findings[:100]` nei comandi `check` e `baseline`.
L'audit integrale usa le stesse funzioni `scan`, `compare` e
`added_lines_since` del tool senza il limite di stampa. Nessuna modifica al
motore o alle sue regole e stata applicata.

| Raggruppamento dei percorsi | Rilievi iniziali |
| --- | ---: |
| GIS, percorsi `/gis/` | 54 |
| Worker, inclusi i test attualmente nel corpus | 37 |
| Elaborazioni | 36 |
| Presenze | 32 |
| Organigramma | 7 |
| Ruolo | 7 |
| Altri file condivisi, inclusi client API GIS | 27 |

Evidenze: `/tmp/gaia-baseline-audit-before.json` (inventario integrale),
`/tmp/gaia-baseline-audit-full.json` (repeat dopo la slice).

## Tranche revisionabili

1. **GIS coordinate guidate, conclusa**: `geometryFromCoordinates`, unica
   violazione error del file. Unificata la conversione della geometria base
   in `Multi*`, eliminando sei ternarie ripetute. Parsing, minimi di punti,
   chiusura anello e output GeoJSON preservati. Cyc `15 -> 10`, cog `23 -> 20`,
   LOC callable `31 -> 28`; file LOC `236 -> 233`, sum cyc `85 -> 80`,
   sum cog `93 -> 90`. Nessun helper, spostamento o nuova esclusione.
2. **Matching storico Presenze**: verificare i tre rilievi su
   `get_dashboard_summary` (`64/111`, LOC `128`) rispetto al precedente
   router e ai suoi fingerprint. Il backlog documenta gia mismatch da split;
   `new_callable_violation` da solo non prova che il debito sia nuovo.
   Non correggere automaticamente un'identita ambigua.
3. **GIS activity center**: candidato a un singolo hotspot successivo,
   `GisActivityCenter` cyc `15`, LOC `95`, con suite dedicata esistente.
4. **Contratti API e crescita sotto soglia**: classificare prima i rilievi su
   route/client Capacitas, batch e GIS. Ad esempio `list_incass_jobs_route`
   passa da due a quattro parametri per un contratto esteso: comprimere la
   firma solo per ripristinare la metrica sarebbe una correzione artificiale.
   Eventuali cambi di policy richiedono una decisione esplicita e separata.
5. **Hotspot critici**: onboarding INAZ, mapping collaboratori e worker SISTER
   richiedono le skill di dominio, invarianti identitari/di concorrenza e
   coverage completa. Un solo hotspot per iterazione; nessuna campagna
   automatica trasversale.

Il corpus corrente comprende anche test sotto `modules/elaborazioni/worker`.
Non sono stati esclusi per abbassare il conteggio. La loro presenza e una
questione di perimetro da valutare separatamente, non un errore qui dimostrato.

## Criterio di chiusura

La prima slice e `IMPROVED`: 19 test helper/componenti passati, coverage
full-file al 100% (statement 94/94, branch 114/114, funzioni 18/18,
righe 82/82). L'eliminazione di una violazione non risolve la baseline globale.
Il repeat integrale conferma **199 rilievi su 37 file**: 170 regressioni
callable, 19 violazioni senza matching e 10 regressioni file-level. Il file
`guided-workflow.ts` non compare piu tra i rilievi bloccanti.

Si potra sincronizzare la baseline soltanto quando il confronto integrale non
riportera regressioni o ambiguita. Eseguire quindi `complexity-baseline` e
`complexity-baseline-verify`, revisionando il diff. Nessun aggiornamento
globale, commit, deploy o allargamento delle esclusioni in questa prima slice.
