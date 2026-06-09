type AnomaliaLike = {
  tipo: string;
  descrizione?: string | null;
  dati_json?: Record<string, unknown> | null;
};

export type CatastoAnomaliaExplanation = {
  title: string;
  summary: string;
  whyItHappened: string;
  calculations: Array<{ label: string; value: string }>;
  checks: string[];
  resolutionTips: string[];
};

function formatNumber(value: unknown, fractionDigits = 2): string | null {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return null;
  return numeric.toLocaleString("it-IT", {
    minimumFractionDigits: 0,
    maximumFractionDigits: fractionDigits,
  });
}

function formatPct(value: unknown): string | null {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return null;
  return `${(numeric * 100).toLocaleString("it-IT", { maximumFractionDigits: 2 })}%`;
}

function compactParts(parts: Array<string | null | undefined>): string {
  return parts.filter((part): part is string => Boolean(part)).join(" ");
}

function formatValue(value: unknown, fractionDigits = 2): string | null {
  return formatNumber(value, fractionDigits);
}

function pushCalculation(
  rows: Array<{ label: string; value: string }>,
  label: string,
  value: unknown,
  fractionDigits = 2,
): void {
  const formatted = formatValue(value, fractionDigits);
  if (formatted) {
    rows.push({ label, value: formatted });
  }
}

function readNumber(value: unknown): number | null {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function formatSquareMeters(value: unknown): string | null {
  const numeric = readNumber(value);
  if (numeric == null) return null;
  return `${formatNumber(numeric, 2)} mq`;
}

function formatHectaresFromMq(value: unknown): string | null {
  const numeric = readNumber(value);
  if (numeric == null) return null;
  return `${formatNumber(numeric / 10_000, 4)} ha`;
}

function formatEuro(value: unknown, fractionDigits = 2): string | null {
  const numeric = readNumber(value);
  if (numeric == null) return null;
  return `${numeric.toLocaleString("it-IT", {
    minimumFractionDigits: 0,
    maximumFractionDigits: fractionDigits,
  })} €`;
}

function formatIndexEuroPerMq(value: unknown): string | null {
  const numeric = readNumber(value);
  if (numeric == null) return null;
  return `${formatNumber(numeric, 4)} €/mq`;
}

function pushCalculationText(
  rows: Array<{ label: string; value: string }>,
  label: string,
  value: string | null,
): void {
  if (value) {
    rows.push({ label, value });
  }
}

function formatFormula(left: unknown, multiplier: unknown, result: unknown, multiplierDigits = 4, resultDigits = 2): string | null {
  const leftFormatted = formatSquareMeters(left);
  const multiplierFormatted = formatIndexEuroPerMq(multiplier);
  const resultFormatted = formatEuro(result, resultDigits);
  if (!leftFormatted || !multiplierFormatted || !resultFormatted) return null;
  return `${leftFormatted} x ${multiplierFormatted} = ${resultFormatted}`;
}

export function explainCatastoAnomalia(anomalia: AnomaliaLike): CatastoAnomaliaExplanation {
  const data = anomalia.dati_json ?? {};

  switch (anomalia.tipo) {
    case "VAL-01-sup_eccede": {
      const calculations: Array<{ label: string; value: string }> = [];
      pushCalculation(calculations, "Scostamento in metri quadri", data.delta_mq);
      const pct = formatPct(data.delta_pct);
      if (pct) calculations.push({ label: "Scostamento percentuale", value: pct });
      return {
        title: "Superficie irrigabile superiore al catastale",
        summary: "La superficie usata per il ruolo risulta piu alta della superficie catastale disponibile.",
        whyItHappened:
          "Il controllo confronta la superficie irrigabile della riga importata con la superficie catastale registrata in GAIA. Se la superficie irrigabile supera il limite catastale oltre la tolleranza prevista, la riga viene segnalata.",
        calculations,
        checks: [
          "Verificare che la superficie irrigabile importata sia corretta.",
          "Controllare se la superficie catastale in anagrafica e aggiornata.",
          "Confermare che non ci siano errori di unita di misura o righe duplicate.",
        ],
        resolutionTips: [
          "Se la superficie irrigabile e sbagliata, correggere la riga ruolo o ripetere l'import con il dato corretto.",
          "Se il dato catastale in GAIA non e aggiornato, sistemare prima l'anagrafica della particella.",
          "Chiudere l'anomalia solo quando i due valori tornano coerenti o quando esiste una motivazione documentata.",
        ],
      };
    }
    case "VAL-02-cf_invalido":
      return {
        title: "Codice fiscale o partita IVA formalmente non valido",
        summary: "Il valore importato non rispetta il formato atteso.",
        whyItHappened:
          "La riga contiene un codice fiscale o una partita IVA che non supera i controlli formali minimi. Non significa per forza che il soggetto non esista, ma che il dato importato va corretto o confermato.",
        calculations: [
          ...(data.cf_raw ? [{ label: "Valore sorgente", value: String(data.cf_raw) }] : []),
          ...(data.error_code ? [{ label: "Esito controllo", value: String(data.error_code) }] : []),
        ],
        checks: [
          "Controllare eventuali caratteri mancanti o extra.",
          "Verificare se il campo contiene una partita IVA al posto del codice fiscale, o viceversa.",
          "Confermare il dato con la documentazione sorgente prima di correggere la riga.",
        ],
        resolutionTips: [
          "Recuperare il dato fiscale corretto dalla fonte ufficiale o dalla documentazione disponibile.",
          "Aggiornare il valore nella riga anomala usando il workflow guidato di correzione.",
          "Rieseguire la verifica e chiudere l'anomalia solo dopo che il controllo formale risulta superato.",
        ],
      };
    case "VAL-03-cf_mancante":
      return {
        title: "Codice fiscale o partita IVA mancante",
        summary: "La riga ruolo e priva del riferimento fiscale del soggetto.",
        whyItHappened:
          "Il flusso di import ha trovato la posizione senza codice fiscale o partita IVA. Senza questo dato diventa piu difficile collegare correttamente la posizione al soggetto.",
        calculations: [],
        checks: [
          "Recuperare il dato fiscale dalla fonte originale.",
          "Verificare se la posizione puo essere ricondotta al soggetto tramite altri riferimenti.",
          "Correggere la riga solo dopo la conferma del dato mancante.",
        ],
        resolutionTips: [
          "Completare la posizione con il codice fiscale o la partita IVA corretta.",
          "Se il dato non e recuperabile subito, assegnare la posizione a un operatore per follow-up.",
          "Chiudere l'anomalia solo quando il riferimento fiscale e stato inserito o il caso e stato documentato.",
        ],
      };
    case "VAL-04-comune_invalido":
      return {
        title: "Comune non riconosciuto nel riferimento GAIA",
        summary: "Il codice comune presente nella riga importata non trova un corrispondente valido in GAIA.",
        whyItHappened:
          "Il valore del comune proveniente dalla sorgente non coincide con quelli gestiti nel riferimento comuni del sistema, quindi la riga non puo essere agganciata in modo affidabile.",
        calculations: [
          ...(data.cod_istat != null ? [{ label: "Codice comune sorgente", value: String(data.cod_istat) }] : []),
        ],
        checks: [
          "Confrontare il codice comune importato con il riferimento GAIA.",
          "Verificare se il dato sorgente usa un codice storico o non aggiornato.",
          "Controllare che non ci sia stato uno scambio di comune in fase di import.",
        ],
        resolutionTips: [
          "Allineare il comune corretto scegliendo il riferimento GAIA valido.",
          "Se il dato sorgente e obsoleto, correggere il mapping o aggiornare il valore importato.",
          "Richiudere l'anomalia dopo avere verificato che la riga punti al comune giusto.",
        ],
      };
    case "VAL-05-particella_assente":
      return {
        title: "Particella non trovata in anagrafica",
        summary: "La riga ruolo non riesce a collegarsi a una particella corrente di GAIA.",
        whyItHappened:
          "Il controllo cerca una particella con gli stessi riferimenti catastali della riga importata. Se non trova un match attendibile, la posizione resta scollegata e viene segnalata.",
        calculations: [
          ...(data.foglio ? [{ label: "Foglio", value: String(data.foglio) }] : []),
          ...(data.particella ? [{ label: "Particella", value: String(data.particella) }] : []),
          ...(data.subalterno ? [{ label: "Subalterno", value: String(data.subalterno) }] : []),
        ],
        checks: [
          "Verificare che foglio, particella e subalterno siano corretti nella sorgente.",
          "Controllare se la particella esiste in GAIA con una variante storica o un comune diverso.",
          "Confermare che la particella non sia stata rinumerata o unificata.",
        ],
        resolutionTips: [
          "Se esiste una particella candidata corretta, collegarla dalla console anomalie.",
          "Se la particella manca davvero in GAIA, sistemare prima l'anagrafica catastale o aprire un follow-up operativo.",
          "Chiudere l'anomalia solo quando la riga ruolo e agganciata a una particella attendibile.",
        ],
      };
    case "VAL-06-imponibile": {
      const calculations: Array<{ label: string; value: string }> = [];
      pushCalculationText(calculations, "Superficie irrigabile", formatSquareMeters(data.sup_irrigabile_mq));
      pushCalculationText(calculations, "Superficie irrigabile in ettari", formatHectaresFromMq(data.sup_irrigabile_mq));
      pushCalculationText(calculations, "Superficie catastale", formatSquareMeters(data.sup_catastale_mq));
      pushCalculationText(calculations, "Superficie catastale in ettari", formatHectaresFromMq(data.sup_catastale_mq));
      pushCalculationText(calculations, "Indice spese fisse", formatIndexEuroPerMq(data.ind_spese_fisse));
      pushCalculationText(calculations, "Imponibile registrato", formatEuro(data.imponibile_registrato));
      pushCalculationText(calculations, "Valore atteso dal calcolo", formatEuro(data.atteso));
      pushCalculationText(calculations, "Scostamento rilevato", formatEuro(data.delta, 4));
      const formulaIrrigabile = formatFormula(data.sup_irrigabile_mq, data.ind_spese_fisse, data.atteso);
      if (formulaIrrigabile) {
        calculations.push({ label: "Calcolo teorico", value: formulaIrrigabile });
      }
      const formulaCatastale = formatFormula(data.sup_catastale_mq, data.ind_spese_fisse, data.atteso_catastale);
      if (formulaCatastale) {
        calculations.push({ label: "Verifica con catastale", value: formulaCatastale });
      }
      if (readNumber(data.delta_vs_catastale) != null) {
        pushCalculationText(calculations, "Scostamento su catastale", formatEuro(data.delta_vs_catastale, 4));
      }
      if (data.coincide_con_catastale === true && formulaCatastale) {
        calculations.push({ label: "Nota", value: "L'imponibile registrato coincide con il calcolo su superficie catastale." });
      }
      return {
        title: "Imponibile non coerente con il calcolo teorico",
        summary: "L'importo imponibile registrato non coincide con quello che risulta dal calcolo automatico.",
        whyItHappened:
          "Il sistema ricalcola l'imponibile usando la formula superficie irrigabile x indice spese fisse. Se il valore importato si discosta oltre la tolleranza prevista, la riga viene marcata come anomala.",
        calculations,
        checks: [
          "Controllare la superficie irrigabile usata nella riga importata.",
          "Verificare che l'indice spese fisse applicato sia quello corretto.",
          "Confrontare il valore imponibile della riga con il risultato atteso del calcolo.",
        ],
        resolutionTips: [
          "Se la superficie irrigabile o l'indice sono errati, correggere il dato di origine e ripetere il controllo.",
          "Se il calcolo atteso e corretto, aggiornare l'imponibile della riga o rigenerare il caricamento.",
          "Chiudere l'anomalia solo quando imponibile registrato e imponibile atteso coincidono entro tolleranza.",
        ],
      };
    }
    case "VAL-07-importi": {
      const calculations: Array<{ label: string; value: string }> = [];
      const v0648 = data.v07_648 && typeof data.v07_648 === "object" ? (data.v07_648 as Record<string, unknown>) : null;
      const v0985 = data.v07_985 && typeof data.v07_985 === "object" ? (data.v07_985 as Record<string, unknown>) : null;
      if (v0648) {
        pushCalculation(calculations, "Voce 0648 - valore atteso", v0648.atteso, 4);
        pushCalculation(calculations, "Voce 0648 - scostamento", v0648.delta, 4);
      }
      if (v0985) {
        pushCalculation(calculations, "Voce 0985 - valore atteso", v0985.atteso, 4);
        pushCalculation(calculations, "Voce 0985 - scostamento", v0985.delta, 4);
      }
      return {
        title: "Importi del ruolo non coerenti",
        summary: "Almeno uno degli importi di ruolo non coincide con il risultato atteso del calcolo.",
        whyItHappened:
          "Il sistema ricalcola gli importi delle voci di ruolo partendo da imponibile e aliquota. Se una delle voci non rientra nella tolleranza, la posizione viene segnalata.",
        calculations,
        checks: [
          "Verificare l'imponibile usato per il calcolo.",
          "Controllare che l'aliquota applicata alle voci 0648 e 0985 sia corretta.",
          "Confrontare gli importi presenti nella riga importata con quelli attesi dal calcolo.",
        ],
        resolutionTips: [
          "Ricalcolare le voci 0648 e 0985 partendo da imponibile e aliquota effettiva.",
          "Correggere gli importi di ruolo se il dato importato e sbagliato oppure confermare l'aliquota corretta.",
          "Chiudere l'anomalia solo quando gli importi tornano nei limiti di tolleranza del controllo.",
        ],
      };
    }
    default:
      return {
        title: anomalia.descrizione ?? "Anomalia dati",
        summary: anomalia.descrizione ?? "Il sistema ha rilevato una incoerenza da verificare.",
        whyItHappened:
          "Per questo tipo di anomalia non e disponibile una formula guidata. La posizione va verificata leggendo i dati sorgente e il contesto della particella o dell'utenza.",
        calculations: [],
        checks: [
          "Aprire la posizione collegata e confrontare i dati con la sorgente importata.",
          "Valutare se l'anomalia dipende da un dato mancante, errato o non aggiornato.",
        ],
        resolutionTips: [
          "Raccogliere il contesto operativo della posizione prima di intervenire.",
          "Correggere il dato alla fonte o aprire un follow-up se il caso richiede approfondimento manuale.",
        ],
      };
    }
}

export function describeCatastoAnomalia(anomalia: AnomaliaLike): string {
  const data = anomalia.dati_json ?? {};

  switch (anomalia.tipo) {
    case "VAL-01-sup_eccede":
      return compactParts([
        "La superficie irrigabile supera quella catastale.",
        formatNumber(data.delta_mq) ? `Scostamento: ${formatNumber(data.delta_mq)} mq.` : null,
        formatPct(data.delta_pct) ? `Scostamento percentuale: ${formatPct(data.delta_pct)}.` : null,
      ]);
    case "VAL-02-cf_invalido":
      return compactParts([
        "Il codice fiscale o la partita IVA importata non supera i controlli formali.",
        data.cf_raw ? `Valore sorgente: ${String(data.cf_raw)}.` : null,
        data.error_code ? `Errore: ${String(data.error_code)}.` : null,
      ]);
    case "VAL-03-cf_mancante":
      return "Manca il codice fiscale o la partita IVA nella riga ruolo importata.";
    case "VAL-04-comune_invalido":
      return compactParts([
        "Il codice comune Capacitas della riga ruolo non e presente nel riferimento comuni GAIA.",
        data.cod_istat != null ? `Codice sorgente: ${String(data.cod_istat)}.` : null,
      ]);
    case "VAL-05-particella_assente":
      return compactParts([
        "La riga ruolo non trova una particella corrente GAIA con lo stesso riferimento catastale.",
        data.foglio ? `Foglio ${String(data.foglio)}.` : null,
        data.particella ? `Particella ${String(data.particella)}.` : null,
        data.subalterno ? `Sub ${String(data.subalterno)}.` : null,
      ]);
    case "VAL-06-imponibile":
      return compactParts([
        "L'importo imponibile registrato non corrisponde al valore che ci si aspetta calcolando superficie irrigabile e indice spese fisse.",
        formatNumber(data.atteso) ? `Valore atteso dal calcolo: ${formatNumber(data.atteso)}.` : null,
        formatNumber(data.delta, 4) ? `Scostamento rilevato: ${formatNumber(data.delta, 4)}.` : null,
        data.coincide_con_catastale === true ? "Il valore registrato coincide invece con il calcolo su superficie catastale." : null,
        "In pratica: i numeri della riga importata non tornano con il calcolo teorico e la posizione va verificata.",
      ]);
    case "VAL-07-importi": {
      const v0648 = data.v07_648 && typeof data.v07_648 === "object" ? data.v07_648 as Record<string, unknown> : null;
      const v0985 = data.v07_985 && typeof data.v07_985 === "object" ? data.v07_985 as Record<string, unknown> : null;
      return compactParts([
        "Gli importi del ruolo non coincidono con quelli che risultano dal calcolo su imponibile e aliquota.",
        v0648?.atteso != null ? `Per la voce 0648 il valore atteso e ${formatNumber(v0648.atteso, 4)}.` : null,
        v0648?.delta != null ? `Per la voce 0648 lo scostamento e ${formatNumber(v0648.delta, 4)}.` : null,
        v0985?.atteso != null ? `Per la voce 0985 il valore atteso e ${formatNumber(v0985.atteso, 4)}.` : null,
        v0985?.delta != null ? `Per la voce 0985 lo scostamento e ${formatNumber(v0985.delta, 4)}.` : null,
      ]);
    }
    default:
      return anomalia.descrizione ?? "Anomalia ruolo senza dettaglio strutturato.";
  }
}
