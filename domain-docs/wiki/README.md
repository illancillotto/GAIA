# Wiki Domain Docs

Questa directory raccoglie la documentazione del modulo `wiki`.

Struttura:

- `docs/`: PRD, piani implementativi, prompt e note architetturali del modulo
- `operational/`: corpus operativo persistente per il Wiki Agent

Il corpus `operational/` e pensato come base per il routing task-first del Wiki:

- descrive moduli, pagine, capability e workflow
- esplicita input minimi, output attesi ed errori frequenti
- riduce la dipendenza da fallback documentali generici
