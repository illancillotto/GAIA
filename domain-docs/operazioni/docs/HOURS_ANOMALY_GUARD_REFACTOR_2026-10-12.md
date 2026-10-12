# Discrepanze ore — guardia di emissione R52

La risposta `hours_discrepancy` conserva il comportamento precedente:
le query escludono durate null, includono gli estremi temporali e mantengono
l'ordine dei risultati. Si calcola lo scarto assoluto fra le due conversioni
intere, nello stesso ordine; scarti fino a60minuti non producono anomalie.
Da61a119minuti la severity resta low, da120minuti medium. Ordinamento finale
stabile, descrizioni, dettagli, conteggi e autorizzazioni restano invariati.

Una guardia `diff <= THRESHOLD_MIN: continue` sostituisce l'emissione annidata,
senza estrarre servizi, spostare responsabilità o cambiare query/transazioni.
La disposizione su una riga dei due operandi mantiene lo stesso AST e non
riceve credito di complessità. Riduzione piccola: cognitive239→238, aggregato
file724→723; cyclomatic, nesting massimo, LOC e parametri invariati.

Caratterizzazione prima/dopo e verifica sull'integrazione:379test genuini e78
supplementari PASS,15spec/457identità esatte. I supplementari AST/sintetici
sono eseguiti separatamente e non contribuiscono alla coverage. File analytics
completo statement/branch100:623→624statement,252branch; quattro esclusioni
difensive legacy immutate. Il nuovo continue è realmente esercitato.

Ratchet contro main55a PASS/findings[]. Nessun finding eliminato e nessuna
eliminazione della coda estrema. Fonte: report di integrazione R52 e ricevute
native private della campagna; non è una certificazione delle suite globali.
