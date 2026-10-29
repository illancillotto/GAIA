"""Printed notice identity, public links and readable layout on the real PDF."""

import html

import pytest

from app.modules.ruolo.services import tributi_reminder_service as service
from app.services.elaborazioni_credentials import get_credential_fernet


def _payload(years: list[int]) -> dict:
    return {
        "notice_number": "12026212500001",
        "notice_emission_year": 2026,
        "codice_fiscale": "RSSMRA80A01H501Z",
        "display_name": "AZIENDA AGRICOLA ROSSI E FIGLI DI MARIO ROSSI",
        "years": years,
        "saldo_amount": "210.00 EUR",
        "due_date": "2026-11-30",
        "template_path": service.GAIA_PROPOSAL_TEMPLATE_KEY,
        "bollettino_version": "v2",
        "avvisi": [
            {
                "anno_tributario": year,
                "codice_cnc": f"01.020{year}000364253",
                "residenza_raw": "VIA ROMA 1 09170 ORISTANO (OR)",
                "importo_totale_euro": "100.00 EUR",
                "saldo_amount": "42.00 EUR",
                "rateization_fee_amount": "10.00 EUR",
            }
            for year in years
        ],
    }


def test_first_page_groups_requested_content_and_omits_internal_notification_code() -> None:
    rendered = service._gaia_proposal_html(_payload([2024, 2025]))
    front = rendered.split('<section class="page front">')[1].split("</section>")[0]
    header = front.split('<div class="header">')[1].split('<div class="notice-title">')[0]
    amount = front.split('<div class="amount">')[1].split('<div class="instructions">')[0]

    assert header.index('class="brand cbo"') < header.index('class="brand anbi"')
    assert "Logo ANBI" in header and "pagoPA" not in header
    assert header.count('class="logo-image"') == 2
    assert (
        "Si può richiedere, direttamente presso gli uffici dell\N{RIGHT SINGLE QUOTATION MARK}Ente, una diversa dilazione del pagamento"
        in html.unescape(amount)
    )
    assert front.count("una diversa dilazione del pagamento") == 1
    assert "effettuato anche mediante bonifico" in front
    assert (
        "<b>intestato a:</b> Consorzio di Bonifica dell'Oristanese - Riscossione quote associative"
        in front
    )
    assert "SN01" not in front and "Spese Notifica" in front and "11,55" in front
    assert (
        front.index('class="portal-access"')
        < front.index("Per maggiori chiarimenti")
        < front.index("È possibile consultare il sito")
    )
    assert front.index("È possibile consultare il sito") < front.index('class="notice-services"')
    assert "delle proprietà assoggettate a tributo, degli indici applicati nel calcolo" in front
    assert "normativa inerente l\u2019attività istituzionale dell\u2019Ente." in html.unescape(
        front
    )
    assert "Lunedi e giovedì 11.00 - 13.00, - tel. 0783 3150212." in front
    assert front.index('class="notice-services"') < front.index('class="privacy"')
    assert "Comunicazioni e aggiornamenti sulle attività del Consorzio" in front
    assert 'class="notice-service irrighiamo"' in front
    assert "Irrighiamo Insieme" in front
    assert (
        "L'applicazione del Consorzio per segnalare guasti o rotture e richiedere l'autorizzazione all'irrigazione."
        in front
    )
    assert "https://login.bonificaoristanese.it/" in front
    assert "beni soggetti a contributo consortile e gli avvisi di pagamento" in front
    assert 'class="notice-service taxpayer-portal"' not in front
    assert "Apri il canale WhatsApp" not in front
    assert "Per ottenere i dati di accesso contattare gli uffici del Consorzio" in front
    assert '<div class="rateization-note">' in front


@pytest.mark.parametrize("mode", ["fixed_date", "notification_60_days"])
def test_notice_print_uses_requested_blue_and_coordinated_shades(mode):
    from playwright.sync_api import sync_playwright

    payload = {**_payload([2021]), "payment_deadline_mode": mode}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=service._find_chromium_binary())
        try:
            page = browser.new_page()
            page.emulate_media(media="print")
            page.set_content(service._gaia_proposal_html(payload))
            styles = page.evaluate("""() => {
                const properties = ['color', 'backgroundColor', 'borderTopColor', 'backgroundImage'];
                const selectors = ['.notice-title', '.card h2', '.amount', '.amount .label',
                    '.amount .euro', '.instructions h2', '.summary th', '.portal-access h2',
                    '.notice-service h2', '.partitario-title', '.rateization-note',
                    '.payment-deadline', '.attention-icon'];
                return Object.fromEntries(selectors.map(selector => {
                    const element = document.querySelector(selector);
                    return [selector, element ? Object.fromEntries(properties.map(property =>
                        [property, getComputedStyle(element)[property]])) : null];
                }));
            }""")
            font_families = page.locator(".front").evaluate("""front => {
                const walker = document.createTreeWalker(front, NodeFilter.SHOW_TEXT);
                const families = new Set();
                while (walker.nextNode()) {
                    const node = walker.currentNode;
                    if (node.textContent.trim()) families.add(getComputedStyle(node.parentElement).fontFamily);
                }
                return [...families];
            }""")
        finally:
            browser.close()
    primary = "rgb(43, 87, 147)"
    for selector in (
        ".card h2",
        ".amount .label",
        ".amount .euro",
        ".instructions h2",
        ".summary th",
        ".portal-access h2",
        ".notice-service h2",
        ".partitario-title",
    ):
        assert styles[selector]["color"] == primary, selector
    assert styles[".notice-title"]["backgroundImage"] == (
        "linear-gradient(90deg, rgb(43, 87, 147), rgb(62, 114, 179))"
    )
    assert styles[".amount"]["backgroundColor"] == "rgb(242, 246, 250)"
    assert styles[".amount"]["borderTopColor"] == primary
    assert styles[".portal-access h2"]["backgroundColor"] == "rgb(234, 240, 247)"
    assert styles[".summary th"]["backgroundColor"] == "rgb(240, 244, 249)"
    assert styles[".summary th"]["borderTopColor"] == "rgb(204, 215, 229)"
    assert styles[".rateization-note"]["color"] == "rgb(36, 74, 125)"
    assert font_families == ["Arial, Helvetica, sans-serif"]
    if mode == "notification_60_days":
        assert styles[".payment-deadline"]["backgroundColor"] == "rgb(242, 246, 250)"
        assert styles[".payment-deadline"]["borderTopColor"] == primary
        assert styles[".attention-icon"]["color"] == "rgb(198, 40, 40)"
        assert styles[".attention-icon"]["backgroundColor"] == "rgba(0, 0, 0, 0)"


@pytest.mark.parametrize(
    "years,access_count", [([2021], 1), ([2024, 2025], 0), ([2021, 2022, 2023, 2024, 2025], 2)]
)
def test_print_keeps_two_intro_pages_and_scannable_footer_links(
    years, access_count, tmp_path
) -> None:
    pymupdf = pytest.importorskip("pymupdf")
    zxingcpp = pytest.importorskip("zxingcpp")
    pil_image = pytest.importorskip("PIL.Image")
    if service._find_chromium_binary() is None:
        pytest.skip("Chromium richiesto per verificare la stampa reale")
    output = tmp_path / "avviso.pdf"
    payload = _payload(years)
    payload["taxpayer_portal_access"] = [
        {
            "account_code": f"000000{n}",
            "pin_encrypted": get_credential_fernet().encrypt(f"001234{n}".encode()).decode(),
        }
        for n in range(access_count)
    ]
    service.generate_batch_reminder_pdf(payload, output_path=output)
    with pymupdf.open(output) as document:
        front, legal = document[0], document[1]
        front_text = " ".join(front.get_text().split())
        assert "PER CONSULTARE LA PROPRIA POSIZIONE" in front_text
        assert "Cartella contribuenza" in front_text
        assert (
            "L'applicazione del Consorzio per segnalare guasti o rotture e richiedere l'autorizzazione all'irrigazione."
            in front_text
        )
        assert "Apri il canale WhatsApp" not in front_text
        for n in range(access_count):
            assert (f"000000{n}" in front_text) == (access_count == 1)
            assert (f"001234{n}" in front_text) == (access_count == 1)
        assert ("contattare gli uffici" in front_text) == (access_count != 1)
        assert "Comunicazioni per il Contribuente" in legal.get_text()
        assert "Dettaglio partitario allegato" in document[2].get_text()
        assert len(document) == 4
        links = {link["uri"] for link in front.get_links()}
        assert {
            "https://whatsapp.com/channel/0029Vb9tZLzDJ6H3keAt9h24",
            "https://incatasto.servizicapacitas.com/pages/main.aspx?cons=090",
            "https://login.bonificaoristanese.it/",
        } <= links
        # Decode each QR from its printed position at 144 dpi, not from the input PNGs.
        images = front.get_image_info()
        # Chromium also rasterizes the title gradient; select logos and QR images by position.
        top = sorted(
            [item for item in images if item["bbox"][3] < 95], key=lambda item: item["bbox"][0]
        )
        bottom = sorted(
            [item for item in images if item["bbox"][1] > front.rect.height / 2],
            key=lambda item: item["bbox"][0],
        )
        assert len(top) == 2 and len(bottom) == 2
        assert abs(bottom[0]["bbox"][1] - bottom[1]["bbox"][1]) < 1
        # The QR panels sit at the foot of page one, inside the printable margin.
        assert (
            front.rect.height - 110
            < max(item["bbox"][3] for item in bottom)
            < front.rect.height - 20
        )
        decoded = []
        for item in bottom:
            assert item["bbox"][3] < front.rect.height - 20
            raster = front.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=pymupdf.Rect(item["bbox"]))
            image = pil_image.frombytes("RGB", (raster.width, raster.height), raster.samples)
            decoded.append([symbol.text for symbol in zxingcpp.read_barcodes(image)])
        assert decoded == [
            ["https://whatsapp.com/channel/0029Vb9tZLzDJ6H3keAt9h24"],
            ["https://login.bonificaoristanese.it/"],
        ]
        privacy = front.search_for("INFORMATIVA SUL TRATTAMENTO DEI DATI PERSONALI")[0]
        assert 0 < privacy.y0 - bottom[0]["bbox"][3] < 12
        text = " ".join(legal.get_text().split())
        assert text.count("Qualora le somme oggetto della presente comunicazione") == 1
        assert (
            text.index("Numero massimo di rate")
            < text.index("Qualora le somme")
            < text.index("Scadenza del Pagamento:")
        )
        # Keep the legal copy above the signature and fully inside page two.
        words = legal.get_text("words")
        assert max(word[3] for word in words) < legal.rect.height - 15
        assert (
            "La determinazione dell\N{RIGHT SINGLE QUOTATION MARK}importo residuo dovuto tiene conto dei versamenti già effettuati."
            in text
        )


@pytest.mark.parametrize("mode", ["fixed_date", "notification_60_days"])
def test_notice_amount_stays_on_one_line_inside_the_payment_box(mode):
    from playwright.sync_api import sync_playwright

    payload = {**_payload([2021]), "payment_deadline_mode": mode, "saldo_amount": "111130.33 EUR"}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=service._find_chromium_binary())
        try:
            page = browser.new_page()
            page.emulate_media(media="print")
            page.set_content(service._gaia_proposal_html(payload))
            box = page.locator(".amount .euro").evaluate("""euro => {
                const range = document.createRange();
                range.selectNodeContents(euro);
                const text = range.getBoundingClientRect();
                const parent = euro.parentElement.getBoundingClientRect();
                return {text: euro.textContent, lines: range.getClientRects().length,
                    right: text.right, parentRight: parent.right};
            }""")
        finally:
            browser.close()
    assert box["text"].startswith("€. 111.")
    assert box["lines"] == 1
    assert box["right"] <= box["parentRight"]
