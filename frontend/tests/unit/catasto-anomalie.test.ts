import { describe, expect, test } from "vitest";

import { describeCatastoAnomalia, explainCatastoAnomalia } from "@/lib/catasto-anomalie";

describe("source reference descriptions", () => {
  test.each([
    [undefined, ""],
    [null, ""],
    [false, ""],
    [0, ""],
    ["", ""],
    ["ABC", "ABC"],
    [12, "12"],
    [[], ""],
    [{}, "[object Object]"],
  ])("preserves source truthiness and string conversion for %j", (value, text) => {
    const fiscal = "Il codice fiscale o la partita IVA importata non supera i controlli formali.";
    const parcel = "La riga ruolo non trova una particella corrente GAIA con lo stesso riferimento catastale.";
    const included = Boolean(value);
    expect(describeCatastoAnomalia({
      tipo: "VAL-02-cf_invalido", dati_json: { cf_raw: value, error_code: value },
    })).toBe(included ? `${fiscal} Valore sorgente: ${text}. Errore: ${text}.` : fiscal);
    expect(describeCatastoAnomalia({
      tipo: "VAL-05-particella_assente", dati_json: { foglio: value, particella: value, subalterno: value },
    })).toBe(included ? `${parcel} Foglio ${text}. Particella ${text}. Sub ${text}.` : parcel);
  });
});

describe("explainCatastoAnomalia", () => {
  test.each([
    [null, []],
    [false, []],
    ["bad", []],
    [[], []],
    [{ atteso: 0, delta: -2 }, [{ label: "Voce 0648 - valore atteso", value: "0" }, { label: "Voce 0648 - scostamento", value: "-2" }]],
    [{ atteso: "bad", delta: null }, [{ label: "Voce 0648 - scostamento", value: "0" }]],
  ])("preserves VAL-07 calculation values for %j", (value, expected) => {
    expect(explainCatastoAnomalia({
      tipo: "VAL-07-importi",
      dati_json: { v07_648: value },
    }).calculations).toEqual(expected);
  });

  test("preserves VAL-07 calculation order independently of source key order", () => {
    expect(explainCatastoAnomalia({
      tipo: "VAL-07-importi",
      dati_json: { v07_985: { delta: 4, atteso: 3 }, v07_648: { delta: 2, atteso: 1 } },
    }).calculations).toEqual([
      { label: "Voce 0648 - valore atteso", value: "1" },
      { label: "Voce 0648 - scostamento", value: "2" },
      { label: "Voce 0985 - valore atteso", value: "3" },
      { label: "Voce 0985 - scostamento", value: "4" },
    ]);
  });

  test("explains VAL-01 surface excess with calculations", () => {
    const explanation = explainCatastoAnomalia({
      tipo: "VAL-01-sup_eccede",
      dati_json: { delta_mq: 120.5, delta_pct: 0.125 },
    });

    expect(explanation.title).toContain("Superficie irrigabile");
    expect(explanation.calculations).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ label: "Scostamento in metri quadri" }),
        expect.objectContaining({ label: "Scostamento percentuale", value: "12,5%" }),
      ]),
    );
  });

  test("explains VAL-01 without optional percentage", () => {
    const explanation = explainCatastoAnomalia({
      tipo: "VAL-01-sup_eccede",
      dati_json: { delta_mq: "invalid" },
    });

    expect(explanation.calculations).toEqual([]);
  });

  test("explains VAL-02 invalid fiscal code", () => {
    const explanation = explainCatastoAnomalia({
      tipo: "VAL-02-cf_invalido",
      dati_json: { cf_raw: "BADCF", error_code: "checksum" },
    });

    expect(explanation.calculations).toEqual([
      { label: "Valore sorgente", value: "BADCF" },
      { label: "Esito controllo", value: "checksum" },
    ]);

    expect(explainCatastoAnomalia({ tipo: "VAL-02-cf_invalido" }).calculations).toEqual([]);
  });

  test("explains VAL-03 missing fiscal code", () => {
    expect(explainCatastoAnomalia({ tipo: "VAL-03-cf_mancante" }).title).toContain("mancante");
  });

  test("explains VAL-04 invalid municipality", () => {
    const explanation = explainCatastoAnomalia({
      tipo: "VAL-04-comune_invalido",
      dati_json: { cod_istat: 95038 },
    });

    expect(explanation.calculations).toEqual([{ label: "Codice comune sorgente", value: "95038" }]);
    expect(explainCatastoAnomalia({ tipo: "VAL-04-comune_invalido" }).calculations).toEqual([]);
  });

  test("explains VAL-05 missing parcel", () => {
    const explanation = explainCatastoAnomalia({
      tipo: "VAL-05-particella_assente",
      dati_json: { foglio: "12", particella: "34", subalterno: "1" },
    });

    expect(explanation.calculations).toEqual([
      { label: "Foglio", value: "12" },
      { label: "Particella", value: "34" },
      { label: "Subalterno", value: "1" },
    ]);

    expect(
      explainCatastoAnomalia({
        tipo: "VAL-05-particella_assente",
        dati_json: { foglio: "12" },
      }).calculations,
    ).toEqual([{ label: "Foglio", value: "12" }]);

    expect(
      explainCatastoAnomalia({
        tipo: "VAL-05-particella_assente",
        dati_json: { foglio: "12", subalterno: "1" },
      }).calculations,
    ).toEqual([
      { label: "Foglio", value: "12" },
      { label: "Subalterno", value: "1" },
    ]);

    expect(
      explainCatastoAnomalia({
        tipo: "VAL-05-particella_assente",
        dati_json: { particella: "34" },
      }).calculations,
    ).toEqual([{ label: "Particella", value: "34" }]);
  });

  test("explains VAL-06 imponibile with formulas and catastale note", () => {
    const explanation = explainCatastoAnomalia({
      tipo: "VAL-06-imponibile",
      dati_json: {
        sup_irrigabile_mq: 1000,
        sup_catastale_mq: 900,
        ind_spese_fisse: 0.25,
        imponibile_registrato: 250,
        atteso: 250,
        atteso_catastale: 225,
        delta: 0.5,
        delta_vs_catastale: 25,
        coincide_con_catastale: true,
      },
    });

    expect(explanation.calculations).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ label: "Superficie irrigabile" }),
        expect.objectContaining({ label: "Calcolo teorico" }),
        expect.objectContaining({ label: "Verifica con catastale" }),
        expect.objectContaining({ label: "Scostamento su catastale" }),
        expect.objectContaining({ label: "Nota" }),
      ]),
    );
  });

  test("explains VAL-06 without optional formula rows", () => {
    const explanation = explainCatastoAnomalia({
      tipo: "VAL-06-imponibile",
      dati_json: {
        sup_irrigabile_mq: "bad",
        coincide_con_catastale: false,
      },
    });

    expect(explanation.calculations).toEqual([]);
  });

  test("explains VAL-06 with irrigabile formula and catastale delta", () => {
    const explanation = explainCatastoAnomalia({
      tipo: "VAL-06-imponibile",
      dati_json: {
        sup_irrigabile_mq: 1000,
        ind_spese_fisse: 0.25,
        atteso: 250,
        delta_vs_catastale: 12.5,
        coincide_con_catastale: true,
      },
    });

    expect(explanation.calculations).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ label: "Calcolo teorico" }),
        expect.objectContaining({ label: "Scostamento su catastale" }),
      ]),
    );
    expect(explanation.calculations.some((row) => row.label === "Nota")).toBe(false);
  });

  test("explains VAL-06 adds catastale note when formulas align", () => {
    const explanation = explainCatastoAnomalia({
      tipo: "VAL-06-imponibile",
      dati_json: {
        sup_catastale_mq: 900,
        ind_spese_fisse: 0.25,
        atteso_catastale: 225,
        coincide_con_catastale: true,
      },
    });

    expect(explanation.calculations).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ label: "Verifica con catastale" }),
        expect.objectContaining({ label: "Nota" }),
      ]),
    );
  });

  test("explains VAL-07 import amounts", () => {
    const explanation = explainCatastoAnomalia({
      tipo: "VAL-07-importi",
      dati_json: {
        v07_648: { atteso: 12.3456, delta: 0.01 },
        v07_985: { atteso: 98.7654, delta: -0.02 },
      },
    });

    expect(explanation.calculations).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ label: "Voce 0648 - valore atteso" }),
        expect.objectContaining({ label: "Voce 0985 - scostamento" }),
      ]),
    );

    expect(
      explainCatastoAnomalia({
        tipo: "VAL-07-importi",
        dati_json: { v07_648: "bad", v07_985: null },
      }).calculations,
    ).toEqual([]);

    expect(
      explainCatastoAnomalia({
        tipo: "VAL-07-importi",
        dati_json: {
          v07_648: { atteso: "bad", delta: 0.01 },
          v07_985: { atteso: 1, delta: "bad" },
        },
      }).calculations,
    ).toEqual(
      expect.arrayContaining([
        { label: "Voce 0648 - scostamento", value: "0,01" },
        { label: "Voce 0985 - valore atteso", value: "1" },
      ]),
    );
  });

  test("falls back to generic explanation for unknown types", () => {
    const explanation = explainCatastoAnomalia({
      tipo: "VAL-99-custom",
      descrizione: "Anomalia custom",
    });

    expect(explanation.title).toBe("Anomalia custom");
    expect(explanation.summary).toBe("Anomalia custom");
    expect(explanation.calculations).toEqual([]);

    expect(explainCatastoAnomalia({ tipo: "VAL-99-custom" }).summary).toContain("incoerenza");
  });
});

describe("describeCatastoAnomalia", () => {
  test.each([
    [undefined, ""], [null, ""], ["bad", ""], [0, ""], [false, ""],
    [[], ""], [{}, ""], [{ atteso: null, delta: undefined }, ""],
    [{ atteso: 0, delta: 0 }, "il valore atteso e 0. lo scostamento e 0."],
    [{ atteso: "12.34567", delta: -0.00015 }, "il valore atteso e 12,3457. lo scostamento e -0,0002."],
    [{ atteso: "bad", delta: Infinity }, "il valore atteso e null. lo scostamento e null."],
    [{ atteso: "", delta: false }, "il valore atteso e 0. lo scostamento e 0."],
    [{ atteso: 2 }, "il valore atteso e 2."],
    [{ delta: -2 }, "lo scostamento e -2."],
  ])("preserves VAL-07 voice values and exact formatting for %j", (value, detail) => {
    const summary = "Gli importi del ruolo non coincidono con quelli che risultano dal calcolo su imponibile e aliquota.";
    for (const [key, code] of [["v07_648", "0648"], ["v07_985", "0985"]]) {
      const anomalia = { tipo: "VAL-07-importi", dati_json: { [key]: value } };
      const original = structuredClone(anomalia);
      const suffix = detail ? ` Per la voce ${code} ${detail.replace(" lo scostamento", ` Per la voce ${code} lo scostamento`)}` : "";
      expect(describeCatastoAnomalia(anomalia)).toBe(summary + suffix);
      expect(anomalia).toEqual(original);
    }
  });

  test("preserves VAL-07 voice and field order with all values", () => {
    expect(describeCatastoAnomalia({
      tipo: "VAL-07-importi",
      dati_json: { v07_985: { delta: 4, atteso: 3 }, v07_648: { delta: 2, atteso: 1 } },
    })).toBe("Gli importi del ruolo non coincidono con quelli che risultano dal calcolo su imponibile e aliquota. Per la voce 0648 il valore atteso e 1. Per la voce 0648 lo scostamento e 2. Per la voce 0985 il valore atteso e 3. Per la voce 0985 lo scostamento e 4.");
  });

  test("describes VAL-01 with numeric details", () => {
    const description = describeCatastoAnomalia({
      tipo: "VAL-01-sup_eccede",
      dati_json: { delta_mq: 50, delta_pct: 0.1 },
    });

    expect(description).toContain("supera quella catastale");
    expect(description).toContain("50");
    expect(description).toContain("10%");

    expect(describeCatastoAnomalia({ tipo: "VAL-01-sup_eccede", dati_json: {} })).toBe(
      "La superficie irrigabile supera quella catastale.",
    );
  });

  test("describes VAL-02 invalid fiscal code", () => {
    const description = describeCatastoAnomalia({
      tipo: "VAL-02-cf_invalido",
      dati_json: { cf_raw: "BADCF", error_code: "checksum" },
    });

    expect(description).toContain("Valore sorgente: BADCF");
    expect(description).toContain("Errore: checksum");

    expect(describeCatastoAnomalia({ tipo: "VAL-02-cf_invalido" })).toContain("controlli formali");
  });

  test("describes VAL-03 missing fiscal code", () => {
    expect(describeCatastoAnomalia({ tipo: "VAL-03-cf_mancante" })).toContain("Manca il codice fiscale");
  });

  test("describes VAL-04 invalid municipality", () => {
    const description = describeCatastoAnomalia({
      tipo: "VAL-04-comune_invalido",
      dati_json: { cod_istat: 95038 },
    });

    expect(description).toContain("Codice sorgente: 95038");
    expect(describeCatastoAnomalia({ tipo: "VAL-04-comune_invalido" })).not.toContain("Codice sorgente");
  });

  test("describes VAL-05 missing parcel", () => {
    const description = describeCatastoAnomalia({
      tipo: "VAL-05-particella_assente",
      dati_json: { foglio: "12", particella: "34", subalterno: "1" },
    });

    expect(description).toContain("Foglio 12");
    expect(description).toContain("Particella 34");
    expect(description).toContain("Sub 1");

    expect(describeCatastoAnomalia({ tipo: "VAL-05-particella_assente", dati_json: { foglio: "12" } })).toBe(
      "La riga ruolo non trova una particella corrente GAIA con lo stesso riferimento catastale. Foglio 12.",
    );

    expect(
      describeCatastoAnomalia({
        tipo: "VAL-05-particella_assente",
        dati_json: { foglio: "12", particella: "34" },
      }),
    ).toBe(
      "La riga ruolo non trova una particella corrente GAIA con lo stesso riferimento catastale. Foglio 12. Particella 34.",
    );

    expect(
      describeCatastoAnomalia({
        tipo: "VAL-05-particella_assente",
        dati_json: { foglio: "12", subalterno: "1" },
      }),
    ).toContain("Sub 1");

    expect(
      describeCatastoAnomalia({
        tipo: "VAL-05-particella_assente",
        dati_json: { subalterno: "1" },
      }),
    ).toBe(
      "La riga ruolo non trova una particella corrente GAIA con lo stesso riferimento catastale. Sub 1.",
    );
  });

  test("describes VAL-06 imponibile with catastale coincidence", () => {
    const description = describeCatastoAnomalia({
      tipo: "VAL-06-imponibile",
      dati_json: {
        atteso: 250,
        delta: 0.5,
        atteso_catastale: 225,
        coincide_con_catastale: true,
      },
    });

    expect(description).toContain("Valore atteso dal calcolo");
    expect(description).toContain("Scostamento rilevato");
    expect(description).toContain("superficie catastale");

    expect(
      describeCatastoAnomalia({
        tipo: "VAL-06-imponibile",
        dati_json: { coincide_con_catastale: true },
      }),
    ).toContain("non corrisponde");

    expect(
      describeCatastoAnomalia({
        tipo: "VAL-06-imponibile",
        dati_json: {
          atteso: "bad",
          delta: "bad",
          coincide_con_catastale: true,
          atteso_catastale: 225,
        },
      }),
    ).toContain("superficie catastale: 225");
  });

  test("describes VAL-07 import amounts", () => {
    const description = describeCatastoAnomalia({
      tipo: "VAL-07-importi",
      dati_json: {
        v07_648: { atteso: 12.3456, delta: 0.01 },
        v07_985: { atteso: 98.7654, delta: -0.02 },
      },
    });

    expect(description).toContain("voce 0648");
    expect(description).toContain("voce 0985");

    expect(
      describeCatastoAnomalia({
        tipo: "VAL-07-importi",
        dati_json: { v07_648: { atteso: 1 }, v07_985: { delta: 2 } },
      }),
    ).toContain("imponibile e aliquota");

    expect(
      describeCatastoAnomalia({
        tipo: "VAL-07-importi",
        dati_json: {
          v07_648: { atteso: 1.2345 },
          v07_985: { delta: -0.5 },
        },
      }),
    ).toContain("voce 0648 il valore atteso");

    expect(
      describeCatastoAnomalia({
        tipo: "VAL-07-importi",
        dati_json: { v07_648: "bad", v07_985: { atteso: 2, delta: null } },
      }),
    ).toContain("voce 0985 il valore atteso");

    expect(
      describeCatastoAnomalia({
        tipo: "VAL-07-importi",
        dati_json: { v07_648: { delta: 1 }, v07_985: "bad" },
      }),
    ).toContain("voce 0648 lo scostamento");
  });

  test("falls back to description or generic text", () => {
    expect(describeCatastoAnomalia({ tipo: "VAL-99-custom", descrizione: "Custom" })).toBe("Custom");
    expect(describeCatastoAnomalia({ tipo: "VAL-99-custom" })).toContain("senza dettaglio strutturato");
  });
});
