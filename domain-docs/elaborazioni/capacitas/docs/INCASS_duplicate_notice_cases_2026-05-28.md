# Casi Residui Duplicazione Notice inCass

Data estrazione: `2026-05-28T10:53:20+02:00`

## Contesto

Durante il retry `inCass` dei job `126..130` sono rimasti `27` soggetti falliti.

Tutti i casi residui osservati in questa estrazione hanno lo stesso pattern applicativo:

- errore SQLAlchemy/PostgreSQL: `UniqueViolation`
- vincolo colpito: `uq_ana_payment_notices_source_notice`
- chiave conflittuale: `(source_system='incass', source_notice_id='<avviso>')`

## Interpretazione

Questi casi non indicano duplicati veri persistiti in `ana_payment_notices`.

Il problema osservato e coerente con risposte `inCass` che ripropongono lo stesso `avviso`
piu volte con varianti di stato o con reinserimento nello stesso flusso di sync/retry.

## Esempi verificati live su inCass

- `PUPPIN PIERGUIDO` `PPPPGD71L18A357V`
  - avviso `020110010251660`
  - anno avviso `2011`
  - stesso `row_id`
  - stato restituito in due varianti:
    - `Con esubero`
    - `Pagamento tardivo registrato post-chiusura`

- `PODDA ANTONELLO` `PDDNNL63D17L122O`
  - avviso `120170008376340`
  - anno avviso `2017`
  - stesso `row_id`
  - stato restituito in due varianti:
    - `Con esubero`
    - `Pagamento tardivo`

## Elenco Completo Casi Residui

| Retry job | Subject ID | CF/P.IVA | Nominativo | Avviso in conflitto | Anno avviso | Errore |
| --- | --- | --- | --- | --- | --- | --- |
| 126 | `4e040e41-cb3d-4ac0-8870-7bf0691ba829` | `PDDNNL63D17L122O` | Podda Antonello | `120170008376340` | `2017` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 126 | `41eac757-5f79-4fb6-a113-23e2987b1f58` | `PPPPGD71L18A357V` | PUPPIN PIERGUIDO | `020110010251660` | `2011` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 126 | `0191eb3a-fa6c-485f-8a98-ac3030f41b88` | `PNNMRA25C61A621Q` | Pinna Maria | `020130009398860` | `2013` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 126 | `06dca1a9-b4f5-4f21-a80b-d34794a3bdbe` | `LTZMHL36P70I384M` | Lutzu Michela | `020130006096820` | `2013` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 126 | `434abd28-4513-4d89-bd61-d00becdaf91b` | `SRDFNC50A06F980X` | Sardu Francesco Angelo | `020150012395760` | `2015` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 126 | `148cdd5f-e39c-4afb-bf46-9138f3dda7d6` | `TRODNL66L18G113F` | Tore Daniele | `020130013351620` | `2013` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 126 | `492b117c-874c-4544-a8d9-b3c785949624` | `CLAFNC60P07A126S` | Cauli Francesco | `020140002243120` | `2014` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 128 | `773c98b9-83fb-45a2-9eda-be392570d2b9` | `STCMRZ75P28E281O` | Stocchino Maurizio | `020130012990890` | `2013` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 128 | `6acfc3e8-64c1-4f8d-b1f1-fb7d1f074425` | `CCIBNR76D03E972I` | CICU BERNARDINO | `020130002003630` | `2013` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 128 | `73bd42c1-0671-47d5-9441-23dceb0c61e6` | `PNTRLL63R57A357J` | PANETTO ORNELLA MARIA | `020120009851540` | `2012` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 128 | `626618e2-0fe1-46aa-a370-3e89ff105cc6` | `PNNGRG54R31L122Y` | PINNA GIORGIO | `020130009339270` | `2013` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 128 | `785df07a-d323-4ba6-be14-c2a733b525f7` | `PTZMCR69P66E972I` | PUTZULU MARIA CARMELINA | `020130010560840` | `2013` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 128 | `7738444a-51a1-41b6-a4b6-ed86b7f1165e` | `CRTGST60E13H301P` | Carta Augusto | `020150003247460` | `2015` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 128 | `705ffd8a-181c-4cba-9826-3e17b08cfea2` | `MLSGNN65L23F979L` | MULAS GIOVANNI | `020120006953660` | `2012` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 130 | `e6c1fb14-8694-4040-a25f-614859909442` | `CDDFBN59A20F980Q` | Cadeddu Fabiano | `120160001845020` | `2016` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 130 | `f37692c1-bab9-4639-a754-457f0a35b731` | `FNEVGN28D63L122F` | FENU VIRGINIA | `120160004586270` | `2016` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 130 | `e79c6841-173f-48bb-adcc-4c7aea1525d9` | `DSSPRN46S16L122E` | Dessi Pietrino | `020110005054100` | `2011` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 130 | `bd81edb9-de4d-4ff7-9c71-577ad2da3c72` | `TCCSLV25H23L122O` | TOCCO SILVIO | `020130013119240` | `2013` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 130 | `9c06ebc2-e606-4634-bbb0-f1a1345ce18c` | `SRRMRA33M53G113H` | Serra Maria | `020130012824200` | `2013` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 130 | `a34c56f7-101a-4c30-9ee0-d57d16de62b6` | `DSELSN48C57I743U` | Deias Lisena | `120170003879960` | `2017` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 130 | `f8706c08-6a83-4912-a4d2-973f7d48463f` | `TVRRNZ56S18L122S` | TUVERI RENZO | `120160013138430` | `2016` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 130 | `9da35d8c-ca3a-4389-859c-8a71792ea085` | `TRTMLN74M47E972P` | Tirotto Emiliana | `020120013671910` | `2012` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 130 | `8d255311-eca6-4c91-ac83-d7429fb39b51` | `MLSPTR75T15F979J` | Mulas Pietro | `020110007389170` | `2011` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 130 | `b975ce86-d2e4-4764-8e5f-d58c2ca65cc6` | `TZNLND51C43L321N` | ATZENI LINDA | `020120013842680` | `2012` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 130 | `ae4e566a-93f9-474e-811e-86464c63408c` | `CDNGLC75C12G113J` | Cadoni Gianluca | `120170001911680` | `2017` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 130 | `bbdadba0-78c5-4811-a346-c7513cd0f033` | `MNCFST61C14G113N` | Mancosu Fausto | `120170006525260` | `2017` | `UniqueViolation uq_ana_payment_notices_source_notice` |
| 130 | `8e3fd138-0ea2-4e6d-a8e2-9ad635a49619` | `DSSGNN52A13G113K` | Dessi' Giovanni Angelo | `020130004344760` | `2013` | `UniqueViolation uq_ana_payment_notices_source_notice` |

## Sintesi Numerica

- soggetti residui: `27`
- tutti i residui classificati: `UniqueViolation`
- job retry coinvolti:
  - `126`: `7` casi
  - `128`: `7` casi
  - `130`: `13` casi

## Implicazione Operativa

Prima di un ulteriore retry e necessario rafforzare la strategia di upsert
su `ana_payment_notices`, idealmente con:

1. deduplica preventiva per `source_notice_id` nel batch in memoria
2. `INSERT .. ON CONFLICT (source_system, source_notice_id) DO UPDATE`
3. eventuale persistenza separata delle varianti di stato raw restituite da `inCass`
