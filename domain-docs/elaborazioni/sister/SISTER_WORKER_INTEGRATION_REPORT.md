# SISTER Worker — Report analisi implementazione e integrazione

> REP-WORKER-001 · v1.0 · maggio 2026
> Scope: `modules/elaborazioni/worker/` — sessione browser, flusso visura, CAPTCHA, gestione cookie/sessione
> Sorgenti analizzate: `browser_session.py`, `visura_flow.py`, `InoltraRichiestaVis.do` + 9 script JS caricati dalla pagina

---

## Sommario

| # | Titolo | File | Priorità |
|---|---|---|---|
| 1 | Cookie WINID non inizializzato prima del caricamento pagina | `browser_session.py · start()` | 🔴 Alta |
| 2 | Delay CAPTCHA reload fisso — race condition con sessione server | `visura_flow.py · capture_captcha_image()` | 🔴 Alta |
| 3 | `submit_captcha()` bypassa `checkCode()` — submit diretto del form | `browser_session.py · submit_captcha()` | 🔴 Alta |
| 4 | jQuery 1.4.2 — fingerprint esposto, nessun impatto funzionale | `all_sg_new.js` | 🟡 Media |
| 5 | Matomo traccia le sessioni automatizzate come utenti reali | `app.js` | 🟡 Media |
| 6 | Ambiguità tra `CloseSessions` e `CloseSession` | `browser_session.py · _recover_locked_session()` | 🟡 Media |
| 7 | UA del worker non riconosciuto da `browser_detection.js` | `browser_detection.js` | 🟢 Miglioramento |
| 8 | Endpoint immagine CAPTCHA accessibile via GET diretto | `browser_session.py · capture_captcha_image()` | 🟢 Miglioramento |

---

## Finding priorità alta

### 1 — Cookie WINID non inizializzato prima del caricamento pagina

**File:** `browser_session.py` · `start()` / `new_context()`

**Descrizione**

`window.js` esegue all'avvio di ogni pagina con questa logica:

```javascript
if (window.name == "") {
  ts = new Date();
  window.name = ts.getMilliseconds() + ts.getSeconds() + ts.getMinutes() + ts.getHours();
  setWinid(); // scrive cookie WINID
}
window.onfocus = setWinid;
```

Il contesto Playwright nasce senza `window.name` impostato, quindi:

- ad ogni navigazione `window.name` è vuoto
- il cookie `WINID` viene riscritto con un valore diverso a ogni pagina caricata
- il portale usa `WINID` per distinguere le tab attive — un valore che cambia a sessione aperta può causare comportamenti inconsistenti sulla gestione multi-tab di SISTER

Il token generato non ha entropia sufficiente (concatenazione stringa di millisecondi+secondi+minuti+ore, non somma numerica), ma il problema principale è l'instabilità per tutta la sessione.

**Correzione**

In `start()`, dopo `new_page()`, iniettare uno script di init che imposta `window.name` prima che qualsiasi JS di pagina venga eseguito:

```python
async def start(self) -> None:
    self._playwright = await async_playwright().start()
    self._browser = await self._playwright.chromium.launch(headless=self.config.headless)
    self._context = await self._browser.new_context(accept_downloads=True)
    # imposta window.name stabile prima che window.js lo sovrascriva
    await self._context.add_init_script("window.name = 'gaia-worker-1';")
    self._page = await self._context.new_page()
```

Il valore deve essere stabile per tutta la sessione. Se il worker gestisce sessioni parallele, usare un identificatore unico per contesto (es. `f"gaia-worker-{uuid4().hex[:8]}"`).

---

### 2 — Delay CAPTCHA reload fisso — race condition con la sessione server

**File:** `visura_flow.py` · `capture_captcha_image()` — `window.js reload()`

**Descrizione**

Il commento nel codice sorgente di `window.js` è esplicito:

```javascript
function reload() {
    var r2 = Math.random();
    document.getElementById("imgCaptcha").src = "/Visure/captcha?lang="+lang+"&type=i&"+r2;
    // serve per dare il tempo all'immagine di essere generata e creare il codice corretto in sessione
    setTimeout('StartMeUp()', 1000);
}
```

Il timeout di 1 secondo esiste perché il server ha latenza nell'aggiornare il codice CAPTCHA in sessione dopo aver generato la nuova immagine. Se il worker:

1. riceve un CAPTCHA errato
2. provoca un reload dell'immagine (via `reloadImg()` invece di `reload()`)
3. cattura subito la nuova immagine

ottiene un'immagine visivamente aggiornata, ma il codice in sessione server è ancora quello precedente. Il CAPTCHA appare corretto visivamente ma viene rifiutato dal portale — failure intermittente non riproducibile in debug.

Questa è la causa più probabile dei fallimenti CAPTCHA intermittenti già documentati nel runbook.

**Correzione**

Dopo ogni tentativo CAPTCHA fallito, attendere il riallineamento sessione/immagine prima di catturare il nuovo CAPTCHA. Opzione 1 — delay esplicito:

```python
async def reload_captcha(self) -> None:
    """Ricarica immagine e audio CAPTCHA attendendo il riallineamento sessione."""
    await self.page.evaluate("reload()")   # chiama reload() di window.js
    await asyncio.sleep(1.2)              # attesa > 1000ms del setTimeout server-side
```

Opzione 2 — wait su cambio `src` (più robusta):

```python
async def reload_captcha(self) -> None:
    old_src = await self.page.get_attribute(
        self.selectors.captcha_image_selector, "src"
    )
    await self.page.evaluate("reloadImg()")
    await self.page.wait_for_function(
        f"document.getElementById('imgCaptcha').src !== '{old_src}'"
    )
    await asyncio.sleep(1.2)  # attesa riallineamento codice sessione
```

Aggiornare `visura_flow.py` per chiamare `browser.reload_captcha()` invece di procedere direttamente alla cattura successiva.

---

### 3 — `submit_captcha()` bypassa `checkCode()` — submit diretto del form

**File:** `browser_session.py` · `submit_captcha()` · `inoltra_button_selector`

**Descrizione**

Il worker compila `#inCaptchaChars` e clicca il pulsante Inoltra. Il form è strutturato così:

```html
<form name="InoltraRichiestaVisForm" method="post"
      action="/Visure/vpart/InoltraRichiestaVis.do"
      onsubmit="this.inoltra.disabled=true;" id="TipoVisuraForm">
  ...
  <input type="submit" name="inoltra" value="Inoltra">
```

Il click su `Inoltra` dovrebbe scatenare `checkCode()` (definita inline nella pagina), che:

1. chiama `checkcode.jsp?code=<valore>&r=<random>` via XHR
2. solo se la risposta è diversa da `'false'` esegue `document.formcaptcha.submit()`

Se Playwright risolve il click come submit diretto senza eseguire i listener JS del form, la validazione `checkcode.jsp` viene saltata. Il finding è correlato alla vulnerabilità VUL-002 già documentata (CAPTCHA bypassabile lato client): il comportamento del worker dipende da se il server validi il CAPTCHA indipendentemente dal pre-check client.

**Correzione**

Verificare con un trace di rete Playwright che la chiamata a `checkcode.jsp` avvenga effettivamente prima del POST a `InoltraRichiestaVis.do`:

```python
async def submit_captcha(self, text: str) -> bool:
    page = self.page
    # intercetta per verificare se checkcode.jsp viene chiamato
    captcha_checked = False

    async def on_request(request):
        nonlocal captcha_checked
        if "checkcode.jsp" in request.url:
            captcha_checked = True

    page.on("request", on_request)
    await page.fill(self.selectors.captcha_field_selector, text)
    # chiamare checkCode() esplicitamente garantisce il flusso JS
    await page.evaluate("checkCode()")
    # ... resto del metodo
```

Se si conferma che il server valida il CAPTCHA indipendentemente, documentare nel runbook come assunzione verificata e lasciare il click diretto. Se invece `checkcode.jsp` è necessario, usare `page.evaluate("checkCode()")` invece del click.

---

## Finding priorità media

### 4 — jQuery 1.4.2 — fingerprint esposto, nessun impatto funzionale

**File:** `all_sg_new.js` · `window.jQuery.fn.jquery`

**Descrizione**

La pagina espone `window.jQuery.fn.jquery === "1.4.2"` (febbraio 2010), accessibile da qualsiasi `page.evaluate()`. Non causa problemi diretti al worker, ma conferma che il portale non usa API DOM moderne. `window.$` e `window.jQuery` sono disponibili e stabili per tutta la durata della sessione.

**Azione consigliata**

Aggiungere al runbook: usare `await page.evaluate("typeof $ !== 'undefined'")` come guard per verificare che jQuery sia caricato prima di usarlo in evaluate. Alternativa a `wait_for_load_state` come check di DOM readiness:

```python
await page.wait_for_function("typeof $ !== 'undefined' && $.fn.jquery === '1.4.2'")
```

---

### 5 — Matomo traccia le sessioni automatizzate come utenti reali

**File:** `app.js` · `etws-analytics.sogei.it/piwik/` · SiteId 5

**Descrizione**

`app.js` inietta il tracker Matomo self-hosted su `etws-analytics.sogei.it`. Ogni navigazione del worker genera:

- `trackPageView` per ogni pagina caricata
- `enableLinkTracking` attivo

In batch intensivi (centinaia di visure) questo produce spike anomali nelle metriche di utilizzo del portale, potenzialmente interpretabili come attività sospetta da chi monitora le analytics di Sogei.

**Correzione**

Bloccare il dominio nel contesto Playwright — una riga in `start()`:

```python
async def start(self) -> None:
    # ...
    self._context = await self._browser.new_context(accept_downloads=True)
    await self._context.add_init_script("window.name = 'gaia-worker-1';")
    # blocca il tracker analytics: nessun impatto sul flusso visura
    await self._context.route(
        "**/etws-analytics.sogei.it/**",
        lambda route: route.abort()
    )
    self._page = await self._context.new_page()
```

---

### 6 — Ambiguità tra `CloseSessions` e `CloseSession`

**File:** `browser_session.py` · `_recover_locked_session()` · `browser_close.js` · runbook

**Descrizione**

Sono state rilevate tre varianti dell'endpoint di chiusura sessione:

| Sorgente | URL |
|---|---|
| `browser_close.js` (commentato) | `/Servizi/CloseSessions` (plurale) |
| `closejs.js` (attivo) | `<WATRACE_url>/CloseSession` (singolare) |
| Runbook SISTER | `CloseSessionsSis` |

Non è chiaro quale sia l'endpoint canonico usato da `_recover_locked_session()` e quale risponda correttamente nel caso di sessione bloccata (`error_locked.jsp`).

**Azione consigliata**

Nel prossimo debug cycle con sessione bloccata, loggare l'URL esatto raggiunto e la risposta HTTP:

```python
async def _recover_locked_session(self) -> None:
    page = self.page
    logger.info("Tentativo chiusura sessione SISTER già attiva")
    # loggare URL corrente prima del click
    logger.info("URL pre-close: %s", page.url)
    close_link = page.get_by_role("link", name="Chiudi")
    if await close_link.count() > 0:
        await close_link.first.click()
        logger.info("URL post-click-chiudi: %s", page.url)
    else:
        target_url = "https://sister3.agenziaentrate.gov.it/Servizi/CloseSessionsSis"
        await page.goto(target_url)
        logger.info("URL post-goto: %s", page.url)
    await self._trace_state("session-recovery-close")
```

Aggiornare il runbook con l'URL canonico confermato e aggiungere un artifact `trace-session-close-confirmed.*`.

---

## Miglioramenti

### 7 — UA del worker non riconosciuto da `browser_detection.js`

**File:** `browser_detection.js` · `BrowserDetect.browser`

**Descrizione**

`browser_detection.js` non riconosce Chrome né Edge moderni. Playwright con UA default (Chromium headless) viene classificato come `"Mozilla"` o `"An unknown browser"`. Non impatta il flusso attuale perché `browser_close.js` ha `attachEvent()` vuota e tutto il codice di branching per browser è commentato. Potrebbe causare problemi se AdE dovesse riabilitare quei branch.

**Azione consigliata**

Documentare nel runbook:

- `BrowserDetect.browser` restituisce `"Mozilla"` per il worker Playwright
- `browser_close.js` è attualmente inerte: `function attachEvent(){}` (corpo vuoto)
- il codice di chiusura sessione via coordinate mouse (IE6/IE7) è in un blocco `/* ... */` e non viene eseguito

Nessuna azione correttiva urgente.

---

### 8 — Endpoint immagine CAPTCHA accessibile via GET diretto

**File:** `browser_session.py` · `capture_captcha_image()` · `/Visure/captcha?type=i`

**Descrizione**

Il worker cattura il CAPTCHA con:

```python
async def capture_captcha_image(self) -> bytes:
    await self.page.wait_for_selector(self.selectors.captcha_image_selector)
    return await self.page.locator(self.selectors.captcha_image_selector).screenshot(type="png")
```

Questo produce uno screenshot del DOM element, che include il rendering CSS (bordi, ombre, background) e dipende dalla viewport. L'endpoint `/Visure/captcha?lang=it&type=i` restituisce il PNG grezzo della sessione corrente via GET autenticata — immagine più pulita per Tesseract OCR.

**Azione consigliata**

Valutare il fetch diretto come alternativa:

```python
async def capture_captcha_image(self) -> bytes:
    """Cattura l'immagine CAPTCHA via GET diretto — PNG grezzo senza artefatti CSS."""
    import random
    response = await self.page.context.request.get(
        f"/Visure/captcha?lang=it&type=i&{random.random()}"
    )
    if response.ok:
        return await response.body()
    # fallback a screenshot DOM element
    await self.page.wait_for_selector(self.selectors.captcha_image_selector)
    return await self.page.locator(self.selectors.captcha_image_selector).screenshot(type="png")
```

La sessione Playwright condivide i cookie con la page, quindi l'endpoint restituisce il CAPTCHA corrente. Confrontare i tassi OCR tra i due metodi su un campione di sessioni prima di adottare il cambio.

---

## Note operative

### Cookie rilevanti da preservare nella sessione

| Cookie | Gestione | Scopo |
|---|---|---|
| `JSESSIONID` | Automatica (Playwright) | Sessione Java server-side |
| `WINID` | Da inizializzare (finding 1) | Window token per gestione tab |
| `WATRACE` | Automatica | Lista servizi per logout multi-app |

### Endpoint mappati dagli script JS

| Endpoint | Metodo | Scopo |
|---|---|---|
| `/Visure/captcha?lang=it&type=i` | GET | Immagine CAPTCHA |
| `/Visure/captcha?lang=it&type=a` | GET | Audio CAPTCHA |
| `checkcode.jsp?code=X&r=Y` | GET | Pre-validazione CAPTCHA (lato client) |
| `/Visure/vpart/InoltraRichiestaVis.do` | POST | Submit form visura |
| `/Visure/vimm/IndietroDatiImm.do` | POST | Torna indietro |
| `/Servizi/CloseSessions` | GET | Chiusura sessione (da browser_close.js) |
| `etws-analytics.sogei.it/piwik/matomo.php` | GET | Tracking analytics (da bloccare) |

---

*Documento prodotto nel contesto di analisi degli script JS del portale SISTER per il worker GAIA Catasto/Elaborazioni.*
*Aggiornare questo documento dopo ogni sessione di debug che conferma o smentisce i finding.*
