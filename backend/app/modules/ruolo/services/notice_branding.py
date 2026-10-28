"""Official masthead, portal access, WhatsApp and Irrighiamo Insieme on page one."""

import base64
import html
from pathlib import Path

from app.modules.ruolo.services.taxpayer_portal_access import printable_portal_access

_ASSETS = Path(__file__).resolve().parents[1] / "assets"
WHATSAPP_CHANNEL_URL = "https://whatsapp.com/channel/0029Vb9tZLzDJ6H3keAt9h24"
TAXPAYER_PORTAL_URL = "https://incatasto.servizicapacitas.com/pages/main.aspx?cons=090"
IRRIGHIAMO_LOGIN_URL = "https://login.bonificaoristanese.it/"

NOTICE_BRANDING_CSS = """
.front { display: flex; flex-direction: column; }
.header { display: grid; grid-template-columns: 39mm 1fr 39mm; align-items: center;
  gap: 5mm; padding-bottom: 2mm; border-bottom: 1.6pt solid #2b5793; }
.brand { height: 18mm; display: flex; align-items: center; justify-content: center; }
.brand .logo-image { display: block; width: 100%; height: 100%; object-fit: contain; }
.head-title { text-align: center; }
.head-title h1 { margin: 0; font-size: 19.5pt; line-height: 1.05; }
.head-title p { margin: 1mm 0 0; font-weight: 700; font-size: 10.2pt; }
.amount .installment-request { margin: 2mm 0 0; font-size: 8.5pt; line-height: 1.2; }
.front .card p { margin: 2mm 0; }
.front > .note { padding-top: 1mm; margin-top: 1mm; font-size: 8.5pt; line-height: 1.12; }
.notice-footer { margin-top: auto; padding-top: 1.5mm; break-inside: avoid; }
.notice-services { display: grid; grid-template-columns: 1fr 1fr; gap: 3mm; break-inside: avoid; }
.notice-service { display: grid; grid-template-columns: 18mm 1fr; gap: 2.5mm;
  align-items: center; border: .7pt solid #ccd7e5; border-radius: 2mm; padding: 1mm 2mm; }
.notice-service .qr { display: block; width: 18mm; height: 18mm; object-fit: contain; }
.notice-service h2 { margin: 0 0 1mm; color: #2b5793; font-size: 9pt; line-height: 1.15; }
.notice-service p { margin: 0 0 1mm; font-size: 7.8pt; line-height: 1.2; }
.notice-service a { color: #244a7d; text-decoration: underline; }
.portal-access { margin-top: 2mm; border: 1pt solid #2b5793; border-radius: 2mm;
  overflow: hidden; break-inside: avoid; }
.portal-access h2 { margin: 0; background: #eaf0f7; color: #2b5793;
  padding: 1mm 3mm; font-size: 10.2pt; }
.portal-access .portal-body { padding: 1.5mm 3mm; }
.portal-access p { margin: 0 0 .6mm; font-size: 9pt; }
.portal-access .access-row { display: inline-flex; gap: 5mm; margin-right: 7mm;
  font-size: 10.2pt; padding-top: 1mm; }
.portal-access .access-value { font-weight: 700; letter-spacing: .5pt; }
.portal-access a { color: inherit; text-decoration: none; }
.notice-footer .privacy { margin-top: 1.5mm; font-size: 7.8pt; line-height: 1.15;
  color: #344154; text-align: justify; }
"""


def _image(filename: str, alt: str, class_name: str) -> str:
    encoded = base64.b64encode((_ASSETS / filename).read_bytes()).decode("ascii")
    return (
        f'<img class="{class_name}" alt="{html.escape(alt)}" src="data:image/png;base64,{encoded}">'
    )


def notice_header_html() -> str:
    cbo = _image("notice-cbo-logo.png", "Logo Consorzio di Bonifica dell'Oristanese", "logo-image")
    anbi = _image("notice-anbi-logo.png", "Logo ANBI", "logo-image")
    return f"""<div class="header">
  <div class="brand cbo">{cbo}</div>
  <div class="head-title"><h1>Consorzio di Bonifica<br>dell'Oristanese</h1><p>DPGRS N. 239 del 04.12.96</p></div>
  <div class="brand anbi">{anbi}</div>
</div>"""


def notice_contacts_html() -> str:
    whatsapp = _image("notice-whatsapp-qr.png", "QR del canale WhatsApp del Consorzio", "qr")
    irrighiamo = _image("notice-irrighiamo-qr.png", "QR di accesso a Irrighiamo Insieme", "qr")
    return f"""<div class="notice-services">
  <div class="notice-service whatsapp">
    <a href="{WHATSAPP_CHANNEL_URL}" aria-label="Canale WhatsApp del Consorzio">{whatsapp}</a>
    <div><h2>Canale WhatsApp del Consorzio</h2>
      <p>Comunicazioni e aggiornamenti sulle attività del Consorzio. Inquadra il QR per accedere.</p>
    </div>
  </div>
  <div class="notice-service irrighiamo">
    <a href="{IRRIGHIAMO_LOGIN_URL}" aria-label="Accedi a Irrighiamo Insieme">{irrighiamo}</a>
    <div><h2>Irrighiamo Insieme</h2>
      <p>L'applicazione del Consorzio per segnalare guasti o rotture e richiedere l'autorizzazione all'irrigazione. Inquadra il QR per accedere.</p>
    </div>
  </div>
</div>"""


def notice_portal_html(payload: dict) -> str:
    accesses = printable_portal_access(payload)
    rows = "".join(
        '<div class="access-row"><span>Codice ditta: <span class="access-value">'
        f'{html.escape(account)}</span></span><span>PIN: <span class="access-value">'
        f"{html.escape(pin)}</span></span></div>"
        for account, pin in accesses
    )
    if not rows:
        rows = "<p>Per ottenere i dati di accesso contattare gli uffici del Consorzio.</p>"
    return f"""<div class="portal-access">
  <h2>PER CONSULTARE LA PROPRIA POSIZIONE</h2>
  <div class="portal-body"><p><a href="{TAXPAYER_PORTAL_URL}">www.bonificaoristanese.it &gt; Cartella contribuenza &gt;</a></p>
  <p>Consulta online i beni soggetti a contributo consortile e gli avvisi di pagamento.</p>
  {rows}</div>
</div>"""
