export type NoticeDetailField = {
  label: string;
  value: string;
};

export type NoticeRateDetail = {
  label: string;
  dueDate: string | null;
  amount: string | null;
};

export function normalizeNoticeDetailText(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

export function extractTokenSegment(source: string, startToken: string, endTokens: string[]): string | null {
  const startIndex = source.indexOf(startToken);
  if (startIndex === -1) return null;
  const afterStart = source.slice(startIndex + startToken.length);
  let endIndex = afterStart.length;
  for (const endToken of endTokens) {
    const candidateIndex = afterStart.indexOf(endToken);
    if (candidateIndex !== -1 && candidateIndex < endIndex) {
      endIndex = candidateIndex;
    }
  }
  const extracted = afterStart.slice(0, endIndex).trim();
  return extracted || null;
}

export function extractNoticeDetailFields(detailText: string): NoticeDetailField[] {
  const normalized = normalizeNoticeDetailText(detailText);
  const fields: NoticeDetailField[] = [];
  const pushField = (label: string, value: string | null) => {
    if (!value) return;
    fields.push({ label, value: value.trim() });
  };

  pushField("Codice fiscale", extractTokenSegment(normalized, "Codice fiscale ", [" Dati anagrafici", " Partita ", " Avviso "]));
  pushField("Dati anagrafici", extractTokenSegment(normalized, "Dati anagrafici ", [" Partita ", " Avviso ", " Anno "]));
  pushField("Partita", extractTokenSegment(normalized, "Partita ", [" Avviso ", " Anno "]));
  pushField("Avviso", extractTokenSegment(normalized, "Avviso ", [" Anno ", " Totale imposta "]));
  pushField("Anno", extractTokenSegment(normalized, "Anno ", [" Totale imposta ", " Totale residuo "]));
  pushField("Totale imposta", extractTokenSegment(normalized, "Totale imposta ", [" Totale residuo ", " Totale sgravio "]));
  pushField("Totale residuo", extractTokenSegment(normalized, "Totale residuo ", [" Totale sgravio ", " Invio ", " Ultimo invio "]));
  pushField("Totale sgravio", extractTokenSegment(normalized, "Totale sgravio ", [" Invio ", " Ultimo invio ", " Ruolo "]));
  pushField("Ultimo invio", extractTokenSegment(normalized, "Ultimo invio ", [" Ruolo ", " Lista "]));
  pushField("Ruolo", extractTokenSegment(normalized, "Ruolo ", [" Lista ", " Rate ", " Rata tot. "]));
  pushField("Lista", extractTokenSegment(normalized, "Lista ", [" Rate ", " Rata tot. ", " Trib. "]));
  pushField("Tributo", extractTokenSegment(normalized, "Trib. ", [" Raggruppamento colonne"]));

  return fields;
}

export function extractNoticeRateDetails(detailText: string): NoticeRateDetail[] {
  const normalized = normalizeNoticeDetailText(detailText);
  const ratePattern = /(Rata tot\.|Rata \d+)(?:\s+(\d{2}\/\d{2}\/\d{4}))?\s*(€\s*[\d.,]+)?/g;
  const matches = Array.from(normalized.matchAll(ratePattern));
  const results: NoticeRateDetail[] = [];
  for (const match of matches) {
    const label = match[1]!.trim();
    results.push({
      label,
      dueDate: match[2]?.trim() ?? null,
      amount: match[3]?.replace(/\s+/g, " ").trim() ?? null,
    });
  }
  return results;
}

export function buildNoticeResidualNotes(detailText: string, fields: NoticeDetailField[]): string[] {
  let normalized = normalizeNoticeDetailText(detailText);
  const noiseTokens = [
    /inCass(?:\s+inCass)?\s+\S+\s+\S+/i,
    /Indietro/i,
    /Azioni/i,
    /Aggiungi pag\. manuale/i,
    /Rimuovi pag\. manuale/i,
    /Annulla assegnaz\. boll\./i,
    /Aggiungi a Mailing/i,
    /List Rottamazione avviso/i,
    /Sgravio Inserisci/i,
    /Rimuovi Immagine pag\. Inserisci/i,
    /Rimuovi Modifica Tipo di avviso/i,
    /Blocca Aggiorna dettagli/i,
    /Rateizzazione/i,
    /AVVISO NON RISCOSSO/i,
    /Codice consorzio:\s*\d+/i,
    /Server:\s*[^ ]+/i,
    /Base dati:\s*[^ ]+/i,
    /Chiudi/i,
    /Manuale/i,
    /Tile bloccate/i,
    /Mappa del sito/i,
    /principale ricerca avvisi dettaglio Dettaglio/i,
    /Raggruppamento colonne/i,
    /©\s*\d{4}(?:-\d{4})?\s*Capacitas/i,
    /Contattaci/i,
    /Privacy/i,
    /Informativa Cookies/i,
  ];

  for (const pattern of noiseTokens) {
    normalized = normalized.replace(pattern, " ");
  }
  for (const field of fields) {
    normalized = normalized.replace(field.label, " ");
    normalized = normalized.replace(field.value, " ");
  }
  normalized = normalized.replace(/(Rata tot\.|Rata \d+)\s+\d{2}\/\d{2}\/\d{4}\s*€\s*[\d.,]+/g, " ");
  normalized = normalized.replace(/\s+/g, " ").trim();
  if (!normalized) return [];

  return normalized
    .split(/(?<=\.)\s+|\s{2,}/)
    .map((item) => item.trim())
    .filter((item) => item.length >= 6);
}
