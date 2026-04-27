"use client";

import * as XLSX from "xlsx";
import { useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { DataTable } from "@/components/table/data-table";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertBanner } from "@/components/ui/alert-banner";
import { DocumentIcon, RefreshIcon } from "@/components/ui/icons";
import { catastoBulkSearchAnagrafica, catastoGetParticellaUtenze } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatAnagraficaBulkRowInput, CatAnagraficaBulkRowResult, CatUtenzaIrrigua } from "@/types/catasto";

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

type BulkSummary = {
  total: number;
  found: number;
  notFound: number;
  multiple: number;
  invalid: number;
  error: number;
};

type BulkOperationHistoryItem = BulkSummary & {
  id: string;
  executedAt: string;
  fileName: string | null;
  kind: "CF_PIVA_PARTICELLE" | "COMUNE_FOGLIO_PARTICELLA_INTESTATARI" | null;
  skippedRows: number;
};

const HISTORY_STORAGE_KEY = "gaia.catasto.elaborazioniMassive.history.v1";
const HISTORY_LIMIT = 5;

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

function loadHistory(): BulkOperationHistoryItem[] {
  try {
    const raw = window.localStorage.getItem(HISTORY_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.slice(0, HISTORY_LIMIT).filter((item): item is BulkOperationHistoryItem => {
      return item && typeof item === "object" && typeof item.id === "string" && typeof item.executedAt === "string";
    });
  } catch {
    return [];
  }
}

function saveHistory(items: BulkOperationHistoryItem[]): void {
  window.localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(items.slice(0, HISTORY_LIMIT)));
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

  const summary = useMemo(() => buildSummary(results), [results]);

  useEffect(() => {
    setOperationHistory(loadHistory());
  }, []);

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
      const response = await catastoBulkSearchAnagrafica(token, { kind: inferredKind ?? undefined, rows: parsedRows });
      const nextSummary = buildSummary(response.results);
      const historyItem: BulkOperationHistoryItem = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        executedAt: new Date().toISOString(),
        fileName: sourceFile?.name ?? null,
        kind: inferredKind,
        skippedRows,
        ...nextSummary,
      };
      const nextHistory = [historyItem, ...operationHistory].slice(0, HISTORY_LIMIT);
      setResults(response.results);
      setOperationHistory(nextHistory);
      saveHistory(nextHistory);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore elaborazione massiva");
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
      if (inferredKind === "COMUNE_FOGLIO_PARTICELLA_INTESTATARI") {
        const particellaIds = Array.from(
          new Set(results.map((r) => r.particella_id).filter((id): id is string => Boolean(id))),
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
        for (const r of results) {
          const m = r.match;
          const intest = (m?.intestatari ?? [])
            .map((i) => (i.denominazione ?? i.ragione_sociale ?? [i.cognome, i.nome].filter(Boolean).join(" ")) || "")
            .filter(Boolean)
            .join(" | ");

          const utenze = r.particella_id ? (utenzeByParticella.get(r.particella_id) ?? []) : [];
          if (utenze.length === 0) {
            flat.push({
              row_index: r.row_index,
              kind: inferredKind,
              comune_input: r.comune_input ?? "",
              sezione_input: r.sezione_input ?? "",
              foglio_input: r.foglio_input ?? "",
              particella_input: r.particella_input ?? "",
              sub_input: r.sub_input ?? "",
              esito: r.esito,
              message: r.message,
              particella_id: r.particella_id ?? "",
              intestatari: intest,
              particella_comune: m?.comune ?? "",
              particella_cod_comune_capacitas: m?.cod_comune_capacitas ?? "",
              particella_foglio: m?.foglio ?? "",
              particella_particella: m?.particella ?? "",
              particella_subalterno: m?.subalterno ?? "",
              particella_num_distretto: m?.num_distretto ?? "",
              particella_nome_distretto: m?.nome_distretto ?? "",
              particella_superficie_mq: m?.superficie_mq ?? "",
              particella_superficie_grafica_mq: m?.superficie_grafica_mq ?? "",
              dettaglio_particella_url: r.particella_id ? `/catasto/particelle/${r.particella_id}` : "",
            });
            continue;
          }

          for (const u of utenze) {
            flat.push({
              row_index: r.row_index,
              kind: inferredKind,
              comune_input: r.comune_input ?? "",
              sezione_input: r.sezione_input ?? "",
              foglio_input: r.foglio_input ?? "",
              particella_input: r.particella_input ?? "",
              sub_input: r.sub_input ?? "",
              esito: r.esito,
              message: r.message,
              particella_id: r.particella_id ?? "",
              intestatari: intest,
              dettaglio_particella_url: r.particella_id ? `/catasto/particelle/${r.particella_id}` : "",
              // flatten utenza (tutti i campi disponibili dal tipo)
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
        }

        const sheet = XLSX.utils.json_to_sheet(flat);
        const csv = XLSX.utils.sheet_to_csv(sheet);
        triggerDownload(new Blob([csv], { type: "text/csv;charset=utf-8" }), "catasto-elaborazione-massiva-utenze.csv");
        return;
      }

      // CF/PIVA -> Particelle (una riga per particella trovata)
      const flat = results.flatMap((r) => {
        const matches = r.matches ?? (r.match ? [r.match] : []);
        if (matches.length === 0) {
          return [
            {
              row_index: r.row_index,
              kind: inferredKind,
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
          kind: inferredKind,
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
          dettaglio_particella_url: m.particella_id ? `/catasto/particelle/${m.particella_id}` : "",
        }));
      });

      const sheet = XLSX.utils.json_to_sheet(flat);
      const csv = XLSX.utils.sheet_to_csv(sheet);
      triggerDownload(new Blob([csv], { type: "text/csv;charset=utf-8" }), "catasto-elaborazione-massiva-particelle.csv");
    } finally {
      setBusy(false);
    }
  }

  async function exportXlsx(): Promise<void> {
    if (results.length === 0 || !inferredKind) return;
    const token = getStoredAccessToken();
    if (!token) return;

    setBusy(true);
    try {
      const wb = XLSX.utils.book_new();

      if (inferredKind === "COMUNE_FOGLIO_PARTICELLA_INTESTATARI") {
        const particellaIds = Array.from(
          new Set(results.map((r) => r.particella_id).filter((id): id is string => Boolean(id))),
        );
        const utenzeRows: Record<string, unknown>[] = [];

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

        const particelleSheetRows = results.map((r) => {
          const m = r.match;
          const intest = (m?.intestatari ?? [])
            .map((i) => (i.denominazione ?? i.ragione_sociale ?? [i.cognome, i.nome].filter(Boolean).join(" ")) || "")
            .filter(Boolean)
            .join(" | ");

          const utenze = r.particella_id ? (utenzeByParticella.get(r.particella_id) ?? []) : [];
          for (const u of utenze) {
            utenzeRows.push({
              row_index: r.row_index,
              input_particella_id: r.particella_id ?? "",
              comune_input: r.comune_input ?? "",
              sezione_input: r.sezione_input ?? "",
              foglio_input: r.foglio_input ?? "",
              particella_input: r.particella_input ?? "",
              sub_input: r.sub_input ?? "",
              esito: r.esito,
              message: r.message,
              // utenza full
              ...u,
            });
          }

          return {
            row_index: r.row_index,
            kind: inferredKind,
            comune_input: r.comune_input ?? "",
            sezione_input: r.sezione_input ?? "",
            foglio_input: r.foglio_input ?? "",
            particella_input: r.particella_input ?? "",
            sub_input: r.sub_input ?? "",
            esito: r.esito,
            message: r.message,
            particella_id: r.particella_id ?? "",
            intestatari: intest,
            utenze_count: utenze.length,
            dettaglio_particella_url: r.particella_id ? `/catasto/particelle/${r.particella_id}` : "",
          };
        });

        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(particelleSheetRows), "particelle");
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(utenzeRows), "utenze");
      } else {
        const particelleRows = results.flatMap((r) => {
          const matches = r.matches ?? (r.match ? [r.match] : []);
          if (matches.length === 0) {
            return [
              {
                row_index: r.row_index,
                kind: inferredKind,
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
            kind: inferredKind,
            codice_fiscale_input: r.codice_fiscale_input ?? "",
            partita_iva_input: r.partita_iva_input ?? "",
            esito: r.esito,
            message: r.message,
            matches_count: r.matches_count ?? "",
            ...m,
            dettaglio_particella_url: m.particella_id ? `/catasto/particelle/${m.particella_id}` : "",
          }));
        });

        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(particelleRows), "particelle");
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
        inferredKind === "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"
          ? "catasto-elaborazione-massiva-particelle-utenze.xlsx"
          : "catasto-elaborazione-massiva-particelle.xlsx",
      );
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

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button className="btn-primary" type="button" disabled={busy || parsedRows.length === 0} onClick={() => void runBulkSearch()}>
            <RefreshIcon className="h-4 w-4" />
            {busy ? "Elaborazione…" : "Elabora righe"}
          </button>
          <button className="btn-secondary" type="button" disabled={busy || results.length === 0} onClick={() => void exportCsv()}>
            <DocumentIcon className="h-4 w-4" />
            Export CSV
          </button>
          <button className="btn-secondary" type="button" disabled={busy || results.length === 0} onClick={() => void exportXlsx()}>
            <DocumentIcon className="h-4 w-4" />
            Export Excel
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
                saveHistory([]);
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
                    <p className="text-sm font-medium text-gray-900">{item.fileName ?? "Elaborazione senza file"}</p>
                    <p className="mt-1 text-xs text-gray-500">
                      {new Intl.DateTimeFormat("it-IT", {
                        dateStyle: "short",
                        timeStyle: "short",
                      }).format(new Date(item.executedAt))}{" "}
                      · {formatOperationKind(item.kind)}
                      {item.skippedRows ? ` · ${item.skippedRows} righe vuote saltate` : ""}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2 text-xs text-gray-700">
                    <span className="rounded-full bg-white px-2.5 py-1">Totale: {item.total}</span>
                    <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-emerald-700">FOUND: {item.found}</span>
                    <span className="rounded-full bg-white px-2.5 py-1">NOT_FOUND: {item.notFound}</span>
                    <span className="rounded-full bg-amber-50 px-2.5 py-1 text-amber-700">MULTIPLE: {item.multiple}</span>
                    <span className="rounded-full bg-red-50 px-2.5 py-1 text-red-700">ERROR: {item.error}</span>
                  </div>
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
