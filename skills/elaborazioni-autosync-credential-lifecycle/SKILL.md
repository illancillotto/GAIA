---
name: elaborazioni-autosync-credential-lifecycle
description: Gestisci le credenziali SISTER e la campagna AutoSync visure senza confondere l'abilitazione globale con le fasce dedicate della campagna.
version: 1.1.0
author: GAIA maintainers
---

# Elaborazioni AutoSync Credential Lifecycle

Usa questa skill per incidenti, modifiche o verifiche che coinvolgono
`/elaborazioni/settings`, `/elaborazioni/visure` e il workflow AutoSync a
ruolo.

## Modello operativo

- `catasto_credentials.active` rende una credenziale utilizzabile dal worker,
  ma non la iscrive automaticamente alla campagna AutoSync.
- La selezione AutoSync e le sue fasce vivono in
  `catasto_ruolo_autosync_config.credential_profiles`.
- Le fasce configurate in `/elaborazioni/settings` sono globali della
  credenziale. Sono usate da AutoSync solo dalle configurazioni legacy senza
  `credential_profiles`.
- Quando esiste un profilo AutoSync, le sue fasce dedicate prevalgono su quelle
  globali. Non copiarle o sovrascriverle automaticamente.
- Il scheduler `elaborazioni_ruolo_autosync` verifica le configurazioni attive
  ogni minuto. Per una verifica immediata usare `Esegui adesso` dalla pagina
  AutoSync, non avviare batch direttamente dal database.

## Lifecycle sicuro

1. Creare o aggiornare una credenziale in Settings e verificarne il login.
2. Attivare la credenziale globale solo quando puo essere usata dal worker.
3. Abilitare esplicitamente la stessa credenziale nel pool AutoSync e impostare
   le fasce dedicate della campagna.
4. Dopo una modifica delle fasce AutoSync, salvare la configurazione e usare
   `Esegui adesso` per il controllo immediato; il scheduler resta il fallback
   entro un minuto.
5. Quando una credenziale viene disattivata, non lasciare profili AutoSync
   abilitati che la referenziano. La riattivazione non deve riabilitarla nella
   campagna senza una scelta esplicita dell'operatore.

## Diagnosi

- `Una credenziale autosync non e disponibile o non e attiva`: controllare
  prima i profili persistiti e le credenziali attive; i riferimenti stale
  disabilitati vanno rimossi, quelli abilitati richiedono una scelta esplicita.
- Fascia aggiornata ma nessun batch: verificare se la fascia e stata cambiata
  nel profilo AutoSync, non solo nelle impostazioni globali; poi controllare
  configurazione ON, almeno una priorita attiva, elementi dovuti, lease SISTER
  e batch gia in corso.
- Non modificare `credential_profiles` via SQL per forzare un avvio: usare API
  o UI per mantenere lock, validazione e audit coerenti.

## Artifact errori recenti

- In `/elaborazioni/visure`, ogni errore recente con `linked_request_id` offre
  `Dettagli`: mostra stato, tentativi, operazione, esecuzione ed errore della
  richiesta batch collegata.
- Se la richiesta ha `artifact_dir`, usare `Scarica artifact` per lo ZIP e
  `Preview screenshot` per la schermata diagnostica. Le azioni riusano gli
  endpoint autorizzati della Gestione batch e rispettano l'ownership utente.
- Se la richiesta non ha artifact o la directory non e piu disponibile, non
  ricostruire dati: conservare i dettagli persistiti e mostrare chiaramente
  l'assenza dell'artifact.

## Verifiche minime

- Il profilo AutoSync contiene solo credenziali attive e abilitate
  esplicitamente.
- La fascia mostrata nella modalita AutoSync e quella effettivamente valutata
  da `available_perpetual_credentials`.
- Il monitor AutoSync registra il batch avviato oppure la ragione per cui non
  esistono elementi avviabili.
