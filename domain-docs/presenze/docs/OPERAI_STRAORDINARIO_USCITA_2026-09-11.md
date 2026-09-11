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
- Suite estesa: 421 test passati; il solo test del contratto elenco è stato
  corretto e ripetuto con esito positivo (campi export assenti da quella API).
  Restano i warning JWT delle credenziali di test, nessun errore runtime.
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
