# Straordinario operai: anticipo escluso e uscita da 15 minuti

Il turno OPE0613 poteva ereditare l'inizio 05:30 dal modello stagionale anche
quando INAZ attestava 06:00–13:00 per quella giornata. Un ingresso 05:50 con
uscita 13:10 produceva così 20 minuti extra e 10 notturni. Ora il codice
**effettivo della giornata** prevale sul modello generico: ordinario 420,
extra zero, notturno zero. Un modello con più inizi alternativi non autorizza
la scelta automatica dell'inizio più precoce.

La regola confermata esclude l'anticipo dal calcolo automatico e riconosce
l'uscita oltre le ore standard da **15 minuti inclusi**, conteggiata al minuto.
Restano la pausa dalle 16:00 e le rettifiche amministrative esplicite; i valori
STR/MPE importati non possono ripristinare minuti esclusi.

Sono coperti anche OPEF0613 e i sabati estivi effettivi OPESACE (06:00–12:00),
OPSABE (06:00–12:30), OSAB5.3_11.3 (05:30–11:30), usando le configurazioni
persistite dei gruppi senza modificare il DB. Un codice feriale da sette ore
esplicitamente lavorato al sabato conserva la propria durata. Il turno delle
05:30 conserva l'ordinario notturno 05:30–06:00.

Per OPE0714 rimasto nominalmente 07:00–14:00 viene applicato il cambio operativo
06:00–13:00 già confermato: coppie complete nella stessa giornata, primo ingresso
oltre 05:30 ed entro 06:00, ultima uscita fra 13:00 e 22:00 incluse. Il caso
05:35–17:30 vale 420 minuti ordinari e 240 extra dopo la pausa, esclusi i 25
minuti anticipati. Le coppie incomplete/notturne non vengono trasformate in
turni diurni; impiegati e codici sconosciuti mantengono il percorso esistente.

## Verifiche

- Regressione mirata: 184 test; tre runtime al 100% statement (511/511).
- Suite finale estesa: **422 test passati**, tre runtime al 100% statement
  (511/511). Restano i warning JWT delle credenziali di test.
- Casi 14/15 minuti, anticipo puro, anticipo più uscita breve, pausa, ritardo,
  rettifiche, festività, sabati, modello con alternative e turno effettivo.
- Audit read-only su 1.054 giornate di 34 collaboratori presenti nell'export
  agosto: tutte le 329 quote feriali positive originarie sono incluse.
  Totale prima 22.583 minuti (376h23), dopo 18.782 (313h02), 239 quote cambiate;
  nessuna quota positiva residua sotto 15 e nessuna fuori dalla policy.
- Tre giornate OPE0714 perdono anche 5, 17 e 13 minuti ordinari precedenti
  all'inizio nominale: l'anticipo escluso non completa ore standard mancanti.
- Ruff e ratchet globale contro origin/main/e9804b84 superati, findings vuoti.
  Nel perimetro errori di complessità invariati (7), warning 10→11; il resolver
  passa da cognitive/cyclomatic 34/21 a 27/19. Il nuovo helper di riconoscimento
  del cambio turno è al limite warning, sotto tutte le soglie error.
- Sincronizzazione baseline globale respinta per debito preesistente esterno
  alla change, fra cui capacitas_routes.py e callback UI; baseline invariata.
- Graphify Presenze codice aggiornato; output locali non versionati.

Il campione copre le quote dell'audit, non certifica gli altri collaboratori o
mesi. Il rilascio richiede gli stessi tre moduli su API GAIA, outbound e worker,
poi confronto effettivo con cache GATE e compilatore XLSM installato sul VPS.
GATE non necessita di un nuovo algoritmo: usa i minuti canonici ricevuti.

## Rilascio verificato

Runtime commit `30828445`, immagine `gaia-backend:extra-30828445`. API,
outbound e worker Presenze sul server sorgente CED sono healthy e verificati
con hash dei tre file identici al commit. Worker sostituito con zero importazioni
running e lock sulle nuove acquisizioni. Manifest, backup, overlay e rollback:
`/opt/gaia/releases/extra-30828445/`. Aggiornato anche il tag backend latest
per mantenere il fix nelle ricreazioni ordinarie dei container.

Ciclo outbound dopo il deploy riuscito: 2026-09-11 09:25:51–09:28:15 UTC.
Snapshot GAIA 09:26:37 UTC confrontato con cache GATE ricevuta alle 09:27:47:
5.859 giornaliere, nessun record mancante e zero differenze su totali, stato,
minuti mancanti e categorie export. Nessun backfill delle timbrature.

Verifica finale su tutti i **35 collaboratori e 1.085 giorni** del file utente:
329 quote feriali positive precedenti, 164 dopo il fix, totale 313h02;
239 quote cambiate. Nessuna quota feriale residua sotto 15 minuti.
Il compilatore realmente installato sul VPS GATE (`88dee90`) ha generato
`Giornaliere_2026_08_straordinari_corretti.xlsm` dalla cache aggiornata.
Le 1.085 celle FG:GK e i 35 totali Archivio!L coincidono con i dati canonici;
VBA identico al modello e 1.259 formule con valori memorizzati in Giornaliera2.
SHA256 del file: `2c2180d70a0abffc8a84376eb615ec10452d9f5104ecc2bf05c4b7c120462383`.
Nessuna variazione alla soglia buoni pasto fra le quote positive confrontate.

GATE non ha richiesto modifiche runtime né un nuovo deploy: la correzione è
nella sorgente e lo snapshot corretto è già arrivato sul VPS. Report e CSV con
le timbrature sono nella cartella Downloads dell'operatore, fuori dal repository.
