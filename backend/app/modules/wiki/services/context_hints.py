from __future__ import annotations

KNOWN_MODULE_TOKENS = (
    "wiki",
    "accessi",
    "catasto",
    "ruolo",
    "utenze",
    "operazioni",
    "riordino",
    "network",
    "rete",
    "organigramma",
    "elaborazioni",
    "inaz",
)

MODULE_HINTS = {
    "wiki": {
        "label": "Wiki",
        "examples": (
            "come cercare un articolo",
            "come aprire una richiesta supporto",
            "quali fonti sta usando questa risposta",
        ),
    },
    "accessi": {
        "label": "Accessi",
        "examples": (
            "come funziona il flusso di richiesta accesso",
            "quali ruoli servono per una funzione",
            "dove verificare i permessi disponibili",
        ),
    },
    "catasto": {
        "label": "Catasto",
        "examples": (
            "come leggere una visura",
            "quali dati controllare prima di una ricerca",
            "come interpretare esiti e stati",
        ),
    },
    "ruolo": {
        "label": "Ruolo",
        "examples": (
            "come funziona il workflow della pratica",
            "quali campi sono obbligatori",
            "come interpretare lo stato corrente",
        ),
    },
    "utenze": {
        "label": "Utenze",
        "examples": (
            "come leggere i dati di un'utenza",
            "quali campi sono rilevanti nella scheda",
            "come trovare una specifica informazione",
        ),
    },
    "operazioni": {
        "label": "Operazioni",
        "examples": (
            "come leggere una metrica operativa",
            "come interpretare un'anomalia",
            "quali dati spiegano un indicatore",
        ),
    },
    "riordino": {
        "label": "Riordino",
        "examples": (
            "come leggere lo stato di una pratica",
            "quali passaggi prevede il workflow",
            "quale documentazione serve per avanzare",
        ),
    },
    "network": {
        "label": "Rete",
        "examples": (
            "come leggere il riepilogo di rete",
            "come interpretare un device o un allarme",
            "quali dati controllare in caso di anomalia",
        ),
    },
    "rete": {
        "label": "Rete",
        "examples": (
            "come leggere il riepilogo di rete",
            "come interpretare un device o un allarme",
            "quali dati controllare in caso di anomalia",
        ),
    },
    "inaz": {
        "label": "Giornaliere",
        "examples": (
            "come leggere una giornata o un collaboratore",
            "come trovare responsabili e operatori",
            "come interpretare dati e anomalie del modulo",
        ),
    },
    "organigramma": {
        "label": "Organigramma",
        "examples": (
            "come leggere l'albero organizzativo",
            "come capire chi vede chi",
            "come interpretare ruoli, nodi e collegamenti",
        ),
    },
    "inventario": {
        "label": "Inventario",
        "examples": (
            "come leggere una scheda bene o asset",
            "quali dati identificativi controllare",
            "come trovare un elemento specifico",
        ),
    },
    "elaborazioni": {
        "label": "Elaborazioni",
        "examples": (
            "come leggere lo stato di un job",
            "come interpretare esiti e scarti",
            "quali artefatti sono stati prodotti",
        ),
    },
}

PAGE_HINTS = {
    "/inaz/banca-ore": {
        "label": "Banca ore",
        "examples": (
            "come leggere saldo, delta e liquidabile",
            "come aprire il dettaglio di un collaboratore",
            "come gestire rettifiche e liquidazioni della banca ore",
        ),
    },
    "/inaz/organigramma": {
        "label": "Organigramma giornaliere",
        "examples": (
            "come leggere l'organigramma corrente",
            "come trovare responsabili, diretti e sotto-alberi",
            "come leggere blocchi, collegamenti e livelli",
        ),
    },
    "/organigramma": {
        "label": "Organigramma",
        "examples": (
            "come leggere l'albero organizzativo",
            "come capire chi vede chi",
            "come interpretare ruoli, nodi e collegamenti",
        ),
    },
    "/wiki/support": {
        "label": "Supporto Wiki",
        "examples": (
            "come aprire una richiesta supporto completa",
            "quali campi compilare per farla gestire meglio",
            "quando usare supporto, bug report o feature request",
        ),
    },
    "/wiki/support/analytics": {
        "label": "Analytics supporto Wiki",
        "examples": (
            "come leggere i cluster di richieste",
            "come interpretare fallback e guardrail",
            "quali moduli o pagine generano più richieste",
        ),
    },
    "/wiki/conversations": {
        "label": "Conversazioni Wiki",
        "examples": (
            "come leggere una conversazione con fallback",
            "come trovare thread con denied o no match",
            "come capire perché una conversazione è stata segnalata",
        ),
    },
    "/operazioni/analisi": {
        "label": "Analisi Operazioni",
        "examples": (
            "come leggere una metrica operativa",
            "come interpretare un'anomalia",
            "quali dati spiegano un indicatore",
        ),
    },
    "/operazioni/pratiche": {
        "label": "Pratiche Operazioni",
        "examples": (
            "come leggere una pratica",
            "quali stati e campi contano di più",
            "come capire responsabile, avanzamento e contesto operativo",
        ),
    },
    "/operazioni/attivita": {
        "label": "Attività Operazioni",
        "examples": (
            "come leggere una attività",
            "quali dati spiegano tempi e operatori",
            "come interpretare stato e avanzamento",
        ),
    },
    "/elaborazioni/visure": {
        "label": "Visure",
        "examples": (
            "come leggere lo stato di una visura",
            "come interpretare esiti, scarti e retry",
            "quali artefatti sono stati prodotti",
        ),
    },
    "/elaborazioni/new-single": {
        "label": "Nuova visura singola",
        "examples": (
            "quali campi servono per una nuova visura",
            "come interpretare la preparazione della richiesta",
            "quali controlli fare prima dell'invio",
        ),
    },
    "/elaborazioni/new-batch": {
        "label": "Nuovo batch elaborazioni",
        "examples": (
            "come preparare un nuovo batch",
            "quali dati servono prima dell'avvio",
            "come interpretare i controlli iniziali del lotto",
        ),
    },
    "/elaborazioni/batches": {
        "label": "Batch elaborazioni",
        "examples": (
            "come leggere la lista dei batch",
            "quali stati aiutano a capire l'avanzamento",
            "come individuare batch bloccati, in errore o in retry",
        ),
    },
    "/elaborazioni/bonifica": {
        "label": "WhiteCompany Sync",
        "examples": (
            "come leggere lo stato della sincronizzazione",
            "quali esiti o anomalie richiedono attenzione",
            "come interpretare il risultato del sync",
        ),
    },
    "/elaborazioni/anpr": {
        "label": "ANPR batch",
        "examples": (
            "come leggere un batch ANPR",
            "quali esiti spiegano gli scarti",
            "come interpretare avanzamento e risultati del job",
        ),
    },
    "/elaborazioni/capacitas": {
        "label": "Capacitas",
        "examples": (
            "come leggere un'elaborazione Capacitas",
            "quali dati spiegano esiti e anomalie",
            "come interpretare il risultato del processo",
        ),
    },
    "/elaborazioni/ade-alignment": {
        "label": "Allineamento AdE",
        "examples": (
            "come leggere l'allineamento con AdE",
            "quali dati spiegano scarti o mismatch",
            "come interpretare il risultato del controllo",
        ),
    },
    "/elaborazioni/autodoc": {
        "label": "AUTODOC mezzi",
        "examples": (
            "come leggere la sincronizzazione AUTODOC",
            "quali dati spiegano esiti o anomalie",
            "come interpretare lo stato dei job sui mezzi",
        ),
    },
    "/elaborazioni/settings": {
        "label": "Credenziali Elaborazioni",
        "examples": (
            "quali credenziali servono per il modulo",
            "come capire se una configurazione manca",
            "come interpretare l'impatto operativo delle impostazioni",
        ),
    },
    "/nas-control/users": {
        "label": "Utenti NAS Control",
        "examples": (
            "come leggere una scheda utente",
            "quali gruppi o permessi verificare",
            "come capire lo stato di sincronizzazione dell'utente",
        ),
    },
    "/nas-control/groups": {
        "label": "Gruppi NAS Control",
        "examples": (
            "come leggere un gruppo",
            "quali utenti o share sono collegati",
            "come interpretare il ruolo del gruppo nel dominio NAS",
        ),
    },
    "/nas-control/shares": {
        "label": "Cartelle condivise NAS Control",
        "examples": (
            "come leggere una cartella condivisa",
            "quali utenti o gruppi hanno accesso",
            "come capire i permessi applicati alla share",
        ),
    },
    "/nas-control/effective-permissions": {
        "label": "Permessi effettivi NAS Control",
        "examples": (
            "come leggere i permessi effettivi",
            "quali eredità o gruppi spiegano un accesso",
            "come verificare perché un utente vede una share",
        ),
    },
    "/nas-control/reviews": {
        "label": "Review NAS",
        "examples": (
            "come leggere una review NAS",
            "quali anomalie o conferme richiedono attenzione",
            "come interpretare gli esiti di validazione",
        ),
    },
    "/network/devices": {
        "label": "Dispositivi Rete",
        "examples": (
            "come leggere un dispositivo di rete",
            "quali dati controllare in caso di anomalia",
            "come leggere stato, tracking e ultimo rilevamento",
        ),
    },
    "/network/firewalls": {
        "label": "Firewall Rete",
        "examples": (
            "come leggere una scheda firewall",
            "quali dati aiutano a capire regole o stato",
            "come interpretare anomalie o configurazioni rilevanti",
        ),
    },
    "/network/tracking": {
        "label": "Tracking Rete",
        "examples": (
            "come leggere il tracking di un dispositivo",
            "quali eventi spiegano un cambiamento di stato",
            "come interpretare cronologia e presenza in rete",
        ),
    },
    "/network/statistics": {
        "label": "Statistiche Rete",
        "examples": (
            "come leggere una statistica di rete",
            "quali indicatori aiutano a capire il carico",
            "come interpretare trend e distribuzioni",
        ),
    },
    "/network/alerts": {
        "label": "Alert Rete",
        "examples": (
            "come leggere un alert di rete",
            "quali dati aiutano a stimare l'urgenza",
            "come interpretare il contesto operativo dell'alert",
        ),
    },
    "/catasto/gis": {
        "label": "GIS Catasto",
        "examples": (
            "come leggere una particella sulla mappa",
            "quali livelli o dati cartografici contano",
            "come interpretare il contesto territoriale della selezione",
        ),
    },
    "/catasto/distretti": {
        "label": "Distretti Catasto",
        "examples": (
            "come leggere un distretto",
            "quali dati territoriali o riepiloghi controllare",
            "come capire il perimetro operativo del distretto",
        ),
    },
    "/catasto/particelle": {
        "label": "Particelle Catasto",
        "examples": (
            "come leggere una particella",
            "quali dati catastali sono più rilevanti",
            "come leggere i collegamenti con utenze, soggetti o documenti",
        ),
    },
    "/catasto/letture-contatori": {
        "label": "Contatori irrigui",
        "examples": (
            "come leggere una lettura contatore",
            "quali dati servono per verificare un'anomalia",
            "come interpretare storico e stato della lettura",
        ),
    },
    "/catasto/anomalie": {
        "label": "Anomalie Catasto",
        "examples": (
            "come leggere un'anomalia catastale",
            "quali dati aiutano a capire la causa",
            "come interpretare priorità e stato di gestione",
        ),
    },
    "/catasto/archive": {
        "label": "Archivio documenti Catasto",
        "examples": (
            "come trovare un documento",
            "quali metadati usare per filtrare",
            "come interpretare il collegamento tra documento e particella",
        ),
    },
    "/utenze/import": {
        "label": "Import Utenze",
        "examples": (
            "come leggere l'esito di un import",
            "quali campi o righe causano errori",
            "come interpretare scarti e aggiornamenti applicati",
        ),
    },
    "/utenze/visure-routing-anomalies": {
        "label": "Anomalie visure Utenze",
        "examples": (
            "come leggere una anomalia di routing",
            "quali dati spiegano l'instradamento della visura",
            "come interpretare errori, esiti e casi da correggere",
        ),
    },
    "/riordino/pratiche": {
        "label": "Pratiche Riordino",
        "examples": (
            "come leggere una pratica di riordino",
            "quali stati e fasi contano di più",
            "come leggere documenti, timeline e passaggi successivi",
        ),
    },
    "/riordino/configurazione": {
        "label": "Configurazione Riordino",
        "examples": (
            "come leggere una configurazione di riordino",
            "quali regole influenzano il workflow",
            "come capire l'effetto operativo di una impostazione",
        ),
    },
    "/ruolo/avvisi": {
        "label": "Avvisi Ruolo",
        "examples": (
            "come leggere un avviso",
            "quali dati sono più rilevanti nella scheda",
            "come leggere stato, importi e contesto tributario",
        ),
    },
    "/ruolo/particelle": {
        "label": "Particelle Ruolo",
        "examples": (
            "come leggere una particella collegata al ruolo",
            "quali dati aiutano a capire il collegamento con gli avvisi",
            "come interpretare la relazione con i soggetti coinvolti",
        ),
    },
    "/ruolo/stats": {
        "label": "Statistiche Ruolo",
        "examples": (
            "come leggere una statistica del ruolo",
            "quali indicatori spiegano andamento e distribuzione",
            "come interpretare i riepiloghi disponibili",
        ),
    },
    "/ruolo/import": {
        "label": "Workflow Ruolo",
        "examples": (
            "come leggere l'esito di una materializzazione ruolo",
            "quali errori o scarti richiedono attenzione",
            "come interpretare il risultato del workflow storico ruolo",
        ),
    },
    "/inventory": {
        "label": "Inventario",
        "examples": (
            "come leggere una scheda bene o asset",
            "quali dati identificativi controllare",
            "come trovare un elemento specifico",
        ),
    },
}
