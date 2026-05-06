"use client";

import * as XLSX from "xlsx";
import { useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { DataTable } from "@/components/table/data-table";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertBanner } from "@/components/ui/alert-banner";
import { DocumentIcon, RefreshIcon } from "@/components/ui/icons";
import { capacitasGetRptCertificatoLink, catastoBulkSearchAnagrafica, catastoDeleteElaborazioniMassiveJobs, catastoGetElaborazioneMassivaJob, catastoListElaborazioniMassiveJobs, catastoSaveElaborazioneMassivaJob } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatAnagraficaBulkJobItem, CatAnagraficaBulkRowInput, CatAnagraficaBulkRowResult, CatAnagraficaMatch, CatIntestatario } from "@/types/catasto";

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = window.document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function normHeader(value: unknown): string {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "_")
    .replace(/[^\w]/g, "_");
}

function pickColumn(headers: string[], aliases: string[]): string | null {
  const set = new Set(headers);
  for (const a of aliases) {
    if (set.has(a)) return a;
  }
  return null;
}

function formatHaFromMq(value: unknown): string {
  if (value == null) return "—";
  const mq = typeof value === "number" ? value : Number(value);
  const ha = (Number.isFinite(mq) ? mq : 0) / 10_000;
  return `${new Intl.NumberFormat("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(ha)} ha`;
}

function intestatarioDisplayName(intestatario: CatIntestatario): string {
  return (
    intestatario.denominazione ??
    intestatario.ragione_sociale ??
    [intestatario.cognome, intestatario.nome].filter(Boolean).join(" ")
  );
}

function formatEsitoForExport(esito: string): string {
  if (esito === "FOUND") return "Presente in Catasto";
  if (esito === "NOT_FOUND") return "Non trovata in Catasto";
  return esito;
}

function formatConsorzioEsitoForExport(presenteInConsorzio: boolean): string {
  return presenteInConsorzio ? "Particella presente in Catasto Consorzio" : "Particella non presente in Catasto Consorzio";
}

async function resolveCapacitasRptCertificatoUrls(
  token: string,
  matches: CatAnagraficaMatch[],
): Promise<Map<string, string>> {
  const out = new Map<string, string>();
  const unique = Array.from(
    new Map(
      matches
        .filter((match) => Boolean(match.utenza_latest?.cco))
        .map((match) => {
          const cco = match.utenza_latest?.cco?.trim() ?? "";
          const key = [cco, match.cert_com ?? "", match.cert_pvc ?? "", match.cert_fra ?? "", match.cert_ccs ?? ""].join("|");
          return [key, match] as const;
        }),
    ).values(),
  );
  // Capacitas/InVolture può rate-limitare o essere instabile: preferiamo meno concorrenza e un retry leggero.
  const concurrency = 3;
  let idx = 0;

  async function worker(): Promise<void> {
    for (;;) {
      const current = unique[idx];
      idx += 1;
      if (!current) return;
      let resolved = "";
      for (let attempt = 0; attempt < 2; attempt += 1) {
        try {
          const cco = current.utenza_latest?.cco?.trim() ?? "";
          const { url } = await capacitasGetRptCertificatoLink(token, cco, {
            com: current.cert_com,
            pvc: current.cert_pvc,
            fra: current.cert_fra,
            ccs: current.cert_ccs,
          });
          resolved = url || "";
          break;
        } catch {
          // backoff minimo prima del retry
          await new Promise((r) => window.setTimeout(r, 250 + attempt * 300));
        }
      }
      const key = [
        current.utenza_latest?.cco?.trim() ?? "",
        current.cert_com ?? "",
        current.cert_pvc ?? "",
        current.cert_fra ?? "",
        current.cert_ccs ?? "",
      ].join("|");
      out.set(key, resolved);
    }
  }

  await Promise.all(Array.from({ length: Math.min(concurrency, unique.length) }, () => worker()));
  return out;
}

type BulkSummary = {
  total: number;
  found: number;
  notFound: number;
  multiple: number;
  invalid: number;
  error: number;
};

const FOGLIO_WITH_SEZIONE_RE = /^\s*([^\s]+)\s+sez\.?\s*([A-Za-z0-9]+)(?:\s+.*)?$/i;

function normalizeSezioneValue(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return "";
  const lowered = trimmed.toLowerCase();
  if (lowered.startsWith("sez")) {
    return trimmed.slice(3).replace(/^[\s.:-]+/, "").trim();
  }
  return trimmed;
}

function normalizeFoglioSezioneInput(foglio: string, sezione: string): { foglio: string; sezione: string } {
  const foglioTrimmed = foglio.trim();
  const sezioneTrimmed = normalizeSezioneValue(sezione);
  const match = foglioTrimmed.match(FOGLIO_WITH_SEZIONE_RE);
  if (!match) {
    return { foglio: foglioTrimmed, sezione: sezioneTrimmed };
  }
  return {
    foglio: match[1]?.trim() ?? foglioTrimmed,
    sezione: sezioneTrimmed || normalizeSezioneValue(match[2] ?? ""),
  };
}

type BulkOperationHistoryItem = CatAnagraficaBulkJobItem;

type BulkProgressState = {
  open: boolean;
  processed: number;
  total: number;
  currentLabel: string;
  phase: "idle" | "processing" | "saving" | "completed" | "error";
};

function buildSummary(results: CatAnagraficaBulkRowResult[]): BulkSummary {
  const s: BulkSummary = { total: results.length, found: 0, notFound: 0, multiple: 0, invalid: 0, error: 0 };
  for (const r of results) {
    if (r.esito === "FOUND") s.found += 1;
    else if (r.esito === "NOT_FOUND") s.notFound += 1;
    else if (r.esito === "MULTIPLE_MATCHES") s.multiple += 1;
    else if (r.esito === "INVALID_ROW") s.invalid += 1;
    else if (r.esito === "ERROR") s.error += 1;
  }
  return s;
}

function formatOperationKind(kind: BulkOperationHistoryItem["kind"]): string {
  if (kind === "CF_PIVA_PARTICELLE") return "CF/P.IVA -> Particelle";
  if (kind === "COMUNE_FOGLIO_PARTICELLA_INTESTATARI") return "Particelle -> Intestatari";
  return "Tipo non rilevato";
}

function inferKindFromHeaders(headers: string[]): "CF_PIVA_PARTICELLE" | "COMUNE_FOGLIO_PARTICELLA_INTESTATARI" {
  const comuneKey = pickColumn(headers, ["comune", "codice_comune", "nome_comune"]);
  const foglioKey = pickColumn(headers, ["foglio"]);
  const particellaKey = pickColumn(headers, ["particella", "mappale"]);
  const cfKey = pickColumn(headers, ["codice_fiscale", "cf"]);
  const pivaKey = pickColumn(headers, ["partita_iva", "piva", "iva"]);

  const hasCadastral = Boolean(comuneKey && foglioKey && particellaKey);
  const hasTax = Boolean(cfKey || pivaKey);

  if (hasTax && !hasCadastral) return "CF_PIVA_PARTICELLE";
  return "COMUNE_FOGLIO_PARTICELLA_INTESTATARI";
}

async function readFileToRows(
  file: File,
): Promise<{ kind: "CF_PIVA_PARTICELLE" | "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"; rows: CatAnagraficaBulkRowInput[]; skipped: number }> {
  const ext = file.name.toLowerCase().split(".").pop() ?? "";

  const toJsonRows = (worksheet: XLSX.WorkSheet): Record<string, unknown>[] => {
    return XLSX.utils.sheet_to_json<Record<string, unknown>>(worksheet, { defval: null, raw: false });
  };

  let workbook: XLSX.WorkBook;
  if (ext === "csv") {
    const text = await file.text();
    workbook = XLSX.read(text, { type: "string" });
  } else {
    const buf = await file.arrayBuffer();
    workbook = XLSX.read(buf, { type: "array" });
  }

  const firstSheetName = workbook.SheetNames[0];
  if (!firstSheetName) {
    return { kind: "COMUNE_FOGLIO_PARTICELLA_INTESTATARI", rows: [], skipped: 0 };
  }
  const sheet = workbook.Sheets[firstSheetName];
  const data = toJsonRows(sheet);
  if (data.length === 0) {
    return { kind: "COMUNE_FOGLIO_PARTICELLA_INTESTATARI", rows: [], skipped: 0 };
  }

  const headers = Object.keys(data[0] ?? {}).map(normHeader);
  const kind = inferKindFromHeaders(headers);
  const headerMap = new Map<string, string>();
  for (const rawKey of Object.keys(data[0] ?? {})) {
    headerMap.set(normHeader(rawKey), rawKey);
  }

  const comuneKey = pickColumn(headers, ["comune", "codice_comune", "nome_comune"]);
  const sezioneKey = pickColumn(headers, ["sezione", "sez", "sezione_catastale"]);
  const foglioKey = pickColumn(headers, ["foglio"]);
  const particellaKey = pickColumn(headers, ["particella", "mappale"]);
  const subKey = pickColumn(headers, ["sub", "subalterno"]);
  const cfKey = pickColumn(headers, ["codice_fiscale", "cf"]);
  const pivaKey = pickColumn(headers, ["partita_iva", "piva", "iva"]);

  if (kind === "CF_PIVA_PARTICELLE") {
    if (!cfKey && !pivaKey) {
      throw new Error("Colonne minime mancanti. Richieste: codice_fiscale oppure partita_iva.");
    }
  } else {
    if (!comuneKey || !foglioKey || !particellaKey) {
      throw new Error("Colonne minime mancanti. Richieste: comune, foglio, particella (opzionali: sezione, sub). Nel campo comune puoi usare nome comune, codice Capacitas numerico o codice catastale/Belfiore.");
    }
  }

  let skipped = 0;
  const rows: CatAnagraficaBulkRowInput[] = [];
  for (let i = 0; i < data.length; i += 1) {
    const record = data[i] ?? {};
    if (kind === "CF_PIVA_PARTICELLE") {
      const cfRaw = cfKey ? record[headerMap.get(cfKey) ?? cfKey] : null;
      const pivaRaw = pivaKey ? record[headerMap.get(pivaKey) ?? pivaKey] : null;
      const cf = cfRaw != null ? String(cfRaw).trim() : "";
      const piva = pivaRaw != null ? String(pivaRaw).trim() : "";

      if (!cf && !piva) {
        skipped += 1;
        continue;
      }

      rows.push({
        row_index: i + 2,
        codice_fiscale: cf || null,
        partita_iva: piva || null,
      });
    } else {
      const comuneRaw = comuneKey ? record[headerMap.get(comuneKey) ?? comuneKey] : null;
      const sezioneRaw = sezioneKey ? record[headerMap.get(sezioneKey) ?? sezioneKey] : null;
      const foglioRaw = foglioKey ? record[headerMap.get(foglioKey) ?? foglioKey] : null;
      const particellaRaw = particellaKey ? record[headerMap.get(particellaKey) ?? particellaKey] : null;
      const subRaw = subKey ? record[headerMap.get(subKey) ?? subKey] : null;

      const comune = comuneRaw != null ? String(comuneRaw).trim() : "";
      const sezione = sezioneRaw != null ? String(sezioneRaw).trim() : "";
      const foglio = foglioRaw != null ? String(foglioRaw).trim() : "";
      const particella = particellaRaw != null ? String(particellaRaw).trim() : "";
      const sub = subRaw != null ? String(subRaw).trim() : "";
      const normalized = normalizeFoglioSezioneInput(foglio, sezione);

      if (!comune && !normalized.foglio && !particella && !sub && !normalized.sezione) {
        skipped += 1;
        continue;
      }

      rows.push({
        row_index: i + 2,
        comune: comune || null,
        sezione: normalized.sezione || null,
        foglio: normalized.foglio || null,
        particella: particella || null,
        sub: sub || null,
      });
    }
  }
  return { kind, rows, skipped };
}

export function AnagraficaBulkPanel() {
  const [inferredKind, setInferredKind] = useState<"CF_PIVA_PARTICELLE" | "COMUNE_FOGLIO_PARTICELLA_INTESTATARI" | null>(
    null,
  );
  const [sourceFile, setSourceFile] = useState<File | null>(null);
  const [parsedRows, setParsedRows] = useState<CatAnagraficaBulkRowInput[]>([]);
  const [skippedRows, setSkippedRows] = useState(0);
  const [results, setResults] = useState<CatAnagraficaBulkRowResult[]>([]);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [operationHistory, setOperationHistory] = useState<BulkOperationHistoryItem[]>([]);
  const [showDeleteHistoryConfirm, setShowDeleteHistoryConfirm] = useState(false);
  const [bulkProgress, setBulkProgress] = useState<BulkProgressState>({
    open: false,
    processed: 0,
    total: 0,
    currentLabel: "",
    phase: "idle",
  });

  const summary = useMemo(() => buildSummary(results), [results]);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    void (async () => {
      try {
        const { items } = await catastoListElaborazioniMassiveJobs(token, { limit: 5 });
        setOperationHistory(items);
      } catch {
        setOperationHistory([]);
      }
    })();
  }, []);

  async function deleteOperationHistory(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    setBusy(true);
    try {
      await catastoDeleteElaborazioniMassiveJobs(token);
      setOperationHistory([]);
      setActiveJobId(null);
      setShowDeleteHistoryConfirm(false);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore cancellazione storico");
    } finally {
      setBusy(false);
    }
  }

  function progressRowLabel(row: CatAnagraficaBulkRowInput): string {
    if (inferredKind === "CF_PIVA_PARTICELLE") {
      return row.codice_fiscale ?? row.partita_iva ?? `Riga ${row.row_index}`;
    }
    return [
      row.comune ?? "Comune n/d",
      row.foglio ? `Fg. ${row.foglio}` : null,
      row.particella ? `Part. ${row.particella}` : null,
      row.sub ? `Sub. ${row.sub}` : null,
    ]
      .filter(Boolean)
      .join(" · ");
  }

  const columns = useMemo<ColumnDef<CatAnagraficaBulkRowResult>[]>(
    () => [
      { header: "Riga", accessorKey: "row_index", cell: ({ row }) => <span className="text-sm text-gray-700">{row.original.row_index}</span> },
      {
        header: "Input",
        id: "input",
        cell: ({ row }) => (
          <div className="text-sm text-gray-700">
            {inferredKind === "CF_PIVA_PARTICELLE" ? (
              <>
                <p className="font-medium">{row.original.codice_fiscale_input ?? row.original.partita_iva_input ?? "—"}</p>
                <p className="text-xs text-gray-500">CF/P.IVA</p>
              </>
            ) : (
              <>
                <p className="font-medium">{row.original.comune_input ?? "—"}</p>
                <p className="text-xs text-gray-500">
                  {row.original.sezione_input ? `Sez.${row.original.sezione_input} ` : ""}
                  Fg.{row.original.foglio_input ?? "—"} Part.{row.original.particella_input ?? "—"}
                  {row.original.sub_input ? ` Sub.${row.original.sub_input}` : ""}
                </p>
              </>
            )}
          </div>
        ),
      },
      {
        header: "Esito",
        accessorKey: "esito",
        cell: ({ row }) => (
          <span
            className={[
              "rounded-full px-2 py-1 text-xs font-medium",
              row.original.esito === "FOUND"
                ? "bg-emerald-50 text-emerald-700"
                : row.original.esito === "NOT_FOUND"
                  ? "bg-gray-100 text-gray-700"
                  : row.original.esito === "MULTIPLE_MATCHES"
                    ? "bg-amber-50 text-amber-700"
                    : row.original.esito === "INVALID_ROW"
                      ? "bg-amber-50 text-amber-800"
                      : "bg-red-50 text-red-700",
            ].join(" ")}
          >
            {row.original.esito}
          </span>
        ),
      },
      { header: "Messaggio", accessorKey: "message", cell: ({ row }) => <span className="text-sm text-gray-700">{row.original.message}</span> },
      {
        header: "Dettaglio",
        id: "detail",
        cell: ({ row }) => {
          const m = row.original.match;
          if (!m) return <span className="text-sm text-gray-400">—</span>;
          return (
            <div className="text-sm text-gray-700">
              <p className="font-medium">{m.comune ?? m.cod_comune_capacitas ?? "—"}</p>
              <p className="text-xs text-gray-500">
                Distretto: {m.num_distretto ?? "—"} · Sup. cat.: {formatHaFromMq(m.superficie_mq)}
              </p>
              {inferredKind !== "CF_PIVA_PARTICELLE" && m.intestatari.length > 0 ? (
                <p className="mt-1 text-xs text-gray-500">
                  Intestatari:{" "}
                  {m.intestatari
                    .slice(0, 3)
                    .map(intestatarioDisplayName)
                    .filter(Boolean)
                    .join(" · ")}
                  {m.intestatari.length > 3 ? ` (+${m.intestatari.length - 3})` : ""}
                </p>
              ) : null}
              {inferredKind === "CF_PIVA_PARTICELLE" && (row.original.matches_count ?? 0) > 1 ? (
                <p className="mt-1 text-xs text-gray-500">Particelle trovate: {row.original.matches_count}</p>
              ) : null}
            </div>
          );
        },
      },
    ],
    [inferredKind],
  );

  async function parseSelectedFile(file: File): Promise<void> {
    setError(null);
    setBusy(true);
    try {
      const parsed = await readFileToRows(file);
      if (parsed.rows.length === 0) {
        throw new Error("File vuoto o senza righe valide.");
      }
      setInferredKind(parsed.kind);
      setParsedRows(parsed.rows);
      setSkippedRows(parsed.skipped);
      setResults([]);
      setActiveJobId(null);
      setBulkProgress((prev) => ({ ...prev, open: false }));
    } catch (e) {
      setInferredKind(null);
      setParsedRows([]);
      setSkippedRows(0);
      setResults([]);
      setActiveJobId(null);
      setBulkProgress((prev) => ({ ...prev, open: false }));
      setError(e instanceof Error ? e.message : "Errore parsing file");
    } finally {
      setBusy(false);
    }
  }

  async function runBulkSearch(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    if (parsedRows.length === 0) {
      setError("Carica un file e verifica che contenga righe valide.");
      return;
    }
    setBusy(true);
    setResults([]);
    setActiveJobId(null);
    setBulkProgress({
      open: true,
      processed: 0,
      total: parsedRows.length,
      currentLabel: "Preparazione elaborazione...",
      phase: "processing",
    });
    try {
      const includeCapacitasLive = inferredKind === "COMUNE_FOGLIO_PARTICELLA_INTESTATARI";
      const chunkSize = includeCapacitasLive ? 5 : 25;
      const collectedResults: CatAnagraficaBulkRowResult[] = [];

      for (let start = 0; start < parsedRows.length; start += chunkSize) {
        const chunk = parsedRows.slice(start, start + chunkSize);
        const firstRow = chunk[0];
        setBulkProgress((prev) => ({
          ...prev,
          currentLabel: firstRow ? progressRowLabel(firstRow) : "Preparazione...",
          phase: "processing",
        }));
        const response = await catastoBulkSearchAnagrafica(token, {
          kind: inferredKind ?? undefined,
          include_capacitas_live: includeCapacitasLive,
          rows: chunk,
        });
        collectedResults.push(...response.results);
        setResults([...collectedResults]);
        setBulkProgress((prev) => ({
          ...prev,
          processed: Math.min(start + chunk.length, parsedRows.length),
        }));
      }

      setBulkProgress((prev) => ({
        ...prev,
        currentLabel: "Salvataggio nello storico...",
        phase: "saving",
      }));
      const job = await catastoSaveElaborazioneMassivaJob(token, {
        source_filename: sourceFile?.name ?? null,
        skipped_rows: skippedRows,
        payload: { kind: inferredKind ?? undefined, include_capacitas_live: includeCapacitasLive, rows: parsedRows },
        results: collectedResults,
      });
      setResults(job.results);
      setActiveJobId(job.id);
      setOperationHistory((prev) => [job, ...prev].slice(0, 5));
      setBulkProgress((prev) => ({
        ...prev,
        processed: parsedRows.length,
        currentLabel: "Elaborazione completata.",
        phase: "completed",
      }));
      setError(null);
    } catch (e) {
      setBulkProgress((prev) => ({
        ...prev,
        currentLabel: e instanceof Error ? e.message : "Errore elaborazione massiva",
        phase: "error",
      }));
      setError(e instanceof Error ? e.message : "Errore elaborazione massiva");
    } finally {
      setBusy(false);
    }
  }

  async function exportVeloceFrom(
    token: string,
    kind: "CF_PIVA_PARTICELLE" | "COMUNE_FOGLIO_PARTICELLA_INTESTATARI",
    exportResults: CatAnagraficaBulkRowResult[],
    format: "csv" | "xlsx",
  ): Promise<void> {
    const matchesForLinks = exportResults.flatMap((r) => r.matches ?? (r.match ? [r.match] : []));
    const urlByMatchKey = matchesForLinks.length ? await resolveCapacitasRptCertificatoUrls(token, matchesForLinks) : new Map<string, string>();
    const rows: Record<string, unknown>[] = [];
    for (const r of exportResults) {
      const matches = r.matches ?? (r.match ? [r.match] : []);
      const buildMatchLinkKey = (match?: (typeof matches)[0]): string =>
        [
          match?.utenza_latest?.cco?.trim() ?? "",
          match?.cert_com ?? "",
          match?.cert_pvc ?? "",
          match?.cert_fra ?? "",
          match?.cert_ccs ?? "",
        ].join("|");
      const buildBase = (m?: (typeof matches)[0]) =>
        kind === "CF_PIVA_PARTICELLE"
          ? {
              cf_input: r.codice_fiscale_input ?? "",
              piva_input: r.partita_iva_input ?? "",
              comune: m?.comune ?? "",
              foglio: m?.foglio ?? "",
              particella: m?.particella ?? "",
              sub: m?.subalterno ?? "",
              esito: formatEsitoForExport(r.esito),
              "trovato in esito consorzio": formatConsorzioEsitoForExport(Boolean(m?.presente_in_catasto_consorzio)),
              cco: m?.utenza_latest?.cco ?? "",
              link_involture: m?.utenza_latest?.cco ? urlByMatchKey.get(buildMatchLinkKey(m)) ?? "" : "",
              apri_involture: "",
              stato_ruolo: m?.stato_ruolo ?? "",
              stato_cnc: m?.stato_cnc ?? "",
            }
          : {
              comune: m?.comune ?? r.comune_input ?? "",
              sezione: r.sezione_input ?? "",
              foglio: m?.foglio ?? r.foglio_input ?? "",
              particella: m?.particella ?? r.particella_input ?? "",
              sub: m?.subalterno ?? r.sub_input ?? "",
              esito: formatEsitoForExport(r.esito),
              "trovato in esito consorzio": formatConsorzioEsitoForExport(Boolean(m?.presente_in_catasto_consorzio)),
              cco: m?.utenza_latest?.cco ?? "",
              link_involture: m?.utenza_latest?.cco ? urlByMatchKey.get(buildMatchLinkKey(m)) ?? "" : "",
              apri_involture: "",
              stato_ruolo: m?.stato_ruolo ?? "",
              stato_cnc: m?.stato_cnc ?? "",
            };

      const emptyInt = {
        n_intestatari: 0,
        rank: "",
        cf: "",
        tipo: "",
        cognome: "",
        nome: "",
        denominazione: "",
        ragione_sociale: "",
        data_nascita: "",
        luogo_nascita: "",
        comune_residenza: "",
        indirizzo: "",
        cap: "",
        telefono: "",
        email: "",
        deceduto: "",
        note: "",
      };

      if (matches.length === 0) {
        rows.push({ ...buildBase(), ...emptyInt });
        continue;
      }

      for (const m of matches) {
        const intestatari = m.intestatari ?? [];
        const n = intestatari.length;
        const base = buildBase(m);
        if (n === 0) {
          rows.push({ ...base, ...emptyInt, note: m?.note ?? "" });
          continue;
        }
        intestatari.forEach((intestatario, index) => {
          rows.push({
            ...base,
            n_intestatari: n,
            rank: `${index + 1}/${n}`,
            cf: intestatario.codice_fiscale ?? "",
            tipo: intestatario.tipo ?? "",
            cognome: intestatario.cognome ?? "",
            nome: intestatario.nome ?? "",
            denominazione: intestatarioDisplayName(intestatario),
            ragione_sociale: intestatario.ragione_sociale ?? "",
            data_nascita: intestatario.data_nascita ?? "",
            luogo_nascita: intestatario.luogo_nascita ?? "",
            comune_residenza: intestatario.comune_residenza ?? "",
            indirizzo: intestatario.indirizzo ?? "",
            cap: intestatario.cap ?? "",
            telefono: intestatario.telefono ?? "",
            email: intestatario.email ?? "",
            deceduto: intestatario.deceduto ? "si" : "",
            note: m?.note ?? "",
          });
        });
      }
    }

    const basename = kind === "CF_PIVA_PARTICELLE" ? "catasto-intestatari-da-cf" : "catasto-intestatari";
    if (format === "csv") {
      const csv = XLSX.utils.sheet_to_csv(XLSX.utils.json_to_sheet(rows));
      triggerDownload(new Blob([csv], { type: "text/csv;charset=utf-8" }), `${basename}.csv`);
      return;
    }

    const ws = XLSX.utils.json_to_sheet(rows);
    if (rows.length > 0) {
      const headers = Object.keys(rows[0] ?? {});
      const linkCol = headers.indexOf("link_involture");
      const apriCol = headers.indexOf("apri_involture");
      const ref = ws["!ref"];
      if (linkCol >= 0 && apriCol >= 0 && ref) {
        const range = XLSX.utils.decode_range(ref);
        for (let r = range.s.r + 1; r <= range.e.r; r += 1) {
          const linkA1 = XLSX.utils.encode_cell({ r, c: linkCol });
          const apriA1 = XLSX.utils.encode_cell({ r, c: apriCol });
          // Formula per riga: funziona in Excel; in Fogli Google resta valida dopo import xlsx.
          // (ARRAYFORMULA è solo Fogli e non è supportata da Excel nello stesso modo.)
          ws[apriA1] = { f: `IF(${linkA1}="","",HYPERLINK(${linkA1},"Clicca qui"))` };
        }
      }
    }

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "intestatari");
    const out = XLSX.write(wb, { type: "array", bookType: "xlsx" });
    triggerDownload(new Blob([out], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }), `${basename}.xlsx`);
  }

  async function exportVeloce(format: "csv" | "xlsx"): Promise<void> {
    if (results.length === 0 || !inferredKind) return;
    const token = getStoredAccessToken();
    if (!token) return;
    setBusy(true);
    try {
      let exportResults = results;
      let exportKind = inferredKind;
      if (activeJobId) {
        const refreshedJob = await catastoGetElaborazioneMassivaJob(token, activeJobId);
        exportResults = refreshedJob.results;
        exportKind = refreshedJob.kind;
        setResults(refreshedJob.results);
        setInferredKind(refreshedJob.kind);
      }
      await exportVeloceFrom(token, exportKind, exportResults, format);
    } finally {
      setBusy(false);
    }
  }

  const progressPercent =
    bulkProgress.total > 0 ? Math.round((bulkProgress.processed / bulkProgress.total) * 100) : 0;
  const canCloseProgress = bulkProgress.phase === "completed" || bulkProgress.phase === "error";

  return (
    <div className="page-stack">
      {error ? (
        <AlertBanner variant="danger" title="Errore">
          {error}
        </AlertBanner>
      ) : null}

      {showDeleteHistoryConfirm ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <p className="text-lg font-semibold text-gray-900">Cancellare lo storico?</p>
            <p className="mt-2 text-sm text-gray-600">
              Verranno eliminati definitivamente tutti i job di elaborazione massiva salvati per il tuo utente. Dopo il refresh della pagina non saranno più visibili.
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" className="btn-secondary" disabled={busy} onClick={() => setShowDeleteHistoryConfirm(false)}>
                Annulla
              </button>
              <button type="button" className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60" disabled={busy} onClick={() => void deleteOperationHistory()}>
                {busy ? "Cancellazione..." : "Cancella storico"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {bulkProgress.open ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-lg font-semibold text-gray-900">
                  {bulkProgress.phase === "completed" ? "Elaborazione completata" : bulkProgress.phase === "error" ? "Elaborazione interrotta" : "Elaborazione in corso"}
                </p>
                <p className="mt-1 text-sm text-gray-600">
                  {bulkProgress.phase === "saving"
                    ? "Salvataggio dei risultati nello storico."
                    : bulkProgress.phase === "completed"
                      ? "Elaborazione completata."
                      : bulkProgress.phase === "error"
                        ? "L'elaborazione si e interrotta."
                        : "Sto processando le righe del file a blocchi."}
                </p>
              </div>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-semibold text-slate-700">
                {progressPercent}%
              </span>
            </div>

            <div className="mt-5">
              <div className="mb-2 flex items-center justify-between text-sm text-gray-600">
                <span>
                  {bulkProgress.processed} di {bulkProgress.total} righe
                </span>
                <span>{bulkProgress.phase === "saving" ? "Salvataggio" : bulkProgress.phase === "completed" ? "Completato" : "Elaborazione"}</span>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-slate-100">
                <div
                  className={[
                    "h-full rounded-full transition-all duration-300",
                    bulkProgress.phase === "error" ? "bg-red-500" : bulkProgress.phase === "completed" ? "bg-emerald-500" : "bg-blue-600",
                  ].join(" ")}
                  style={{ width: `${Math.max(progressPercent, bulkProgress.phase === "processing" ? 4 : 0)}%` }}
                />
              </div>
              <p className="mt-3 text-sm text-gray-700">
                Riga corrente: <span className="font-medium">{bulkProgress.currentLabel || "Preparazione..."}</span>
              </p>
            </div>

            {canCloseProgress ? (
              <div className="mt-5 flex justify-end">
                <button type="button" className="btn-primary" onClick={() => setBulkProgress((prev) => ({ ...prev, open: false }))}>
                  Chiudi
                </button>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      <article className="panel-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-gray-900">Template ed upload</p>
            <p className="mt-1 text-sm text-gray-500">
              Seleziona un template, scarica l’esempio e carica un file <span className="font-medium">.xlsx</span> o{" "}
              <span className="font-medium">.csv</span> con le colonne richieste.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-secondary"
              disabled={busy || parsedRows.length === 0}
              onClick={() => {
                setSourceFile(null);
                setParsedRows([]);
                setSkippedRows(0);
                setResults([]);
                setActiveJobId(null);
                setBulkProgress((prev) => ({ ...prev, open: false }));
                setError(null);
              }}
            >
              Reset
            </button>
          </div>
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <span className="label-caption">Template CF/P.IVA → Particelle</span>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-secondary"
                disabled={busy}
                onClick={() => {
                  const sheet = XLSX.utils.json_to_sheet([{ codice_fiscale: "RSSMRA80A01H501U", partita_iva: "" }]);
                  const csv = XLSX.utils.sheet_to_csv(sheet);
                  triggerDownload(new Blob([csv], { type: "text/csv;charset=utf-8" }), "template-cf-piva-particelle.csv");
                }}
              >
                Template CSV
              </button>
              <button
                type="button"
                className="btn-secondary"
                disabled={busy}
                onClick={() => {
                  const wb = XLSX.utils.book_new();
                  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet([{ codice_fiscale: "RSSMRA80A01H501U", partita_iva: "" }]), "template");
                  const out = XLSX.write(wb, { type: "array", bookType: "xlsx" });
                  triggerDownload(
                    new Blob([out], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }),
                    "template-cf-piva-particelle.xlsx",
                  );
                }}
              >
                Template Excel
              </button>
            </div>
          </div>

          <div className="space-y-2">
            <span className="label-caption">Template Particelle → Intestatari</span>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-secondary"
                disabled={busy}
                onClick={() => {
                  const sheet = XLSX.utils.json_to_sheet([{ comune: "A357", sezione: "", foglio: "5", particella: "120", sub: "" }]);
                  const csv = XLSX.utils.sheet_to_csv(sheet);
                  triggerDownload(new Blob([csv], { type: "text/csv;charset=utf-8" }), "template-particelle-intestatari.csv");
                }}
              >
                Template CSV
              </button>
              <button
                type="button"
                className="btn-secondary"
                disabled={busy}
                onClick={() => {
                  const wb = XLSX.utils.book_new();
                  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet([{ comune: "A357", sezione: "", foglio: "5", particella: "120", sub: "" }]), "template");
                  const out = XLSX.write(wb, { type: "array", bookType: "xlsx" });
                  triggerDownload(
                    new Blob([out], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }),
                    "template-particelle-intestatari.xlsx",
                  );
                }}
              >
                Template Excel
              </button>
            </div>
          </div>
        </div>

        <div className="mt-4 rounded-xl border border-dashed border-gray-200 bg-gray-50/70 p-4">
          <div className="flex flex-wrap items-center gap-3">
            <input
              id="catasto-bulk-file"
              type="file"
              accept=".xlsx,.csv"
              className="sr-only"
              aria-label="File ricerca anagrafica"
              disabled={busy}
              onChange={(e) => {
                const file = e.target.files?.[0] ?? null;
                if (!file) return;
                setSourceFile(file);
                void parseSelectedFile(file);
              }}
            />
            <label
              htmlFor="catasto-bulk-file"
              className={[
                "inline-flex cursor-pointer items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-800 shadow-sm transition hover:bg-gray-50",
                busy ? "pointer-events-none opacity-60" : "",
              ].join(" ")}
            >
              <DocumentIcon className="h-4 w-4" />
              Scegli file
            </label>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-gray-900">
                {sourceFile ? sourceFile.name : "Nessun file selezionato"}
              </p>
              <p className="mt-1 text-xs text-gray-500">
                {sourceFile ? (
                  <>
                    {parsedRows.length} righe pronte
                    {skippedRows ? ` · ${skippedRows} vuote saltate` : ""}
                    {inferredKind ? ` · ${inferredKind === "CF_PIVA_PARTICELLE" ? "CF/P.IVA → Particelle" : "Particelle → Intestatari"}` : ""}
                  </>
                ) : (
                  "Carica un file .xlsx o .csv dopo aver scaricato il template corretto."
                )}
              </p>
            </div>
          </div>
        </div>

        {inferredKind ? (
          <div className="mt-4 rounded-xl border border-gray-100 bg-gray-50 p-4">
            <p className="text-sm font-medium text-gray-900">Esportazione</p>
            <p className="mt-3 text-sm text-gray-500">
              Una riga per intestatario.{" "}
              {inferredKind === "CF_PIVA_PARTICELLE"
                ? "Colonne: CF input · P.IVA input · Comune · Foglio · Particella · Sub"
                : "Colonne: Comune · Sezione · Foglio · Particella · Sub"}{" "}
              · Esito · Trovato in esito consorzio · CCO · Link InVolture · Apri InVolture (link cliccabile nel .xlsx) · N intestatari · Rank intestatario (1/n) · CF · Tipo · Cognome · Nome · Denominazione · Ragione Sociale · Data Nascita · Luogo Nascita · Comune Residenza · Indirizzo · CAP · Telefono · Email · Deceduto
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <button className="btn-secondary" type="button" disabled={busy || results.length === 0} onClick={() => void exportVeloce("csv")}>
                <DocumentIcon className="h-4 w-4" />
                Export CSV
              </button>
              <button className="btn-secondary" type="button" disabled={busy || results.length === 0} onClick={() => void exportVeloce("xlsx")}>
                <DocumentIcon className="h-4 w-4" />
                Export Excel
              </button>
            </div>
          </div>
        ) : null}

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button className="btn-primary" type="button" disabled={busy || parsedRows.length === 0} onClick={() => void runBulkSearch()}>
            <RefreshIcon className="h-4 w-4" />
            {busy ? "Elaborazione…" : "Elabora righe"}
          </button>
        </div>
      </article>

      <article className="panel-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-gray-900">Ultime operazioni</p>
            <p className="mt-1 text-sm text-gray-500">Storico locale delle ultime 5 elaborazioni eseguite da questo browser.</p>
          </div>
          {operationHistory.length > 0 ? (
            <button
              type="button"
              className="btn-secondary"
              disabled={busy}
              onClick={() => setShowDeleteHistoryConfirm(true)}
            >
              Cancella storico
            </button>
          ) : null}
        </div>
        {operationHistory.length === 0 ? (
          <p className="mt-4 text-sm text-gray-500">Nessuna operazione salvata.</p>
        ) : (
          <div className="mt-4 space-y-2">
            {operationHistory.map((item) => (
              <div key={item.id} className="rounded-xl border border-gray-100 bg-gray-50 p-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{item.source_filename ?? "Elaborazione senza file"}</p>
                    <p className="mt-1 text-xs text-gray-500">
                      {new Intl.DateTimeFormat("it-IT", {
                        dateStyle: "short",
                        timeStyle: "short",
                      }).format(new Date(item.created_at))}{" "}
                      · {formatOperationKind(item.kind)}
                      {item.skipped_rows ? ` · ${item.skipped_rows} righe vuote saltate` : ""}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2 text-xs text-gray-700">
                    <span className="rounded-full bg-white px-2.5 py-1">Totale: {item.summary.total}</span>
                    <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-emerald-700">FOUND: {item.summary.found}</span>
                    <span className="rounded-full bg-white px-2.5 py-1">NOT_FOUND: {item.summary.notFound}</span>
                    <span className="rounded-full bg-amber-50 px-2.5 py-1 text-amber-700">MULTIPLE: {item.summary.multiple}</span>
                    <span className="rounded-full bg-red-50 px-2.5 py-1 text-red-700">ERROR: {item.summary.error}</span>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="btn-secondary"
                    disabled={busy}
                    onClick={() => {
                      const token = getStoredAccessToken();
                      if (!token) return;
                      void (async () => {
                        try {
                          const job = await catastoGetElaborazioneMassivaJob(token, item.id);
                          setInferredKind(job.kind);
                          setResults(job.results);
                          setActiveJobId(job.id);
                          setError(null);
                        } catch (e) {
                          setError(e instanceof Error ? e.message : "Errore caricamento job");
                        }
                      })();
                    }}
                  >
                    Ricarica risultati
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    disabled={busy}
                    onClick={() => {
                      const token = getStoredAccessToken();
                      if (!token) return;
                      void (async () => {
                        try {
                          const job = await catastoGetElaborazioneMassivaJob(token, item.id);
                          await exportVeloceFrom(token, job.kind, job.results, "csv");
                        } catch (e) {
                          setError(e instanceof Error ? e.message : "Errore export job");
                        }
                      })();
                    }}
                  >
                    Riesporta CSV
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    disabled={busy}
                    onClick={() => {
                      const token = getStoredAccessToken();
                      if (!token) return;
                      void (async () => {
                        try {
                          const job = await catastoGetElaborazioneMassivaJob(token, item.id);
                          await exportVeloceFrom(token, job.kind, job.results, "xlsx");
                        } catch (e) {
                          setError(e instanceof Error ? e.message : "Errore export job");
                        }
                      })();
                    }}
                  >
                    Riesporta Excel
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </article>

      <article className="panel-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-gray-900">Riepilogo</p>
            <p className="mt-1 text-sm text-gray-500">Contatori sintetici dell’elaborazione.</p>
          </div>
          <div className="flex flex-wrap gap-2 text-sm text-gray-700">
            <span className="rounded-full bg-gray-100 px-3 py-1">Totale: {summary.total}</span>
            <span className="rounded-full bg-emerald-50 px-3 py-1 text-emerald-700">FOUND: {summary.found}</span>
            <span className="rounded-full bg-gray-100 px-3 py-1">NOT_FOUND: {summary.notFound}</span>
            <span className="rounded-full bg-amber-50 px-3 py-1 text-amber-700">MULTIPLE: {summary.multiple}</span>
            <span className="rounded-full bg-amber-50 px-3 py-1 text-amber-800">INVALID: {summary.invalid}</span>
            <span className="rounded-full bg-red-50 px-3 py-1 text-red-700">ERROR: {summary.error}</span>
          </div>
        </div>
      </article>

      <article className="panel-card">
        {busy && results.length === 0 ? (
          <div className="rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-500">Elaborazione…</div>
        ) : results.length === 0 ? (
          <EmptyState icon={DocumentIcon} title="Nessun risultato" description="Carica un file e avvia l’elaborazione per vedere la preview." />
        ) : (
          <DataTable data={results.slice(0, 500)} columns={columns} initialPageSize={12} />
        )}
      </article>
    </div>
  );
}
