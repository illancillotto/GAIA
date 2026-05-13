type AnomaliaLike = {
  tipo: string;
  descrizione?: string | null;
  dati_json?: Record<string, unknown> | null;
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

export function describeCatastoAnomalia(anomalia: AnomaliaLike): string {
  const data = anomalia.dati_json ?? {};

  switch (anomalia.tipo) {
    case "VAL-01-sup_eccede":
      return compactParts([
        "La superficie irrigabile supera quella catastale.",
        formatNumber(data.delta_mq) ? `Scostamento: ${formatNumber(data.delta_mq)} mq.` : null,
        formatPct(data.delta_pct) ? `Delta: ${formatPct(data.delta_pct)}.` : null,
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
        "L'imponibile non coincide con superficie irrigabile per indice spese fisse.",
        formatNumber(data.atteso) ? `Atteso: ${formatNumber(data.atteso)}.` : null,
        formatNumber(data.delta, 4) ? `Delta: ${formatNumber(data.delta, 4)}.` : null,
      ]);
    case "VAL-07-importi": {
      const v0648 = data.v07_648 && typeof data.v07_648 === "object" ? data.v07_648 as Record<string, unknown> : null;
      const v0985 = data.v07_985 && typeof data.v07_985 === "object" ? data.v07_985 as Record<string, unknown> : null;
      return compactParts([
        "Gli importi ruolo non coincidono con imponibile per aliquota.",
        v0648?.atteso != null ? `0648 atteso: ${formatNumber(v0648.atteso, 4)}.` : null,
        v0648?.delta != null ? `0648 delta: ${formatNumber(v0648.delta, 4)}.` : null,
        v0985?.atteso != null ? `0985 atteso: ${formatNumber(v0985.atteso, 4)}.` : null,
        v0985?.delta != null ? `0985 delta: ${formatNumber(v0985.delta, 4)}.` : null,
      ]);
    }
    default:
      return anomalia.descrizione ?? "Anomalia ruolo senza dettaglio strutturato.";
  }
}
