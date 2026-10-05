# Bonifica Oristanese — parsing form HTML

## Contratto preservato

Il parser comune in `backend/app/modules/elaborazioni/bonifica_oristanese/parsers.py`
estrae campi input/select/textarea senza cambiare i workflow dei client Bonifica.

- Nomi mancanti, `_token` e `_method` ignorati; textarea con trim esterno.
- Select legge solo option selezionate, lista per multiple o nome terminante[];
  altrimenti primo valore selezionato o stringa vuota, senza fallback implicito.
- Checkbox scalare produce bool; array accumula copie dei valori precedenti,
  default `on` per checked senza value. Un precedente scalare viene sostituito.
- Radio checked sovrascrive; unchecked inizializza vuoto solo senza valore
  precedente. Input generico/hidden/disabled conserva value o stringa vuota.
- Ordine chiavi e sovrascritture seguono l'ordine del documento; liste fresh.

## Refactoring verificato

Scansione documento, lettura select/checkbox e raccolta input sono responsabilita
separate. Guard clause preservano la precedenza e riducono nesting, senza wrapper,
nuove esclusioni o modifiche a API, auth, schema dati o workflow.

`parse_form_fields` cog/cyc/LOC/nesting51/21/36/4 ->12/7/14/3;
cognitive file61 ->38. Cyclomatic32 ->35 per tre basi callable aggiunte,
branching28 invariato, LOC65 ->68. Tre violation diventano zero, senza trasferimento.

34 test prima/dopo, coverage full-file100% statement67/branch38 senza esclusioni,
5000 documenti differenziali con valori e ordine chiavi identici. Ratchet merge-base
`45741085`, Ruff mirato e format-check del nuovo test PASS. Lint globale segnala
UP038 InCass concorrente fuori perimetro; test integrazione richiedono virtualenv
con geoalchemy2, assente nel Python di sistema: cinque test pertinenti PASS nel
virtualenv completo (36 deselezionati). Campagna di complessita non-MCP
resta aperta sul repository.
