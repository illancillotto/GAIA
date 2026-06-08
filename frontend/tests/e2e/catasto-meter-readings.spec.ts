import { expect, test, type Page } from "@playwright/test";
import * as XLSX from "xlsx";

function buildMeterReadingsWorkbookBuffer(): Buffer {
  const worksheet = XLSX.utils.aoa_to_sheet([
    [],
    ["ID", "PUNTO_CONS", "COD_CONT", "LETTURA FINALE 2024", "LETTURA FINALE 2025", "TOTALE m3 2025", "COD. FISC", "NOTE"],
    [1, "PC-001", "MTR-001", 100, 125, 25, "RSSMRA80A01H501U", "ok"],
  ]);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Foglio1");
  return XLSX.write(workbook, { type: "buffer", bookType: "xlsx" }) as Buffer;
}

async function loginAsAdmin(page: Page) {
  const username = process.env.PLAYWRIGHT_ADMIN_USERNAME ?? "admin";
  const password = process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? "#0r1st4n3s1";

  await page.goto("/login");
  await page.getByLabel("Username o email").fill(username);
  await page.locator("input#password").fill(password);
  await page.getByRole("button", { name: "Accedi alla piattaforma" }).click();
  await page.waitForURL("**/");
}

test("catasto meter readings page shows list and opens detail drawer", async ({ page }) => {
  await loginAsAdmin(page);

  await page.route("**/api/catasto/meter-readings?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            id: "00000000-0000-0000-0000-000000000701",
            import_id: "00000000-0000-0000-0000-000000000702",
            distretto_id: "00000000-0000-0000-0000-000000000703",
            anno: 2025,
            row_number: 2,
            excel_id: "1",
            punto_consegna: "PC-001",
            matricola: "MTR-001",
            sigillo: null,
            tipologia_idrante: "Flangia",
            firmware_version: null,
            battery_level: "45%",
            lettura_iniziale: "100.000",
            lettura_finale: "125.000",
            consumo_mc: "25.000",
            data_lettura: "2025-03-15",
            operatore_lettura: "Operatore A",
            intervento_da_eseguire: null,
            intervento_eseguito: null,
            operatore_intervento: null,
            data_intervento: null,
            dui: null,
            codice_fiscale: "RSSMRA80A01H501U",
            codice_fiscale_normalizzato: "RSSMRA80A01H501U",
            subject_id: "00000000-0000-0000-0000-000000000704",
            subject_display_name: "Rossi Mario",
            coltura: "Mais",
            tariffa: "T1",
            fondo_chiuso: null,
            telefono: null,
            note: "ok",
            validation_status: "valid",
            validation_messages: [],
            source: "excel",
            mobile_session_id: null,
            gps_lat: null,
            gps_lng: null,
            photo_url: null,
            offline_created_at: null,
            synced_at: null,
            sync_status: null,
            device_id: null,
            mobile_operator_id: null,
            created_at: "2026-05-15T10:00:00Z",
            updated_at: "2026-05-15T10:00:00Z",
          },
        ],
        total: 1,
        page: 1,
        page_size: 50,
      }),
    });
  });

  await page.route("**/api/catasto/meter-readings/00000000-0000-0000-0000-000000000701", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "00000000-0000-0000-0000-000000000701",
        import_id: "00000000-0000-0000-0000-000000000702",
        distretto_id: "00000000-0000-0000-0000-000000000703",
        anno: 2025,
        row_number: 2,
        excel_id: "1",
        punto_consegna: "PC-001",
        matricola: "MTR-001",
        sigillo: null,
        tipologia_idrante: "Flangia",
        firmware_version: null,
        battery_level: "45%",
        lettura_iniziale: "100.000",
        lettura_finale: "125.000",
        consumo_mc: "25.000",
        data_lettura: "2025-03-15",
        operatore_lettura: "Operatore A",
        intervento_da_eseguire: null,
        intervento_eseguito: null,
        operatore_intervento: null,
        data_intervento: null,
        dui: null,
        codice_fiscale: "RSSMRA80A01H501U",
        codice_fiscale_normalizzato: "RSSMRA80A01H501U",
        subject_id: "00000000-0000-0000-0000-000000000704",
        subject_display_name: "Rossi Mario",
        coltura: "Mais",
        tariffa: "T1",
        fondo_chiuso: null,
        telefono: null,
        note: "ok",
        validation_status: "valid",
        validation_messages: [],
        source: "excel",
        mobile_session_id: null,
        gps_lat: null,
        gps_lng: null,
        photo_url: null,
        offline_created_at: null,
        synced_at: null,
        sync_status: null,
        device_id: null,
        mobile_operator_id: null,
        created_at: "2026-05-15T10:00:00Z",
        updated_at: "2026-05-15T10:00:00Z",
      }),
    });
  });

  await page.goto("/catasto/letture-contatori");

  await expect(page.getByText("Registro letture Catasto")).toBeVisible();
  await expect(page.getByText("PC-001")).toBeVisible();
  await expect(page.getByText("Rossi Mario")).toBeVisible();

  await page.getByText("PC-001").click();
  await expect(page.getByText("Dettaglio lettura")).toBeVisible();
  await expect(page.getByText("Operatore A")).toBeVisible();
  await expect(page.getByText("Mais")).toBeVisible();
});

test("catasto meter readings detail validates warning reading with confirmation", async ({ page }) => {
  await loginAsAdmin(page);

  const warningReading = {
    id: "00000000-0000-0000-0000-000000000711",
    import_id: "00000000-0000-0000-0000-000000000712",
    distretto_id: "00000000-0000-0000-0000-000000000703",
    anno: 2025,
    row_number: 3,
    excel_id: "2",
    punto_consegna: "PC-WARN-001",
    matricola: "MTR-WARN-001",
    sigillo: null,
    record_type: "CONT_NO_TES",
    record_kind: "meter_reading",
    operational_state: "active",
    tipologia_idrante: "Flangia",
    firmware_version: null,
    battery_level: "10%",
    lettura_iniziale: "200.000",
    lettura_finale: "240.000",
    consumo_mc: "40.000",
    data_lettura: "2025-04-10",
    operatore_lettura: "Operatore B",
    intervento_da_eseguire: null,
    intervento_eseguito: null,
    operatore_intervento: null,
    data_intervento: null,
    dui: null,
    codice_fiscale: "RSSMRA80A01H501U",
    codice_fiscale_normalizzato: "RSSMRA80A01H501U",
    subject_id: "00000000-0000-0000-0000-000000000704",
    subject_display_name: "Rossi Mario",
    coltura: "Mais",
    tariffa: "T1",
    fondo_chiuso: null,
    telefono: null,
    note: "ok",
    validation_status: "warning",
    validation_messages: [{ level: "warning", code: "BATTERIA_BASSA", message: "Batteria bassa", field: "battery_level" }],
    source: "excel",
    mobile_session_id: null,
    gps_lat: null,
    gps_lng: null,
    photo_url: null,
    offline_created_at: null,
    synced_at: null,
    sync_status: null,
    device_id: null,
    mobile_operator_id: null,
    manual_corrections: null,
    manual_override_updated_at: null,
    manual_override_updated_by: null,
    manual_audits: [],
    created_at: "2026-05-15T10:00:00Z",
    updated_at: "2026-05-15T10:00:00Z",
  };

  await page.route("**/api/catasto/meter-readings?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        record_tab_counts: { meter: 1, other: 0 },
        operational_counts: { all: 1, unlinked: 0, activities: 0, dismissed: 0, lowBattery: 1 },
        validation_counts: { all: 1, valid: 0, warning: 1, error: 0 },
        items: [warningReading],
        total: 1,
        page: 1,
        page_size: 50,
      }),
    });
  });

  await page.route("**/api/catasto/meter-readings/00000000-0000-0000-0000-000000000711", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(warningReading),
    });
  });

  await page.route("**/api/catasto/meter-readings/00000000-0000-0000-0000-000000000711/validate", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...warningReading,
        validation_status: "valid",
        validation_messages: [],
        manual_override_updated_at: "2026-06-08T09:00:00Z",
        manual_override_updated_by: 1,
        manual_audits: [
          {
            id: "00000000-0000-0000-0000-000000000799",
            meter_reading_id: warningReading.id,
            changed_by: 1,
            changed_by_display_name: "admin",
            change_note: "Validazione manuale lettura confermata.",
            previous_values: {
              validation_status: "warning",
              validation_messages: [{ level: "warning", code: "BATTERIA_BASSA", message: "Batteria bassa", field: "battery_level" }],
            },
            new_values: {
              validation_status: "valid",
              validation_messages: [],
            },
            changed_at: "2026-06-08T09:00:00Z",
          },
        ],
      }),
    });
  });

  await page.goto("/catasto/letture-contatori");
  await page.getByText("PC-WARN-001").click();

  await expect(page.getByRole("button", { name: "Valida lettura" })).toBeVisible();
  await page.getByRole("button", { name: "Valida lettura" }).click();
  await expect(page.getByText("Confermare validazione lettura?")).toBeVisible();
  await page.getByRole("button", { name: "Valida lettura" }).last().click();

  await expect(page.getByText("Correzione manuale presente")).toBeVisible();
  await expect(page.getByText("Storico correzioni")).toBeVisible();
  await expect(page.getByText("Validazione manuale lettura confermata.")).toBeVisible();
});

test("catasto meter readings import page validates and imports workbook", async ({ page }) => {
  await loginAsAdmin(page);

  await page.route("**/api/catasto/distretti", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "00000000-0000-0000-0000-000000000703",
          num_distretto: "1",
          nome_distretto: "Sinis",
          attivo: true,
        },
      ]),
    });
  });

  await page.route("**/api/catasto/meter-readings/import/validate**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        anno: 2025,
        distretto_id: "00000000-0000-0000-0000-000000000703",
        distretto_numero: "1",
        distretto_nome: "Sinis",
        filename: "D01-Sinis 2025.xlsx",
        totale_righe: 1,
        righe_valide: 1,
        righe_con_warning: 0,
        righe_con_errori: 0,
        items: [
          {
            row_number: 3,
            punto_consegna: "PC-001",
            codice_fiscale: "RSSMRA80A01H501U",
            codice_fiscale_normalizzato: "RSSMRA80A01H501U",
            subject_id: "00000000-0000-0000-0000-000000000704",
            subject_display_name: "Rossi Mario",
            validation_status: "valid",
            validation_messages: [],
            data: {
              punto_consegna: "PC-001",
            },
          },
        ],
      }),
    });
  });

  await page.route("**/api/catasto/meter-readings/import?**", async (route) => {
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        import_id: "00000000-0000-0000-0000-000000000702",
        anno: 2025,
        distretto_id: "00000000-0000-0000-0000-000000000703",
        stato: "completed",
        totale_righe: 1,
        righe_importate: 1,
        righe_con_warning: 0,
        righe_scartate: 0,
      }),
    });
  });

  await page.goto("/catasto/letture-contatori/import");

  await expect(page.getByText("Import Excel letture")).toBeVisible();

  await page.getByLabel("File Excel").setInputFiles({
    name: "D01-Sinis 2025.xlsx",
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    buffer: buildMeterReadingsWorkbookBuffer(),
  });

  await page.getByRole("button", { name: "Valida file" }).click();
  await expect(page.getByText("Report validazione")).toBeVisible();
  await expect(page.getByText("D01-Sinis 2025.xlsx")).toBeVisible();
  await expect(page.locator("div.rounded-xl.bg-emerald-50").getByText("Valide")).toBeVisible();
  await expect(page.locator("div.rounded-xl.bg-emerald-50").getByText("1")).toBeVisible();

  await page.getByRole("button", { name: "Importa letture" }).click();
  await expect(page.getByText("Import completato: 1 righe salvate, 0 con warning, 0 scartate.")).toBeVisible();
});
