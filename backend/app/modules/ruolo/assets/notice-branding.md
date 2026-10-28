# Grafica istituzionale e canali pubblici dell’avviso GAIA

Aggiornamento 2026-10-27. Materiale fornito dall’utente per la prima pagina
HTML/Chromium degli avvisi e solleciti; non modifica la base dei bollettini.

| Asset | Origine | Elaborazione |
| --- | --- | --- |
| `notice-cbo-logo.png` | `Logo_Pantone.jpg` | Ritaglio del solo margine bianco e riduzione proporzionale a 1400 x 728 pixel |
| `notice-anbi-logo.png` | `associazione-nazionale-consorzi-gestione-anbi-logo-vector.png` | Ritaglio del solo margine bianco, 600 x 342 pixel |
| `notice-whatsapp-qr.png` | QR WhatsApp allegato dall’utente | Copia integrale, 336 x 336 pixel |
| `notice-irrighiamo-qr.png` | `QR-IrrighiamoInseme.png` fornito dall'utente il 2026-10-28 | Copia integrale, 1080 x 1080 pixel |
| `notice-taxpayer-portal-qr.png` | `QR-PortaleContribuente.png` | Copia integrale, 1080 x 1080 pixel |

I loghi mantengono colori e proporzioni; i QR non sono stati rigenerati.
Destinazioni decodificate e usate anche come link nel PDF:

- WhatsApp: https://whatsapp.com/channel/0029Vb9tZLzDJ6H3keAt9h24
- Portale: https://incatasto.servizicapacitas.com/pages/main.aspx?cons=090
- Irrighiamo Insieme: https://login.bonificaoristanese.it/

Pagina informativa indicata dall’utente:
https://www.bonificaoristanese.it/novita/canale-whatsapp-dedicato-alle-comunicazioni-del-consorzio-di-bonifica/
Il recupero automatico ha restituito HTTP 403: non sono stati dedotti ulteriori
servizi o condizioni del canale. La descrizione stampata si limita alle
comunicazioni del Consorzio.

Il modulo `services/notice_branding.py` incorpora i due loghi e i due QR WhatsApp/Irrighiamo Insieme
come data URI; non accede a Pictures, Downloads o Internet durante la stampa.
I QR sono di `18mm`, in due riquadri affiancati con gap `3mm`, descrizione
del canale/applicazione e invito a inquadrarli. Irrighiamo Insieme e descritto
con la frase: «L'applicazione del Consorzio per segnalare guasti o rotture e
richiedere l'autorizzazione all'irrigazione.» La descrizione riprende le
funzioni dichiarate sulla [pagina pubblica di accesso](https://login.bonificaoristanese.it/),
verificata il 2026-10-28. Il QR WhatsApp rimane
senza «Apri il canale WhatsApp». L'informativa privacy segue con `1.5mm` di
margine. I test decodificano il QR dal PDF stampato a 144 dpi.

Il QR portale e conservato come asset di provenienza ma non viene stampato.
Prima dei contatti degli uffici e del testo informativo sul sito del Consorzio compare un blocco con il percorso
`www.bonificaoristanese.it > Cartella contribuenza >`, la spiegazione del servizio
e una sola coppia Codice ditta/PIN per utenza. Se mancante o ambigua, compare
l'invito a contattare gli uffici. I sei CF con due utenze sono sospesi in attesa
del riscontro dei colleghi. Contatti e sito sono consecutivi nello stesso
paragrafo, corpo `8.5pt`, interlinea `1.12`.
Il percorso nel PDF mantiene il collegamento al portale `cons=090`.

## Palette blu

La grafica HTML/Chromium usa ora il blu richiesto `#2b5793` per titoli, bordi
e importo. L'intimazione usa un triangolo vettoriale rosso `#c62828`, con punto
esclamativo rosso e fondo chiaro, al posto del precedente riquadro blu. La fascia titolo sfuma da `#2b5793` a `#3e72b3`;
i fondi sono `#eaf0f7`, `#f0f4f9` e `#f2f6fa`, con bordi chiari `#ccd7e5`.
Testi secondari e collegamenti usano grigi azzurrati e blu scuro `#244a7d`.
Anche il riquadro importo e la nota sul residuo adottano la palette blu.
Titolo partitario e tabella delle comunicazioni sono coordinati alla palette.

La prima pagina usa interamente Arial/Helvetica/sans-serif, inclusi titolo
ente e importo; le dimensioni e i pesi restano differenziati per gerarchia.
La variazione cromatica iniziale del 27 ottobre riguardava solo i colori;
l'aggiornamento del 28 ottobre aggiunge i due servizi e uniforma la famiglia font. Loghi e QR mantengono i file originali; il bollettino resta invariato.
Il renderer locale usa questa palette. L'anteprima dimostrativa e
`output/pdf/avviso-2021-anteprima-blu.pdf`; la precedente
`output/pdf/avviso-2021-anteprima.pdf` conserva il verde per confronto.
Non e introdotta una nuova selezione di tema nelle regole.

## Integrita degli asset

- `notice-irrighiamo-qr.png`: SHA-256 `d1919ce5d62d6f06a4f4f461ea78f4d67d29302e4d833fd16ce2231f1c51004b`; identico alla sorgente fornita, senza rigenerazione.

- `notice-cbo-logo.png`: SHA-256 `87f99882e89c63438ccbfbb04cb112d03ab1a2617a1ad8d78398043349316579`; sorgente `81a24fa38741c840a34652fa6a0699a1046a7ab4aea9622f863401eb62e3a148`.
- `notice-anbi-logo.png`: SHA-256 `98ac2c8bde0051b5b0a7af36c9248a9f5e7fc7dd84e2a3656d73d68b44cb416a`; sorgente `4758210d0082e4fa36f569a111a657177f3c01e8e4ae3a56d618182905192429`.
- `notice-whatsapp-qr.png`: SHA-256 `4d89a9e44b1ab7176851db250be196beae13e866c8091b27ff58be1600ea2166`; sorgente `4d89a9e44b1ab7176851db250be196beae13e866c8091b27ff58be1600ea2166`.
- `notice-taxpayer-portal-qr.png`: SHA-256 `5211251735be9e994ae12a62435ef984e78560cae9d92f80956a3293ecfc8865`; sorgente `5211251735be9e994ae12a62435ef984e78560cae9d92f80956a3293ecfc8865`.
