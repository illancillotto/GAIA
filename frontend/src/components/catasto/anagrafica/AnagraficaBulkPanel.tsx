"use client";

import * as XLSX from "xlsx";
import { useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { DataTable } from "@/components/table/data-table";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertBanner } from "@/components/ui/alert-banner";
import { DocumentIcon, RefreshIcon } from "@/components/ui/icons";
import {
  capacitasGetRptCertificatoLink,
  catastoBulkSearchAnagrafica,
  catastoCreateElaborazioneMassivaJob,
  catastoGetElaborazioneMassivaJob,
  catastoGetParticellaUtenze,
  catastoListElaborazioniMassiveJobs,
} from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatAnagraficaBulkJobItem, CatAnagraficaBulkRowInput, CatAnagraficaBulkRowResult, CatUtenzaIrrigua } from "@/types/catasto";

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

type ExportFieldDef = { key: string; label: string };

function pickFields(row: Record<string, unknown>, keys: string[]): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const key of keys) out[key] = row[key];
  return out;
}

function normalizeSelectedFields(selected: string[], available: string[]): string[] {
  const set = new Set(selected);
  return available.filter((k) => set.has(k));
}

async function resolveCapacitasRptCertificatoUrls(
  token: string,
  ccos: string[],
): Promise<Map<string, string>> {
  const out = new Map<string, string>();
  const unique = Array.from(new Set(ccos.map((c) => c.trim()).filter(Boolean)));
  const concurrency = 8;
  let idx = 0;

  async function worker(): Promise<void> {
    for (;;) {
      const current = unique[idx];
      idx += 1;
      if (!current) return;
      try {
        const { url } = await capacitasGetRptCertificatoLink(token, current);
        out.set(current, url);
      } catch {
        out.set(current, "");
      }
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

type BulkOperationHistoryItem = CatAnagraficaBulkJobItem;

const EXPORT_FIELD_DEFS_CF_PARTICELLE: ExportFieldDef[] = [
  { key: "row_index", label: "Row index" },
  { key: "kind", label: "Tipo" },
  { key: "codice_fiscale_input", label: "CF input" },
  { key: "partita_iva_input", label: "P.IVA input" },
  { key: "esito", label: "Esito" },
  { key: "message", label: "Messaggio" },
  { key: "matches_count", label: "Match count" },
  { key: "particella_id", label: "Particella ID" },
  { key: "comune", label: "Comune" },
  { key: "cod_comune_capacitas", label: "Cod. comune Capacitas" },
  { key: "codice_catastale", label: "Codice catastale" },
  { key: "foglio", label: "Foglio" },
  { key: "particella", label: "Particella" },
  { key: "subalterno", label: "Subalterno" },
  { key: "num_distretto", label: "Num distretto" },
  { key: "nome_distretto", label: "Nome distretto" },
  { key: "superficie_mq", label: "Sup. catastale (mq)" },
  { key: "superficie_grafica_mq", label: "Sup. grafica (mq)" },
  { key: "utenza_latest_cco", label: "CCO (utenza latest)" },
  { key: "capacitas_rpt_certificato_url", label: "Link Capacitas (rptCertificato)" },
  { key: "dettaglio_particella_url", label: "Link GAIA (dettaglio particella)" },
];

const EXPORT_FIELD_DEFS_PARTICELLE_INTESTATARI: ExportFieldDef[] = [
  { key: "row_index", label: "Row index" },
  { key: "kind", label: "Tipo" },
  { key: "comune_input", label: "Comune input" },
  { key: "sezione_input", label: "Sezione input" },
  { key: "foglio_input", label: "Foglio input" },
  { key: "particella_input", label: "Particella input" },
  { key: "sub_input", label: "Sub input" },
  { key: "esito", label: "Esito" },
  { key: "message", label: "Messaggio" },
  { key: "matches_count", label: "Match count" },
  { key: "match_rank", label: "Rank match" },
  { key: "particella_id", label: "Particella ID" },
  { key: "intestatari", label: "Intestatari (flatten)" },
  { key: "intestatari_cf_flatten", label: "Codici fiscali intestatari" },
  { key: "utenze_count", label: "Utenze count" },
  { key: "particella_comune", label: "Comune" },
  { key: "particella_cod_comune_capacitas", label: "Cod. comune Capacitas" },
  { key: "particella_foglio", label: "Foglio" },
  { key: "particella_particella", label: "Particella" },
  { key: "particella_subalterno", label: "Subalterno" },
  { key: "particella_num_distretto", label: "Num distretto" },
  { key: "particella_nome_distretto", label: "Nome distretto" },
  { key: "particella_superficie_mq", label: "Sup. catastale (mq)" },
  { key: "particella_superficie_grafica_mq", label: "Sup. grafica (mq)" },
  { key: "utenza_cco", label: "CCO (utenza)" },
  { key: "capacitas_rpt_certificato_url", label: "Link Capacitas (rptCertificato)" },
  { key: "dettaglio_particella_url", label: "Link GAIA (dettaglio particella)" },
];

const EXPORT_FIELD_DEFS_UTENZE: ExportFieldDef[] = [
  { key: "utenza_id", label: "Utenza ID" },
  { key: "utenza_import_batch_id", label: "Import batch ID" },
  { key: "utenza_anno_campagna", label: "Anno campagna" },
  { key: "utenza_cco", label: "CCO" },
  { key: "capacitas_rpt_certificato_url", label: "Link Capacitas (rptCertificato)" },
  { key: "utenza_denominazione", label: "Denominazione (Capacitas)" },
  { key: "utenza_codice_fiscale", label: "Codice fiscale (Capacitas)" },
  { key: "utenza_codice_fiscale_raw", label: "Codice fiscale raw (Capacitas)" },
  { key: "intestatari_flatten", label: "Intestatari catasto (tutti)" },
  { key: "intestatario_cf", label: "Intestatario: CF" },
  { key: "intestatario_tipo", label: "Intestatario: tipo" },
  { key: "intestatario_cognome", label: "Intestatario: cognome" },
  { key: "intestatario_nome", label: "Intestatario: nome" },
  { key: "intestatario_denominazione", label: "Intestatario: denominazione" },
  { key: "intestatario_ragione_sociale", label: "Intestatario: ragione sociale" },
  { key: "intestatario_data_nascita", label: "Intestatario: data nascita" },
  { key: "intestatario_luogo_nascita", label: "Intestatario: luogo nascita" },
  { key: "intestatario_deceduto", label: "Intestatario: deceduto" },
  { key: "utenza_cod_provincia", label: "Cod provincia" },
  { key: "utenza_cod_frazione", label: "Cod frazione" },
  { key: "utenza_sup_irrigabile_mq", label: "Sup irrigabile (mq)" },
  { key: "utenza_ind_spese_fisse", label: "Indice spese fisse" },
  { key: "utenza_imponibile_sf", label: "Imponibile SF" },
  { key: "utenza_esente_0648", label: "Esente 0648" },
  { key: "utenza_aliquota_0648", label: "Aliquota 0648" },
  { key: "utenza_importo_0648", label: "Importo 0648" },
  { key: "utenza_aliquota_0985", label: "Aliquota 0985" },
  { key: "utenza_importo_0985", label: "Importo 0985" },
  { key: "utenza_anomalia_superficie", label: "Anomalia: superficie" },
  { key: "utenza_anomalia_cf_invalido", label: "Anomalia: CF invalido" },
  { key: "utenza_anomalia_cf_mancante", label: "Anomalia: CF mancante" },
  { key: "utenza_anomalia_comune_invalido", label: "Anomalia: comune invalido" },
  { key: "utenza_anomalia_particella_assente", label: "Anomalia: particella assente" },
  { key: "utenza_anomalia_imponibile", label: "Anomalia: imponibile" },
  { key: "utenza_anomalia_importi", label: "Anomalia: importi" },
  { key: "utenza_created_at", label: "Created at" },
];

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
      throw new Error("Colonne minime mancanti. Richieste: comune, foglio, particella (opzionali: sezione, sub).");
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

      if (!comune && !foglio && !particella && !sub && !sezione) {
        skipped += 1;
        continue;
      }

      rows.push({
        row_index: i + 2,
        comune: comune || null,
        sezione: sezione || null,
        foglio: foglio || null,
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
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [operationHistory, setOperationHistory] = useState<BulkOperationHistoryItem[]>([]);
  const [exportFieldsParticelle, setExportFieldsParticelle] = useState<string[]>([]);
  const [exportFieldsUtenze, setExportFieldsUtenze] = useState<string[]>([]);
  const [exportMode, setExportMode] = useState<"veloce" | "avanzato">("veloce");

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

  useEffect(() => {
    // reset export fields defaults when the inferred kind changes
    if (inferredKind === "CF_PIVA_PARTICELLE") {
      setExportFieldsParticelle(EXPORT_FIELD_DEFS_CF_PARTICELLE.map((f) => f.key));
      setExportFieldsUtenze([]);
      return;
    }
    if (inferredKind === "COMUNE_FOGLIO_PARTICELLA_INTESTATARI") {
      setExportFieldsParticelle(EXPORT_FIELD_DEFS_PARTICELLE_INTESTATARI.map((f) => f.key));
      setExportFieldsUtenze(EXPORT_FIELD_DEFS_UTENZE.map((f) => f.key));
      return;
    }
    setExportFieldsParticelle([]);
    setExportFieldsUtenze([]);
  }, [inferredKind]);

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
                    .map((i) => i.denominazione ?? i.ragione_sociale ?? [i.cognome, i.nome].filter(Boolean).join(" "))
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
    } catch (e) {
      setInferredKind(null);
      setParsedRows([]);
      setSkippedRows(0);
      setResults([]);
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
    try {
      try {
        const job = await catastoCreateElaborazioneMassivaJob(token, {
          source_filename: sourceFile?.name ?? null,
          skipped_rows: skippedRows,
          payload: { kind: inferredKind ?? undefined, include_capacitas_live: false, rows: parsedRows },
        });
        setResults(job.results);
        setOperationHistory((prev) => [job, ...prev].slice(0, 5));
      } catch {
        // Backward-compatible fallback if the jobs API is not available yet.
        const response = await catastoBulkSearchAnagrafica(token, { kind: inferredKind ?? undefined, include_capacitas_live: false, rows: parsedRows });
        setResults(response.results);
      }
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore elaborazione massiva");
    } finally {
      setBusy(false);
    }
  }

  async function exportCsvFrom(
    token: string,
    kind: "CF_PIVA_PARTICELLE" | "COMUNE_FOGLIO_PARTICELLA_INTESTATARI",
    resultsArg: CatAnagraficaBulkRowResult[],
  ): Promise<void> {
    if (resultsArg.length === 0) return;
    if (kind === "COMUNE_FOGLIO_PARTICELLA_INTESTATARI") {
        const particellaIds = Array.from(
          new Set(
            resultsArg
              .flatMap((r) => r.matches ?? (r.match ? [r.match] : []))
              .map((m) => m.particella_id)
              .filter((id): id is string => Boolean(id)),
          ),
        );

        const utenzeByParticella = new Map<string, CatUtenzaIrrigua[]>();
        await Promise.all(
          particellaIds.map(async (id) => {
            try {
              const utenze = await catastoGetParticellaUtenze(token, id);
              utenzeByParticella.set(id, utenze ?? []);
            } catch {
              utenzeByParticella.set(id, []);
            }
          }),
        );

        const flat: Record<string, unknown>[] = [];
        const ccos: string[] = [];
        for (const r of resultsArg) {
          const matches = r.matches ?? (r.match ? [r.match] : []);

          if (matches.length === 0) {
            flat.push({
              row_index: r.row_index,
              kind,
              comune_input: r.comune_input ?? "",
              sezione_input: r.sezione_input ?? "",
              foglio_input: r.foglio_input ?? "",
              particella_input: r.particella_input ?? "",
              sub_input: r.sub_input ?? "",
              esito: r.esito,
              message: r.message,
              matches_count: r.matches_count ?? "",
            });
            continue;
          }

          for (let index = 0; index < matches.length; index += 1) {
            const m = matches[index];
            const intest = (m.intestatari ?? [])
              .map((i) => (i.denominazione ?? i.ragione_sociale ?? [i.cognome, i.nome].filter(Boolean).join(" ")) || "")
              .filter(Boolean)
              .join(" | ");
            const utenze = utenzeByParticella.get(m.particella_id) ?? [];
            const firstInt = m.intestatari?.[0];
            const intestCf = (m.intestatari ?? []).map((i) => i.codice_fiscale).filter(Boolean).join(" | ");
            const baseRow = {
              row_index: r.row_index,
              kind,
              comune_input: r.comune_input ?? "",
              sezione_input: r.sezione_input ?? "",
              foglio_input: r.foglio_input ?? "",
              particella_input: r.particella_input ?? "",
              sub_input: r.sub_input ?? "",
              esito: r.esito,
              message: r.message,
              matches_count: r.matches_count ?? matches.length,
              match_rank: index + 1,
              particella_id: m.particella_id,
              intestatari: intest,
              intestatari_cf_flatten: intestCf,
              intestatari_flatten: intest,
              intestatario_cf: firstInt?.codice_fiscale ?? "",
              intestatario_tipo: firstInt?.tipo ?? "",
              intestatario_cognome: firstInt?.cognome ?? "",
              intestatario_nome: firstInt?.nome ?? "",
              intestatario_denominazione: firstInt?.denominazione ?? "",
              intestatario_ragione_sociale: firstInt?.ragione_sociale ?? "",
              intestatario_data_nascita: firstInt?.data_nascita ?? "",
              intestatario_luogo_nascita: firstInt?.luogo_nascita ?? "",
              intestatario_deceduto: String(firstInt?.deceduto ?? ""),
              particella_comune: m.comune ?? "",
              particella_cod_comune_capacitas: m.cod_comune_capacitas ?? "",
              particella_foglio: m.foglio ?? "",
              particella_particella: m.particella ?? "",
              particella_subalterno: m.subalterno ?? "",
              particella_num_distretto: m.num_distretto ?? "",
              particella_nome_distretto: m.nome_distretto ?? "",
              particella_superficie_mq: m.superficie_mq ?? "",
              particella_superficie_grafica_mq: m.superficie_grafica_mq ?? "",
              dettaglio_particella_url: `/catasto/particelle/${m.particella_id}`,
              capacitas_rpt_certificato_url: "",
              utenza_cco: "",
            };
            if (utenze.length === 0) {
              flat.push(baseRow);
              continue;
            }
            for (const u of utenze) {
              if (u.cco) ccos.push(u.cco);
              flat.push({
                ...baseRow,
                // flatten utenza (tutti i campi disponibili dal tipo)
                utenza_id: u.id,
                utenza_import_batch_id: u.import_batch_id,
                utenza_anno_campagna: u.anno_campagna,
                utenza_cco: u.cco ?? "",
                capacitas_rpt_certificato_url: "",
                utenza_comune_id: u.comune_id ?? "",
                utenza_cod_provincia: u.cod_provincia ?? "",
                utenza_cod_comune_capacitas: u.cod_comune_capacitas ?? "",
                utenza_cod_frazione: u.cod_frazione ?? "",
                utenza_num_distretto: u.num_distretto ?? "",
                utenza_nome_distretto_loc: u.nome_distretto_loc ?? "",
                utenza_nome_comune: u.nome_comune ?? "",
                utenza_sezione_catastale: u.sezione_catastale ?? "",
                utenza_foglio: u.foglio ?? "",
                utenza_particella: u.particella ?? "",
                utenza_subalterno: u.subalterno ?? "",
                utenza_particella_id: u.particella_id ?? "",
                utenza_sup_catastale_mq: u.sup_catastale_mq ?? "",
                utenza_sup_irrigabile_mq: u.sup_irrigabile_mq ?? "",
                utenza_ind_spese_fisse: u.ind_spese_fisse ?? "",
                utenza_imponibile_sf: u.imponibile_sf ?? "",
                utenza_esente_0648: u.esente_0648,
                utenza_aliquota_0648: u.aliquota_0648 ?? "",
                utenza_importo_0648: u.importo_0648 ?? "",
                utenza_aliquota_0985: u.aliquota_0985 ?? "",
                utenza_importo_0985: u.importo_0985 ?? "",
                utenza_denominazione: u.denominazione ?? "",
                utenza_codice_fiscale: u.codice_fiscale ?? "",
                utenza_codice_fiscale_raw: u.codice_fiscale_raw ?? "",
                utenza_anomalia_superficie: u.anomalia_superficie,
                utenza_anomalia_cf_invalido: u.anomalia_cf_invalido,
                utenza_anomalia_cf_mancante: u.anomalia_cf_mancante,
                utenza_anomalia_comune_invalido: u.anomalia_comune_invalido,
                utenza_anomalia_particella_assente: u.anomalia_particella_assente,
                utenza_anomalia_imponibile: u.anomalia_imponibile,
                utenza_anomalia_importi: u.anomalia_importi,
                utenza_created_at: u.created_at,
              });
            }
          }
        }

        const urlByCco = ccos.length ? await resolveCapacitasRptCertificatoUrls(token, ccos) : new Map<string, string>();
        const filteredUtenzeKeys = normalizeSelectedFields(exportFieldsUtenze, EXPORT_FIELD_DEFS_UTENZE.map((f) => f.key));
        const filteredPartKeys = normalizeSelectedFields(exportFieldsParticelle, EXPORT_FIELD_DEFS_PARTICELLE_INTESTATARI.map((f) => f.key));
        const selectedKeys = Array.from(new Set([...filteredPartKeys, ...filteredUtenzeKeys]));

        const exportRows = flat.map((row) => {
          const cco = String(row["utenza_cco"] ?? "").trim();
          if (cco) row["capacitas_rpt_certificato_url"] = urlByCco.get(cco) ?? "";
          return selectedKeys.length ? pickFields(row, selectedKeys) : row;
        });

        const sheet = XLSX.utils.json_to_sheet(exportRows);
        const csv = XLSX.utils.sheet_to_csv(sheet);
        triggerDownload(new Blob([csv], { type: "text/csv;charset=utf-8" }), "catasto-elaborazione-massiva-utenze.csv");
        return;
    }

    // CF/PIVA -> Particelle (una riga per particella trovata)
    const flat = resultsArg.flatMap((r) => {
        const matches = r.matches ?? (r.match ? [r.match] : []);
        if (matches.length === 0) {
          return [
            {
              row_index: r.row_index,
              kind,
              codice_fiscale_input: r.codice_fiscale_input ?? "",
              partita_iva_input: r.partita_iva_input ?? "",
              esito: r.esito,
              message: r.message,
              matches_count: r.matches_count ?? "",
            },
          ];
        }
        return matches.map((m) => ({
          row_index: r.row_index,
          kind,
          codice_fiscale_input: r.codice_fiscale_input ?? "",
          partita_iva_input: r.partita_iva_input ?? "",
          esito: r.esito,
          message: r.message,
          matches_count: r.matches_count ?? "",
          particella_id: m.particella_id,
          comune: m.comune ?? "",
          cod_comune_capacitas: m.cod_comune_capacitas ?? "",
          codice_catastale: m.codice_catastale ?? "",
          foglio: m.foglio ?? "",
          particella: m.particella ?? "",
          subalterno: m.subalterno ?? "",
          num_distretto: m.num_distretto ?? "",
          nome_distretto: m.nome_distretto ?? "",
          superficie_mq: m.superficie_mq ?? "",
          superficie_grafica_mq: m.superficie_grafica_mq ?? "",
          utenza_latest_cco: m.utenza_latest?.cco ?? "",
          capacitas_rpt_certificato_url: "",
          dettaglio_particella_url: m.particella_id ? `/catasto/particelle/${m.particella_id}` : "",
        }));
      });

      const ccos = flat.map((r) => String((r as Record<string, unknown>)["utenza_latest_cco"] ?? "")).filter(Boolean);
      const urlByCco = ccos.length ? await resolveCapacitasRptCertificatoUrls(token, ccos) : new Map<string, string>();
      const filteredKeys = normalizeSelectedFields(exportFieldsParticelle, EXPORT_FIELD_DEFS_CF_PARTICELLE.map((f) => f.key));
      const exportRows = flat.map((row) => {
        const cco = String((row as Record<string, unknown>)["utenza_latest_cco"] ?? "").trim();
        if (cco) (row as Record<string, unknown>)["capacitas_rpt_certificato_url"] = urlByCco.get(cco) ?? "";
        return filteredKeys.length ? pickFields(row, filteredKeys) : row;
      });

      const sheet = XLSX.utils.json_to_sheet(exportRows);
      const csv = XLSX.utils.sheet_to_csv(sheet);
      triggerDownload(new Blob([csv], { type: "text/csv;charset=utf-8" }), "catasto-elaborazione-massiva-particelle.csv");
  }

  async function exportVeloce(format: "csv" | "xlsx"): Promise<void> {
    if (results.length === 0 || !inferredKind) return;
    const token = getStoredAccessToken();
    if (!token) return;
    setBusy(true);
    try {
      // Fetch all utenze per particella so we get one row per utenza (not per unique intestatario)
      const particellaIds = Array.from(
        new Set(
          results
            .flatMap((r) => r.matches ?? (r.match ? [r.match] : []))
            .map((m) => m.particella_id)
            .filter((id): id is string => Boolean(id)),
        ),
      );
      const utenzeByParticella = new Map<string, CatUtenzaIrrigua[]>();
      await Promise.all(
        particellaIds.map(async (id) => {
          try {
            const utenze = await catastoGetParticellaUtenze(token, id);
            utenzeByParticella.set(id, utenze ?? []);
          } catch {
            utenzeByParticella.set(id, []);
          }
        }),
      );

      const rows: Record<string, unknown>[] = [];
      for (const r of results) {
        const matches = r.matches ?? (r.match ? [r.match] : []);
        const buildBase = (m?: (typeof matches)[0]) =>
          inferredKind === "CF_PIVA_PARTICELLE"
            ? { cf_input: r.codice_fiscale_input ?? "", piva_input: r.partita_iva_input ?? "", comune: m?.comune ?? "", foglio: m?.foglio ?? "", particella: m?.particella ?? "", sub: m?.subalterno ?? "", esito: r.esito }
            : { comune: m?.comune ?? r.comune_input ?? "", sezione: r.sezione_input ?? "", foglio: m?.foglio ?? r.foglio_input ?? "", particella: m?.particella ?? r.particella_input ?? "", sub: m?.subalterno ?? r.sub_input ?? "", esito: r.esito };

        const emptyInt = { n_utenze: 0, rank: "", cf: "", tipo: "", cognome: "", nome: "", denominazione: "", ragione_sociale: "", data_nascita: "", luogo_nascita: "", deceduto: "" };

        if (matches.length === 0) {
          rows.push({ ...buildBase(), ...emptyInt });
          continue;
        }
        for (const m of matches) {
          const utenze = utenzeByParticella.get(m.particella_id) ?? [];
          const n = utenze.length;
          const base = buildBase(m);
          // Build CF→person lookup from intestatari (enrichment only — may not cover all utenze)
          const intByCf = new Map(
            (m.intestatari ?? []).map((p) => [p.codice_fiscale?.trim().toUpperCase() ?? "", p]),
          );
          if (n === 0) {
            rows.push({ ...base, ...emptyInt });
            continue;
          }
          for (let i = 0; i < n; i++) {
            const u = utenze[i];
            const person = intByCf.get(u.codice_fiscale?.trim().toUpperCase() ?? "");
            rows.push({
              ...base,
              n_utenze: n,
              rank: `${i + 1}/${n}`,
              cf: u.codice_fiscale ?? "",
              tipo: person?.tipo ?? "",
              cognome: person?.cognome ?? "",
              nome: person?.nome ?? "",
              denominazione: person?.denominazione ?? u.denominazione ?? "",
              ragione_sociale: person?.ragione_sociale ?? "",
              data_nascita: person?.data_nascita ?? "",
              luogo_nascita: person?.luogo_nascita ?? "",
              deceduto: String(person?.deceduto ?? ""),
            });
          }
        }
      }

      const basename = inferredKind === "CF_PIVA_PARTICELLE" ? "catasto-intestatari-da-cf" : "catasto-intestatari";
      if (format === "csv") {
        const csv = XLSX.utils.sheet_to_csv(XLSX.utils.json_to_sheet(rows));
        triggerDownload(new Blob([csv], { type: "text/csv;charset=utf-8" }), `${basename}.csv`);
      } else {
        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(rows), "intestatari");
        const out = XLSX.write(wb, { type: "array", bookType: "xlsx" });
        triggerDownload(new Blob([out], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }), `${basename}.xlsx`);
      }
    } finally {
      setBusy(false);
    }
  }

  async function exportCsv(): Promise<void> {
    if (results.length === 0 || !inferredKind) return;
    const token = getStoredAccessToken();
    if (!token) return;
    setBusy(true);
    try {
      await exportCsvFrom(token, inferredKind, results);
    } finally {
      setBusy(false);
    }
  }

  async function exportXlsxFrom(
    token: string,
    kind: "CF_PIVA_PARTICELLE" | "COMUNE_FOGLIO_PARTICELLA_INTESTATARI",
    resultsArg: CatAnagraficaBulkRowResult[],
  ): Promise<void> {
    if (resultsArg.length === 0) return;
      const wb = XLSX.utils.book_new();

      if (kind === "COMUNE_FOGLIO_PARTICELLA_INTESTATARI") {
        const particellaIds = Array.from(
          new Set(
            resultsArg
              .flatMap((r) => r.matches ?? (r.match ? [r.match] : []))
              .map((m) => m.particella_id)
              .filter((id): id is string => Boolean(id)),
          ),
        );
        const utenzeRows: Record<string, unknown>[] = [];
        const ccos: string[] = [];

        const utenzeByParticella = new Map<string, CatUtenzaIrrigua[]>();
        await Promise.all(
          particellaIds.map(async (id) => {
            try {
              const utenze = await catastoGetParticellaUtenze(token, id);
              utenzeByParticella.set(id, utenze ?? []);
            } catch {
              utenzeByParticella.set(id, []);
            }
          }),
        );

        const particelleSheetRows = resultsArg.flatMap((r) => {
          const matches = r.matches ?? (r.match ? [r.match] : []);
          if (matches.length === 0) {
            return [
              {
                row_index: r.row_index,
                kind,
                comune_input: r.comune_input ?? "",
                sezione_input: r.sezione_input ?? "",
                foglio_input: r.foglio_input ?? "",
                particella_input: r.particella_input ?? "",
                sub_input: r.sub_input ?? "",
                esito: r.esito,
                message: r.message,
                matches_count: r.matches_count ?? "",
              },
            ];
          }

          return matches.map((m, index) => {
            const intest = (m.intestatari ?? [])
              .map((i) => (i.denominazione ?? i.ragione_sociale ?? [i.cognome, i.nome].filter(Boolean).join(" ")) || "")
              .filter(Boolean)
              .join(" | ");

            const utenze = utenzeByParticella.get(m.particella_id) ?? [];
            const firstInt = m.intestatari?.[0];
            const intestCf = (m.intestatari ?? []).map((i) => i.codice_fiscale).filter(Boolean).join(" | ");
            for (const u of utenze) {
              if (u.cco) ccos.push(u.cco);
              utenzeRows.push({
                row_index: r.row_index,
                input_particella_id: m.particella_id,
                comune_input: r.comune_input ?? "",
                sezione_input: r.sezione_input ?? "",
                foglio_input: r.foglio_input ?? "",
                particella_input: r.particella_input ?? "",
                sub_input: r.sub_input ?? "",
                esito: r.esito,
                message: r.message,
                matches_count: r.matches_count ?? matches.length,
                match_rank: index + 1,
                dettaglio_particella_url: `/catasto/particelle/${m.particella_id}`,
                capacitas_rpt_certificato_url: "",
                intestatari_flatten: intest,
                intestatario_cf: firstInt?.codice_fiscale ?? "",
                intestatario_tipo: firstInt?.tipo ?? "",
                intestatario_cognome: firstInt?.cognome ?? "",
                intestatario_nome: firstInt?.nome ?? "",
                intestatario_denominazione: firstInt?.denominazione ?? "",
                intestatario_ragione_sociale: firstInt?.ragione_sociale ?? "",
                intestatario_data_nascita: firstInt?.data_nascita ?? "",
                intestatario_luogo_nascita: firstInt?.luogo_nascita ?? "",
                intestatario_deceduto: String(firstInt?.deceduto ?? ""),
                utenza_id: u.id,
                utenza_import_batch_id: u.import_batch_id,
                utenza_anno_campagna: u.anno_campagna,
                utenza_cco: u.cco ?? "",
                utenza_comune_id: u.comune_id ?? "",
                utenza_cod_provincia: u.cod_provincia ?? "",
                utenza_cod_comune_capacitas: u.cod_comune_capacitas ?? "",
                utenza_cod_frazione: u.cod_frazione ?? "",
                utenza_num_distretto: u.num_distretto ?? "",
                utenza_nome_distretto_loc: u.nome_distretto_loc ?? "",
                utenza_nome_comune: u.nome_comune ?? "",
                utenza_sezione_catastale: u.sezione_catastale ?? "",
                utenza_foglio: u.foglio ?? "",
                utenza_particella: u.particella ?? "",
                utenza_subalterno: u.subalterno ?? "",
                utenza_particella_id: u.particella_id ?? "",
                utenza_sup_catastale_mq: u.sup_catastale_mq ?? "",
                utenza_sup_irrigabile_mq: u.sup_irrigabile_mq ?? "",
                utenza_ind_spese_fisse: u.ind_spese_fisse ?? "",
                utenza_imponibile_sf: u.imponibile_sf ?? "",
                utenza_esente_0648: u.esente_0648,
                utenza_aliquota_0648: u.aliquota_0648 ?? "",
                utenza_importo_0648: u.importo_0648 ?? "",
                utenza_aliquota_0985: u.aliquota_0985 ?? "",
                utenza_importo_0985: u.importo_0985 ?? "",
                utenza_denominazione: u.denominazione ?? "",
                utenza_codice_fiscale: u.codice_fiscale ?? "",
                utenza_codice_fiscale_raw: u.codice_fiscale_raw ?? "",
                utenza_anomalia_superficie: u.anomalia_superficie,
                utenza_anomalia_cf_invalido: u.anomalia_cf_invalido,
                utenza_anomalia_cf_mancante: u.anomalia_cf_mancante,
                utenza_anomalia_comune_invalido: u.anomalia_comune_invalido,
                utenza_anomalia_particella_assente: u.anomalia_particella_assente,
                utenza_anomalia_imponibile: u.anomalia_imponibile,
                utenza_anomalia_importi: u.anomalia_importi,
                utenza_created_at: u.created_at,
              });
            }

            return {
              row_index: r.row_index,
              kind,
              comune_input: r.comune_input ?? "",
              sezione_input: r.sezione_input ?? "",
              foglio_input: r.foglio_input ?? "",
              particella_input: r.particella_input ?? "",
              sub_input: r.sub_input ?? "",
              esito: r.esito,
              message: r.message,
              matches_count: r.matches_count ?? matches.length,
              match_rank: index + 1,
              particella_id: m.particella_id,
              intestatari: intest,
              intestatari_cf_flatten: intestCf,
              utenze_count: utenze.length,
              particella_comune: m.comune ?? "",
              particella_cod_comune_capacitas: m.cod_comune_capacitas ?? "",
              particella_foglio: m.foglio ?? "",
              particella_particella: m.particella ?? "",
              particella_subalterno: m.subalterno ?? "",
              particella_num_distretto: m.num_distretto ?? "",
              particella_nome_distretto: m.nome_distretto ?? "",
              dettaglio_particella_url: `/catasto/particelle/${m.particella_id}`,
              utenza_cco: "",
              capacitas_rpt_certificato_url: "",
            };
          });
        });

        const urlByCco = ccos.length ? await resolveCapacitasRptCertificatoUrls(token, ccos) : new Map<string, string>();

        const filteredPartKeys = normalizeSelectedFields(exportFieldsParticelle, EXPORT_FIELD_DEFS_PARTICELLE_INTESTATARI.map((f) => f.key));
        const particelleOut = particelleSheetRows.map((row) => (filteredPartKeys.length ? pickFields(row, filteredPartKeys) : row));

        const filteredUtenzeKeys = normalizeSelectedFields(exportFieldsUtenze, EXPORT_FIELD_DEFS_UTENZE.map((f) => f.key));
        const utenzeOut = utenzeRows.map((row) => {
          const cco = String((row as Record<string, unknown>)["utenza_cco"] ?? "").trim();
          if (cco) (row as Record<string, unknown>)["capacitas_rpt_certificato_url"] = urlByCco.get(cco) ?? "";
          // keep only selected utenza fields + common row context if present
          const baseContextKeys = ["row_index", "input_particella_id", "comune_input", "sezione_input", "foglio_input", "particella_input", "sub_input", "esito", "message", "matches_count", "match_rank", "dettaglio_particella_url"];
          const keys = Array.from(new Set([...baseContextKeys, ...filteredUtenzeKeys]));
          return keys.length ? pickFields(row as Record<string, unknown>, keys) : row;
        });

        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(particelleOut), "particelle");
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(utenzeOut), "utenze");
      } else {
        const particelleRows = resultsArg.flatMap((r) => {
          const matches = r.matches ?? (r.match ? [r.match] : []);
          if (matches.length === 0) {
            return [
              {
                row_index: r.row_index,
                kind,
                codice_fiscale_input: r.codice_fiscale_input ?? "",
                partita_iva_input: r.partita_iva_input ?? "",
                esito: r.esito,
                message: r.message,
                matches_count: r.matches_count ?? "",
              },
            ];
          }
          return matches.map((m) => ({
            row_index: r.row_index,
            kind,
            codice_fiscale_input: r.codice_fiscale_input ?? "",
            partita_iva_input: r.partita_iva_input ?? "",
            esito: r.esito,
            message: r.message,
            matches_count: r.matches_count ?? "",
            ...m,
            utenza_latest_cco: m.utenza_latest?.cco ?? "",
            capacitas_rpt_certificato_url: "",
            dettaglio_particella_url: m.particella_id ? `/catasto/particelle/${m.particella_id}` : "",
          }));
        });

        const ccos = particelleRows.map((r) => String((r as Record<string, unknown>)["utenza_latest_cco"] ?? "")).filter(Boolean);
        const urlByCco = ccos.length ? await resolveCapacitasRptCertificatoUrls(token, ccos) : new Map<string, string>();
        const filteredKeys = normalizeSelectedFields(exportFieldsParticelle, EXPORT_FIELD_DEFS_CF_PARTICELLE.map((f) => f.key));
        const outRows = particelleRows.map((row) => {
          const cco = String((row as Record<string, unknown>)["utenza_latest_cco"] ?? "").trim();
          if (cco) (row as Record<string, unknown>)["capacitas_rpt_certificato_url"] = urlByCco.get(cco) ?? "";
          return filteredKeys.length ? pickFields(row as Record<string, unknown>, filteredKeys) : row;
        });

        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(outRows), "particelle");
      }

      const sheetSummary = XLSX.utils.json_to_sheet([
        { key: "tipo_rilevato", value: inferredKind },
        { key: "totale_righe", value: summary.total },
        { key: "trovate", value: summary.found },
        { key: "non_trovate", value: summary.notFound },
        { key: "multiple", value: summary.multiple },
        { key: "righe_invalide", value: summary.invalid },
        { key: "errori", value: summary.error },
        { key: "righe_saltate_vuote", value: skippedRows },
      ]);
      XLSX.utils.book_append_sheet(wb, sheetSummary, "summary");

      const out = XLSX.write(wb, { type: "array", bookType: "xlsx" });
      triggerDownload(
        new Blob([out], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }),
        kind === "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"
          ? "catasto-elaborazione-massiva-particelle-utenze.xlsx"
          : "catasto-elaborazione-massiva-particelle.xlsx",
      );
  }

  async function exportXlsx(): Promise<void> {
    if (results.length === 0 || !inferredKind) return;
    const token = getStoredAccessToken();
    if (!token) return;
    setBusy(true);
    try {
      await exportXlsxFrom(token, inferredKind, results);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-stack">
      {error ? (
        <AlertBanner variant="danger" title="Errore">
          {error}
        </AlertBanner>
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
                  const sheet = XLSX.utils.json_to_sheet([{ comune: "165", sezione: "", foglio: "5", particella: "120", sub: "" }]);
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
                  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet([{ comune: "165", sezione: "", foglio: "5", particella: "120", sub: "" }]), "template");
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

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <input
            type="file"
            accept=".xlsx,.csv"
            aria-label="File ricerca anagrafica"
            disabled={busy}
            onChange={(e) => {
              const file = e.target.files?.[0] ?? null;
              if (!file) return;
              setSourceFile(file);
              void parseSelectedFile(file);
            }}
          />
          <p className="text-sm text-gray-500">
            {sourceFile ? (
              <>
                <span className="font-medium text-gray-800">{sourceFile.name}</span> · {parsedRows.length} righe pronte
                {skippedRows ? <span className="text-gray-400"> · {skippedRows} vuote saltate</span> : null}
                {inferredKind ? (
                  <span className="text-gray-400">
                    {" "}
                    · tipo rilevato: {inferredKind === "CF_PIVA_PARTICELLE" ? "CF/P.IVA → Particelle" : "Particelle → Intestatari"}
                  </span>
                ) : null}
              </>
            ) : (
              "Nessun file selezionato"
            )}
          </p>
        </div>

        {inferredKind ? (
          <div className="mt-4 rounded-xl border border-gray-100 bg-gray-50 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm font-medium text-gray-900">Esportazione</p>
              <div className="flex rounded-lg bg-gray-200/60 p-0.5 text-sm">
                {(["veloce", "avanzato"] as const).map((mode) => (
                  <button
                    key={mode}
                    type="button"
                    onClick={() => setExportMode(mode)}
                    className={`rounded-md px-3 py-1.5 font-medium capitalize transition ${
                      exportMode === mode ? "bg-white shadow-sm text-gray-900" : "text-gray-500 hover:text-gray-700"
                    }`}
                  >
                    {mode}
                  </button>
                ))}
              </div>
            </div>

            {exportMode === "veloce" ? (
              <div className="mt-4 space-y-3">
                <p className="text-sm text-gray-500">
                  Una riga per utenza.{" "}
                  {inferredKind === "CF_PIVA_PARTICELLE"
                    ? "Colonne: CF input · P.IVA input · Comune · Foglio · Particella · Sub"
                    : "Colonne: Comune · Sezione · Foglio · Particella · Sub"}{" "}
                  · Esito · N utenze · Rank (1/n) · CF · Tipo · Cognome · Nome · Denominazione · Ragione Sociale · Data Nascita · Luogo Nascita · Deceduto
                </p>
                <div className="flex flex-wrap gap-2">
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
            ) : (
              <>
                <div className="mt-4 flex flex-wrap items-start justify-between gap-3">
                  <p className="text-sm text-gray-600">Seleziona le colonne incluse nell’export CSV/Excel.</p>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="btn-secondary"
                      disabled={busy}
                      onClick={() => {
                        if (inferredKind === "CF_PIVA_PARTICELLE") {
                          setExportFieldsParticelle(EXPORT_FIELD_DEFS_CF_PARTICELLE.map((f) => f.key));
                          setExportFieldsUtenze([]);
                          return;
                        }
                        setExportFieldsParticelle(EXPORT_FIELD_DEFS_PARTICELLE_INTESTATARI.map((f) => f.key));
                        setExportFieldsUtenze(EXPORT_FIELD_DEFS_UTENZE.map((f) => f.key));
                      }}
                    >
                      Seleziona tutto
                    </button>
                    <button
                      type="button"
                      className="btn-secondary"
                      disabled={busy}
                      onClick={() => {
                        setExportFieldsParticelle([]);
                        setExportFieldsUtenze([]);
                      }}
                    >
                      Nessuno
                    </button>
                  </div>
                </div>

                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <div className="rounded-xl border border-gray-100 bg-white p-3">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-xs font-semibold uppercase tracking-widest text-gray-400">Particelle</p>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          className="btn-secondary"
                          disabled={busy}
                          onClick={() => {
                            const all =
                              inferredKind === "CF_PIVA_PARTICELLE"
                                ? EXPORT_FIELD_DEFS_CF_PARTICELLE.map((f) => f.key)
                                : EXPORT_FIELD_DEFS_PARTICELLE_INTESTATARI.map((f) => f.key);
                            setExportFieldsParticelle(all);
                          }}
                        >
                          Tutti
                        </button>
                        <button type="button" className="btn-secondary" disabled={busy} onClick={() => setExportFieldsParticelle([])}>
                          Nessuno
                        </button>
                      </div>
                    </div>

                    <div className="mt-3 grid gap-2 sm:grid-cols-2">
                      {(inferredKind === "CF_PIVA_PARTICELLE" ? EXPORT_FIELD_DEFS_CF_PARTICELLE : EXPORT_FIELD_DEFS_PARTICELLE_INTESTATARI).map((f) => (
                        <label key={f.key} className="flex items-center gap-2 text-sm text-gray-700">
                          <input
                            type="checkbox"
                            checked={exportFieldsParticelle.includes(f.key)}
                            disabled={busy}
                            onChange={(e) => {
                              const checked = e.target.checked;
                              setExportFieldsParticelle((prev) => {
                                if (checked) return prev.includes(f.key) ? prev : [...prev, f.key];
                                return prev.filter((k) => k !== f.key);
                              });
                            }}
                          />
                          <span className="truncate" title={f.key}>{f.label}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {inferredKind === "COMUNE_FOGLIO_PARTICELLA_INTESTATARI" ? (
                    <div className="rounded-xl border border-gray-100 bg-white p-3">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-xs font-semibold uppercase tracking-widest text-gray-400">Utenze</p>
                        <div className="flex gap-2">
                          <button type="button" className="btn-secondary" disabled={busy} onClick={() => setExportFieldsUtenze(EXPORT_FIELD_DEFS_UTENZE.map((f) => f.key))}>Tutti</button>
                          <button type="button" className="btn-secondary" disabled={busy} onClick={() => setExportFieldsUtenze([])}>Nessuno</button>
                        </div>
                      </div>

                      <div className="mt-3 grid gap-2 sm:grid-cols-2">
                        {EXPORT_FIELD_DEFS_UTENZE.map((f) => (
                          <label key={f.key} className="flex items-center gap-2 text-sm text-gray-700">
                            <input
                              type="checkbox"
                              checked={exportFieldsUtenze.includes(f.key)}
                              disabled={busy}
                              onChange={(e) => {
                                const checked = e.target.checked;
                                setExportFieldsUtenze((prev) => {
                                  if (checked) return prev.includes(f.key) ? prev : [...prev, f.key];
                                  return prev.filter((k) => k !== f.key);
                                });
                              }}
                            />
                            <span className="truncate" title={f.key}>{f.label}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  <button className="btn-secondary" type="button" disabled={busy || results.length === 0} onClick={() => void exportCsv()}>
                    <DocumentIcon className="h-4 w-4" />
                    Export CSV
                  </button>
                  <button className="btn-secondary" type="button" disabled={busy || results.length === 0} onClick={() => void exportXlsx()}>
                    <DocumentIcon className="h-4 w-4" />
                    Export Excel
                  </button>
                </div>
              </>
            )}
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
              onClick={() => {
                setOperationHistory([]);
              }}
            >
              Svuota storico
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
                          await exportCsvFrom(token, job.kind, job.results);
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
                          await exportXlsxFrom(token, job.kind, job.results);
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
