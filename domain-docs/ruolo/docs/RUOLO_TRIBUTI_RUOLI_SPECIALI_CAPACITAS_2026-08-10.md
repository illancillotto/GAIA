# Ruolo tributi - Ruoli speciali Capacitas

Data: 2026-08-10

## Contesto operativo

Alcuni codici Capacitas non rappresentano annualita tributarie ordinarie. Gli operatori li usano come meccanismo tampone per tracciare pagamenti, attivita particolari, avvisi accorpati o rettifiche operative che possono essere creati, annullati e ricreati in base alle esigenze.

Questa logica riguarda in particolare:

- `2525` e `2626`: avvisi accorpati, relativi ad anni precedenti, che possono essere annullati e ricreati.
- `7700`: violazioni di regolamento, senza annualita tributaria ordinaria.
- `7890`: avvisi Agenzia delle Entrate.
- `99xx`: anticipi tributi eseguiti dal conduttore/affittuario per irrigare terreni gravati da morosita del proprietario.

I codici storici `2323` e `2424` non sono considerati speciali noti perche non risultano creati nel perimetro operativo corrente.

## Policy di dominio

I ruoli speciali sono trattati come movimenti amministrativi fuori ordinario:

- non alimentano saldo ordinario;
- non modificano morosita;
- non creano annualita tributarie ordinarie;
- non rettificano automaticamente partite, particelle o soggetti;
- possono essere collegati manualmente ad avvisi, partite, particelle, soggetti o annualita solo come audit operativo.

Ogni collegamento manuale deve essere documentato con una motivazione o una nota. Il collegamento resta `audit_only` e non ha impatto contabile.

## Stato operativo normalizzato

Il sync da InCASS conserva lo stato sorgente Capacitas e deriva uno stato operativo normalizzato:

| Stato | Significato |
| --- | --- |
| `cancelled` | avviso speciale annullato integralmente |
| `partially_cancelled` | avviso speciale annullato parzialmente |
| `paid` | avviso speciale pagato |
| `partial` | avviso speciale pagato parzialmente |
| `open` | avviso speciale aperto/non pagato |
| `to_review` | stato non interpretabile automaticamente |

La priorita di ricostruzione e l'annullamento: se `stato_label` indica annullamento o `importo_annullato` e valorizzato, lo stato operativo viene classificato come annullato prima di valutare pagamento o apertura.

## API e filtri

Gli endpoint `GET /ruolo/tributi/special-notices` espongono:

- `source_status_label`;
- `operational_status`;
- `is_cancelled`;
- `importo_annullato`;
- `accounting_scope = out_of_ordinary`;
- `operational_policy = audit_only`;
- `impacts_ordinary_balance = false`.

Sono disponibili filtri operativi:

```text
GET /ruolo/tributi/special-notices?operational_status=cancelled&is_cancelled=true
GET /ruolo/tributi/special-notices?codice_ruolo=2525&is_cancelled=false
```

## Limite noto

La logica corrente ricostruisce lo stato sincronizzato visibile in InCASS. Per ricostruire una sequenza storica completa, per esempio `creato -> annullato -> ricreato`, serve un event log o snapshot storico locale degli special notices a ogni sync. Senza snapshot locali, GAIA dipende da quanto Capacitas/InCASS espone ancora nel dato corrente.
