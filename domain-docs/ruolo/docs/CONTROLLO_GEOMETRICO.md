# Controllo geometrico delle particelle

## Implementazione

Nel dettaglio pratica di `/ruolo/particelle` il pannello **Confronto geometrico
PostGIS** salva una nuova evidenza `spatial_check` usando il comando versionato
e idempotente esistente. Non introduce tabelle, migrazioni o servizi applicativi
separati. La geometria della particella deriva esclusivamente da un collegamento
`cat_particella_id` gia presente nelle occorrenze dello storico. Collegamenti
assenti o multipli sono rifiutati: non si fa matching sul solo numero di particella.

Il layer deve essere attivo, pubblicato nel registro `gis_layers` e consultabile
dall'operatore secondo i permessi GIS esistenti. L'azione richiede anche i permessi
istruttori Ruolo. Schema, tabella e geometria provengono dal registro, non da SQL
arbitrario; identificativi validati e valori parametrizzati.

## Tre ambiti distinti

- `districts`: unione dei poligoni dei distretti, senza `FD` e `FD_1`–`FD_7`.
  Indicare la colonna codici: `NUM_DIST` nello shapefile originale, oppure il
  nome effettivo conservato dal processo di import GIS. Codici nulli/vuoti
  impediscono un esito verificabile, non sono assimilati a zone escluse.
- `municipality`: selezionare esplicitamente un comune tramite colonna e valore
  identificativo del layer. Il confine comunale non e un centro abitato.
- `settlements`: unione di tutte le categorie del layer poligonale selezionato,
  come classificazione preliminare degli insediamenti. Non rappresenta una
  delimitazione comunale ufficiale dei centri abitati.

Nessun confronto altera la pratica, la coda proposte o il ruolo. Le particelle
storicamente a ruolo nel 2011–2025 restano in istruttoria anche se interferenti
con insediamenti; una precedente presenza non autorizza il reinserimento.
Un risultato geometrico non e l'evidenza tributaria `territory` necessaria per
una conferma: resta richiesta la verifica motivata dell'operatore.

## Calcolo ed evidenze

Un solo statement PostGIS unisce i poligoni con `ST_UnaryUnion(ST_Collect(...))`,
trasforma in EPSG:3003, calcola `ST_Intersection` e `ST_Area`, e classifica:

| Esito | Significato |
| --- | --- |
| `inside` | il perimetro copre tutta la particella (`ST_Covers`) |
| `partial` | sovrapposizione di superficie positiva, copertura non totale |
| `touching` | solo contatto, superficie condivisa nulla |
| `outside` | nessuna intersezione |
| `not_verifiable` | fonte vuota/invalida, SRID ignoto o geometria particella inutilizzabile |

Niente centroide, buffer, snap o riparazione automatica. Nessuna tolleranza
geometrica e introdotta: piccoli disallineamenti vanno valutati con evidenze.
Il confine fra due distretti non esclude una particella coperta dalla loro
unione. Una geometria invalida del layer rende il confronto non verificabile,
anziche essere silenziosamente scartata. Layer lineari non diventano poligoni.

L'evidenza conserva superficie della particella, superficie e percentuale
intersecata, esito, ID del layer e della geometria catastale, data, operatore,
versione e copertura dichiarate, ultimo aggiornamento del registro, hash delle
geometrie e fingerprint dell'evidenza. Le misure sono riferite alle geometrie
effettivamente utilizzate, non alle superfici dichiarate in anagrafica.
Fonte/versione e completezza devono essere verificate dall'operatore; non sono
dedotte dalla presenza di un layer nel catalogo.

## Prerequisiti operativi e limiti

L'ispezione grafica dello shapefile NAS conferma poligoni dei distretti e zone
FD, con discontinuita e vuoti; sono presenti 3 anelli interni nelle 59 feature.
Gli attributi sono `NUM_DIST`, `SUP_HA`, `Sup_Distr`, `Nome_DIST`, `Acq_1`,
`Acq_2`, `Y`, `X`: non identificano delimitazioni comunali dei centri abitati.
Un vuoto o una zona FD non puo essere classificato automaticamente come centro
abitato senza una fonte o una legenda che ne attesti tale significato.

1. Pubblicare lo shapefile NAS `Distretti_Irrigui_3003_r1.shp` tramite il processo
   di import GIS gia esistente, come layer separato. Il file non e letto dal
   mount GVFS del computer operatore durante una richiesta backend.
2. Conservare provenienza, versione e checksum tramite l'archivio import GIS.
   Il pannello richiede l'ID del layer pubblicato e l'attestazione di copertura.
3. Non usare indiscriminatamente `cat_distretti`: il controllo preliminare ha
   accertato differenze rispetto allo shapefile NAS. Nessuna geometria operativa
   e sovrascritta da questa implementazione.
4. I limiti comunali RAS sono registrati come layer esterno `ras_limiti_comunali`
   (`dbu:limiti_amministr_com_ctr`). Le tabelle `cat_comuni` e `catasto_comuni`
   non contengono poligoni comunali. Il layer comunale esterno non e direttamente
   utilizzabile dal pannello PostGIS di questo ciclo.
5. I WMS non sono geometrie. Il layer RAS `dbu:componentiinsediativo_a` e
   interrogabile via WFS, ma non e stato copiato in PostGIS: la governance GIS
   esistente vieta la copia indiscriminata dei layer esterni. Il confronto WFS
   tramite i servizi GIS esistenti resta una integrazione successiva, con
   verifica licenza, copertura, paginazione, timeout e risultati parziali.

L'attivazione richiede deployment del codice e pubblicazione/verifica del layer
di fonte. Questo ciclo non esegue import, deployment o analisi massiva sulle
1.192.948 occorrenze operative. Il pannello e inizialmente per singola pratica:
verificare tempi dei layer nel collaudo prima di un'eventuale elaborazione batch.
Nessuna valutazione geometrica corrente prova confini o titolarita del passato.

## Verifiche

- 68 test backend del flusso, coverage statement e branch 100% dei runtime
  del controllo; 28 test frontend, coverage 100% includendo il nuovo pannello.
- SQL del servizio provato su PostGIS 3.4 del server con sole tabelle temporanee,
  transazione e rollback: unione di due distretti, esclusione FD, sovrapposizione
  50%, solo contatto, fuori e geometria nulla. Nessun dato operativo modificato.
- Test di autorizzazione GIS, SQL parametrizzato, sorgenti mancanti/non poligonali,
  identificativi ambigui, persistenza dei metadati e replay del comando.
- Ruff, ESLint, typecheck e ratchet completo contro la baseline del merge-base;
  Graphify aggiornato tramite i target dedicati, senza versionare gli artefatti.
