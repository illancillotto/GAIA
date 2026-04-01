"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useDeferredValue, useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { UtenzeModulePage } from "@/components/utenze/utenze-module-page";
import { DataTable } from "@/components/table/data-table";
import { TableFilters } from "@/components/table/table-filters";
import { createUtenzeSubject, downloadUtenzeDocumentBlob, downloadUtenzeExportBlob, getUtenzeSubject, getUtenzeSubjects, importUtenzeSubjectsCsv } from "@/lib/api";
import { formatDateTime } from "@/lib/presentation";
import type { UtenzeCsvImportResult, UtenzeDocument, UtenzeSubjectCreateInput, UtenzeSubjectDetail, UtenzeSubjectListItem } from "@/types/api";

type FilterState = {
  search: string;
  subjectType: string;
  status: string;
  letter: string;
  requiresReview: string;
};

const emptyFilters: FilterState = {
  search: "",
  subjectType: "",
  status: "",
  letter: "",
  requiresReview: "",
};

type DocumentPreviewKind = "pdf" | "image" | "docx" | "spreadsheet" | "text" | "download";

type SpreadsheetPreviewSheet = {
  name: string;
  rows: string[][];
};

const IMAGE_EXTENSIONS = new Set([".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"]);
const SPREADSHEET_EXTENSIONS = new Set([".xls", ".xlsx"]);
const TEXT_EXTENSIONS = new Set([".txt", ".csv", ".log", ".md", ".json", ".xml"]);

function isPreviewableImage(extension: string | null): boolean {
  return extension != null && IMAGE_EXTENSIONS.has(extension.toLowerCase());
}

function isPreviewableSpreadsheet(extension: string | null): boolean {
  return extension != null && SPREADSHEET_EXTENSIONS.has(extension.toLowerCase());
}

function isPreviewableText(extension: string | null): boolean {
  return extension != null && TEXT_EXTENSIONS.has(extension.toLowerCase());
}

function normalizeIdentifierPart(value: string): string {
  return value
    .trim()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^A-Za-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .replace(/_+/g, "_");
}

function deriveArchiveLetter(value: string): string {
  const normalized = value
    .trim()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toUpperCase();
  const firstLetter = normalized.match(/[A-Z]/);
  return firstLetter?.[0] ?? "";
}

function buildSourceNameRaw(createType: "person" | "company", values: {
  personSurname: string;
  personName: string;
  personCf: string;
  companyName: string;
  companyVat: string;
}): string {
  const parts = createType === "person"
    ? [values.personSurname, values.personName, values.personCf]
    : [values.companyName, values.companyVat];

  return parts.map(normalizeIdentifierPart).filter(Boolean).join("_");
}

function SubjectsContent({ token }: { token: string }) {
  const [items, setItems] = useState<UtenzeSubjectListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<FilterState>(emptyFilters);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isExportingCsv, setIsExportingCsv] = useState(false);
  const [isExportingXlsx, setIsExportingXlsx] = useState(false);
  const [isImportingCsv, setIsImportingCsv] = useState(false);
  const [csvUploadProgress, setCsvUploadProgress] = useState(0);
  const [createType, setCreateType] = useState<"person" | "company">("person");
  const [personSurname, setPersonSurname] = useState("");
  const [personName, setPersonName] = useState("");
  const [personCf, setPersonCf] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [companyVat, setCompanyVat] = useState("");
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvImportResult, setCsvImportResult] = useState<UtenzeCsvImportResult | null>(null);
  const [duplicateCfMessage, setDuplicateCfMessage] = useState<string | null>(null);
  const [selectedSubjectId, setSelectedSubjectId] = useState<string | null>(null);
  const [selectedSubject, setSelectedSubject] = useState<UtenzeSubjectDetail | null>(null);
  const [isSubjectModalLoading, setIsSubjectModalLoading] = useState(false);
  const [subjectModalError, setSubjectModalError] = useState<string | null>(null);
  const [previewDocument, setPreviewDocument] = useState<UtenzeDocument | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [previewKind, setPreviewKind] = useState<DocumentPreviewKind>("download");
  const [previewHtml, setPreviewHtml] = useState<string | null>(null);
  const [spreadsheetPreview, setSpreadsheetPreview] = useState<SpreadsheetPreviewSheet[]>([]);
  const [textPreview, setTextPreview] = useState<string | null>(null);

  const deferredSearch = useDeferredValue(filters.search);
  const normalizedSearch = deferredSearch.trim();
  const effectiveSearch = normalizedSearch.length === 0 || normalizedSearch.length >= 3 ? normalizedSearch || undefined : undefined;
  const derivedLetter = useMemo(
    () => deriveArchiveLetter(createType === "person" ? personSurname : companyName),
    [companyName, createType, personSurname],
  );
  const derivedSourceNameRaw = useMemo(
    () =>
      buildSourceNameRaw(createType, {
        personSurname,
        personName,
        personCf,
        companyName,
        companyVat,
      }),
    [companyName, companyVat, createType, personCf, personName, personSurname],
  );

  const refreshSubjects = useCallback(async (targetPage: number = page) => {
    const response = await getUtenzeSubjects(token, {
      page: targetPage,
      pageSize: 20,
      search: effectiveSearch,
      subjectType: filters.subjectType || undefined,
      status: filters.status || undefined,
      letter: filters.letter || undefined,
      requiresReview:
        filters.requiresReview === "" ? undefined : filters.requiresReview === "true",
    });
    setItems(response.items);
    setTotal(response.total);
  }, [effectiveSearch, filters.letter, filters.requiresReview, filters.status, filters.subjectType, page, token]);

  useEffect(() => {
    async function loadSubjects() {
      setIsLoading(true);
      try {
        await refreshSubjects(page);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore caricamento utenti");
      } finally {
        setIsLoading(false);
      }
    }

    void loadSubjects();
  }, [page, refreshSubjects]);

  useEffect(() => {
    if (selectedSubjectId == null) {
      setSelectedSubject(null);
      setSubjectModalError(null);
      if (previewDocument || previewUrl) {
        if (previewUrl) {
          URL.revokeObjectURL(previewUrl);
        }
        setPreviewDocument(null);
        setPreviewUrl(null);
        setPreviewError(null);
        setIsLoadingPreview(false);
        setPreviewKind("download");
        setPreviewHtml(null);
        setSpreadsheetPreview([]);
      }
      return;
    }

    const subjectId = selectedSubjectId;
    let cancelled = false;

    async function loadSubjectDetail() {
      setIsSubjectModalLoading(true);
      setSubjectModalError(null);
      try {
        const detail = await getUtenzeSubject(token, subjectId);
        if (!cancelled) {
          setSelectedSubject(detail);
        }
      } catch (error) {
        if (!cancelled) {
          setSubjectModalError(error instanceof Error ? error.message : "Errore caricamento utente");
        }
      } finally {
        if (!cancelled) {
          setIsSubjectModalLoading(false);
        }
      }
    }

    void loadSubjectDetail();

    return () => {
      cancelled = true;
    };
  }, [previewDocument, previewUrl, selectedSubjectId, token]);

  useEffect(() => {
    if (!duplicateCfMessage && !selectedSubjectId) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape") {
        return;
      }

      if (duplicateCfMessage) {
        setDuplicateCfMessage(null);
        return;
      }

      if (previewDocument) {
        if (previewUrl) {
          URL.revokeObjectURL(previewUrl);
        }
        setPreviewDocument(null);
        setPreviewUrl(null);
        setPreviewError(null);
        setPreviewKind("download");
        setPreviewHtml(null);
        setSpreadsheetPreview([]);
        setTextPreview(null);
        setIsLoadingPreview(false);
        return;
      }

      if (selectedSubjectId) {
        setSelectedSubjectId(null);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [duplicateCfMessage, previewDocument, previewUrl, selectedSubjectId]);

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  const columns = useMemo<ColumnDef<UtenzeSubjectListItem>[]>(
    () => [
      {
        header: "Utente",
        accessorKey: "display_name",
        cell: ({ row }) => (
          <div>
            <p className="text-sm font-medium text-[#1D4E35]">{row.original.display_name}</p>
            <p className="text-xs text-gray-400">{row.original.source_name_raw}</p>
          </div>
        ),
      },
      {
        header: "Tipo",
        accessorKey: "subject_type",
        cell: ({ row }) => <span className="text-sm uppercase text-gray-700">{row.original.subject_type}</span>,
      },
      {
        header: "Identificativo",
        accessorKey: "codice_fiscale",
        cell: ({ row }) => (
          <span className="text-sm text-gray-700">{row.original.codice_fiscale || row.original.partita_iva || "—"}</span>
        ),
      },
      {
        header: "Archivio",
        accessorKey: "nas_folder_letter",
        cell: ({ row }) => (
          <span className="text-sm text-gray-700">
            {row.original.nas_folder_letter || "?"} · {row.original.document_count} doc
          </span>
        ),
      },
      {
        header: "Stato",
        accessorKey: "status",
        cell: ({ row }) => (
          <span className={`rounded-full px-2 py-1 text-[11px] font-medium ${row.original.requires_review ? "bg-amber-50 text-amber-700" : "bg-gray-100 text-gray-700"}`}>
            {row.original.requires_review ? "Review" : row.original.status}
          </span>
        ),
      },
      {
        header: "Aggiornato",
        accessorKey: "updated_at",
        cell: ({ row }) => <span className="text-sm text-gray-700">{formatDateTime(row.original.updated_at)}</span>,
      },
    ],
    [],
  );

  async function handleCreateSubject() {
    if (!derivedSourceNameRaw || !derivedLetter) {
      setSaveError("Compila i dati principali dell'utente prima del salvataggio.");
      setSaveMessage(null);
      setDuplicateCfMessage(null);
      return;
    }

    setIsSaving(true);
    setSaveError(null);
    setSaveMessage(null);
    setDuplicateCfMessage(null);

    const payload: UtenzeSubjectCreateInput = {
      subject_type: createType,
      source_name_raw: derivedSourceNameRaw,
      nas_folder_letter: derivedLetter || null,
      requires_review: false,
    };

    if (createType === "person") {
      payload.person = {
        cognome: personSurname,
        nome: personName,
        codice_fiscale: personCf,
        data_nascita: null,
        comune_nascita: null,
        indirizzo: null,
        comune_residenza: null,
        cap: null,
        email: null,
        telefono: null,
        note: null,
      };
    } else {
      payload.company = {
        ragione_sociale: companyName,
        partita_iva: companyVat,
        codice_fiscale: null,
        forma_giuridica: null,
        sede_legale: null,
        comune_sede: null,
        cap: null,
        email_pec: null,
        telefono: null,
        note: null,
      };
    }

    try {
      await createUtenzeSubject(token, payload);
      setSaveMessage("Utente creato correttamente.");
      setPersonSurname("");
      setPersonName("");
      setPersonCf("");
      setCompanyName("");
      setCompanyVat("");
      setPage(1);
      await refreshSubjects(1);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Errore creazione utente";
      if (message.toLowerCase().includes("codice fiscale")) {
        setDuplicateCfMessage(message);
      } else {
        setSaveError(message);
      }
    } finally {
      setIsSaving(false);
    }
  }

  async function handleCsvImport() {
    if (!csvFile) {
      setSaveError("Seleziona un file CSV da importare.");
      return;
    }

    setIsImportingCsv(true);
    setCsvUploadProgress(0);
    setSaveError(null);
    setSaveMessage(null);
    setCsvImportResult(null);
    try {
      const result = await importUtenzeSubjectsCsv(token, csvFile, setCsvUploadProgress);
      setCsvImportResult(result);
      setSaveMessage(
        `Import CSV completato: ${result.created_subjects} creati, ${result.updated_subjects} aggiornati, ${result.skipped_rows} scartati.`,
      );
      setCsvFile(null);
      setPage(1);
      await refreshSubjects(1);
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Errore import CSV");
    } finally {
      setIsImportingCsv(false);
      setCsvUploadProgress(0);
    }
  }

  const closePreviewModal = useCallback(() => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setPreviewDocument(null);
    setPreviewUrl(null);
    setPreviewError(null);
    setIsLoadingPreview(false);
    setPreviewKind("download");
    setPreviewHtml(null);
    setSpreadsheetPreview([]);
    setTextPreview(null);
  }, [previewUrl]);

  async function handlePreviewDocument(document: UtenzeDocument) {
    if (!document.id) {
      setSubjectModalError("Il documento selezionato non ha un identificativo valido.");
      return;
    }

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }

    setPreviewDocument(document);
    setPreviewUrl(null);
    setPreviewError(null);
    setIsLoadingPreview(true);
    setPreviewKind("download");
    setPreviewHtml(null);
    setSpreadsheetPreview([]);
    setTextPreview(null);

    try {
      const blob = await downloadUtenzeDocumentBlob(token, document.id);
      const objectUrl = URL.createObjectURL(blob);
      const extension = document.extension?.toLowerCase() ?? null;
      setPreviewUrl(objectUrl);

      if (document.is_pdf) {
        setPreviewKind("pdf");
        return;
      }

      if (isPreviewableImage(extension)) {
        setPreviewKind("image");
        return;
      }

      if (extension === ".docx") {
        const mammoth = await import("mammoth");
        const arrayBuffer = await blob.arrayBuffer();
        const result = await mammoth.convertToHtml({ arrayBuffer });
        setPreviewHtml(result.value);
        setPreviewKind("docx");
        return;
      }

      if (isPreviewableSpreadsheet(extension)) {
        const xlsx = await import("xlsx");
        const arrayBuffer = await blob.arrayBuffer();
        const workbook = xlsx.read(arrayBuffer, { type: "array" });
        const sheets = workbook.SheetNames.slice(0, 3).map((sheetName) => {
          const worksheet = workbook.Sheets[sheetName];
          const rows = xlsx.utils.sheet_to_json<(string | number | boolean | null)[]>(worksheet, {
            header: 1,
            blankrows: false,
            defval: "",
          });
          return {
            name: sheetName,
            rows: rows.slice(0, 25).map((row) => row.map((cell) => String(cell ?? ""))),
          };
        });
        setSpreadsheetPreview(sheets);
        setPreviewKind("spreadsheet");
        return;
      }

      if (isPreviewableText(extension)) {
        const textContent = await blob.text();
        setTextPreview(textContent);
        setPreviewKind("text");
        return;
      }

      setPreviewKind("download");
    } catch (error) {
      setPreviewError(error instanceof Error ? error.message : "Errore caricamento anteprima documento");
    } finally {
      setIsLoadingPreview(false);
    }
  }

  const pageCount = Math.max(1, Math.ceil(total / 20));
  const csvImportTone = csvImportResult
    ? csvImportResult.skipped_rows > 0
      ? {
          border: "border-amber-200",
          background: "bg-amber-50",
          badge: "bg-amber-100 text-amber-800",
          title: "Import completato con warning",
          copy: "Alcune righe non sono state applicate. Controlla il dettaglio sotto per correggere i record scartati.",
        }
      : {
          border: "border-emerald-200",
          background: "bg-emerald-50",
          badge: "bg-emerald-100 text-emerald-800",
          title: "Import completato",
          copy: "Tutte le righe valide del file sono state elaborate correttamente.",
        }
    : null;

  function triggerDownload(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const anchor = window.document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  async function handleExport(format: "csv" | "xlsx") {
    const setter = format === "csv" ? setIsExportingCsv : setIsExportingXlsx;
    setter(true);
    try {
      const blob = await downloadUtenzeExportBlob(token, {
        format,
        search: filters.search || undefined,
        subjectType: filters.subjectType || undefined,
        status: filters.status || undefined,
        letter: filters.letter || undefined,
        requiresReview: filters.requiresReview === "" ? undefined : filters.requiresReview === "true",
      });
      triggerDownload(blob, `utenze-export.${format}`);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore export utenze");
    } finally {
      setter(false);
    }
  }

  return (
    <div className="page-stack">
      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Nuovo utente manuale</p>
          <p className="section-copy">Inserimento rapido per utenti del Consorzio non ancora importati dal NAS.</p>
        </div>
        {saveError ? <p className="mb-3 text-sm text-red-600">{saveError}</p> : null}
        {saveMessage ? <p className="mb-3 text-sm text-[#1D4E35]">{saveMessage}</p> : null}
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <label className="block text-sm font-medium text-gray-700">
            Tipo
            <select className="form-control mt-1" value={createType} onChange={(event) => setCreateType(event.target.value as "person" | "company")}>
              <option value="person">Persona fisica</option>
              <option value="company">Persona giuridica</option>
            </select>
          </label>
          <label className="block text-sm font-medium text-gray-700">
            Lettera archivio
            <input className="form-control mt-1 bg-gray-50 text-gray-500" value={derivedLetter} readOnly placeholder="Auto" />
          </label>
          <label className="block text-sm font-medium text-gray-700 xl:col-span-2">
            Source name raw
            <input className="form-control mt-1 bg-gray-50 text-gray-500" value={derivedSourceNameRaw} readOnly placeholder="Generato automaticamente" />
          </label>
          {createType === "person" ? (
            <>
              <label className="block text-sm font-medium text-gray-700">
                Cognome
                <input className="form-control mt-1" value={personSurname} onChange={(event) => setPersonSurname(event.target.value)} />
              </label>
              <label className="block text-sm font-medium text-gray-700">
                Nome
                <input className="form-control mt-1" value={personName} onChange={(event) => setPersonName(event.target.value)} />
              </label>
              <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                Codice fiscale
                <input className="form-control mt-1" value={personCf} onChange={(event) => setPersonCf(event.target.value.toUpperCase())} />
              </label>
            </>
          ) : (
            <>
              <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                Ragione sociale
                <input className="form-control mt-1" value={companyName} onChange={(event) => setCompanyName(event.target.value)} />
              </label>
              <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                Partita IVA
                <input className="form-control mt-1" value={companyVat} onChange={(event) => setCompanyVat(event.target.value)} />
              </label>
            </>
          )}
        </div>
        <div className="mt-4 flex justify-end">
          <button className="btn-primary" onClick={() => void handleCreateSubject()} type="button" disabled={isSaving}>
            {isSaving ? "Salvataggio..." : "Crea utente"}
          </button>
        </div>
      </article>

      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Import CSV persone fisiche</p>
          <p className="section-copy">Import con separatore `;` e upsert per Codice Fiscale.</p>
        </div>
        <div className="rounded-2xl border border-[#D9E8DF] bg-gradient-to-br from-[#F7FBF8] to-white p-4 md:p-5">
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_220px] lg:items-end">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#6B8A78]">Caricamento file</p>
              <label className="mt-3 block text-sm font-medium text-gray-700">
                <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-[#CFE1D6] bg-white px-4 py-4 shadow-sm">
                  <label
                    htmlFor="anagrafica-csv-upload"
                    className="inline-flex cursor-pointer items-center rounded-xl bg-[#1D4E35] px-4 py-2.5 text-sm font-medium text-white transition hover:bg-[#163b29]"
                  >
                    Seleziona file
                  </label>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-gray-800">{csvFile?.name || "Nessun file selezionato"}</p>
                    <p className="mt-1 text-xs text-gray-500">Formato supportato: CSV con separatore `;`</p>
                  </div>
                  <input
                    id="anagrafica-csv-upload"
                    className="sr-only"
                    type="file"
                    accept=".csv,text/csv"
                    onChange={(event) => setCsvFile(event.target.files?.[0] ?? null)}
                  />
                </div>
              </label>
            </div>
            <div className="rounded-2xl border border-[#D9E8DF] bg-white p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#6B8A78]">Azione</p>
              <button className="btn-primary mt-3 w-full justify-center" onClick={() => void handleCsvImport()} type="button" disabled={isImportingCsv || !csvFile}>
                {isImportingCsv ? "Import in corso..." : "Importa CSV"}
              </button>
              <p className="mt-2 text-xs text-gray-500">Il file viene validato e importato con upsert su Codice Fiscale.</p>
            </div>
          </div>
        </div>
        <p className="mt-3 text-xs text-gray-500">
          Campi attesi: Codice Fiscale;Cognome;Nome;Sesso;Data_Nascita;Com_Nascita;Com_Residenza;CAP;PR;Indirizzo_Residenza;Variaz_Anagr;STATO;Decesso
        </p>
        {isImportingCsv ? (
          <div className="mt-4 rounded-2xl border border-[#CFE1D6] bg-[#F4FAF6] px-4 py-4 shadow-sm">
            <div className="mb-2 flex items-center justify-between gap-3">
              <p className="text-sm font-medium text-[#1D4E35]">Upload CSV in corso</p>
              <p className="text-sm font-semibold text-[#1D4E35]">{csvUploadProgress}%</p>
            </div>
            <div className="h-2.5 overflow-hidden rounded-full bg-white">
              <div
                className="h-full rounded-full bg-[#1D4E35] transition-[width] duration-300"
                style={{ width: `${csvUploadProgress}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-gray-600">
              {csvUploadProgress < 100 ? "Trasferimento file verso il backend." : "Upload completato, elaborazione in corso."}
            </p>
          </div>
        ) : null}
        {csvImportResult ? (
          <div className="mt-4 space-y-4">
            {csvImportTone ? (
              <div className={`rounded-2xl border px-4 py-4 shadow-sm ${csvImportTone.border} ${csvImportTone.background}`}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-gray-900">{csvImportTone.title}</p>
                    <p className="mt-1 text-sm text-gray-600">{csvImportTone.copy}</p>
                  </div>
                  <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${csvImportTone.badge}`}>
                    {csvImportResult.skipped_rows > 0 ? "Warning" : "Successo"}
                  </span>
                </div>
              </div>
            ) : null}
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Righe lette</p>
                <p className="mt-2 text-2xl font-semibold text-gray-900">{csvImportResult.total_rows}</p>
              </div>
              <div className="rounded-2xl border border-emerald-100 bg-emerald-50 p-4 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Creati</p>
                <p className="mt-2 text-2xl font-semibold text-emerald-900">{csvImportResult.created_subjects}</p>
              </div>
              <div className="rounded-2xl border border-sky-100 bg-sky-50 p-4 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">Aggiornati</p>
                <p className="mt-2 text-2xl font-semibold text-sky-900">{csvImportResult.updated_subjects}</p>
              </div>
              <div className="rounded-2xl border border-amber-100 bg-amber-50 p-4 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">Scartati</p>
                <p className="mt-2 text-2xl font-semibold text-amber-900">{csvImportResult.skipped_rows}</p>
              </div>
            </div>

            {csvImportResult.errors.length > 0 ? (
              <div className="rounded-2xl border border-amber-200 bg-gradient-to-br from-amber-50 to-[#FFFDF5] px-4 py-4 shadow-sm">
                <div className="mb-3">
                  <p className="text-sm font-medium text-amber-900">Righe scartate</p>
                  <p className="text-xs text-amber-800">
                    Il file è stato importato, ma alcune righe non sono state applicate. Sono mostrati i primi {Math.min(csvImportResult.errors.length, 20)} casi.
                  </p>
                </div>
                <div className="space-y-2">
                  {csvImportResult.errors.slice(0, 20).map((item) => (
                    <div key={`${item.row_number}-${item.codice_fiscale || "none"}`} className="rounded-xl border border-amber-100 bg-white px-3 py-3">
                      <p className="text-sm font-medium text-gray-900">
                        Riga {item.row_number}
                        {item.codice_fiscale ? ` · ${item.codice_fiscale}` : ""}
                      </p>
                      <p className="mt-1 text-xs text-red-700">{item.message}</p>
                    </div>
                  ))}
                </div>
                {csvImportResult.errors.length > 20 ? (
                  <p className="mt-3 text-xs text-amber-800">
                    Altre {csvImportResult.errors.length - 20} righe scartate non mostrate in questo riepilogo.
                  </p>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}
      </article>

      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Registro Utenti</p>
          <p className="section-copy">Ricerca server-side su nome, cognome e codice fiscale con risposta immediata da 3 caratteri.</p>
        </div>

        <div className="mb-4 flex flex-wrap justify-end gap-2">
          <button className="btn-secondary" type="button" onClick={() => void handleExport("csv")} disabled={isExportingCsv}>
            {isExportingCsv ? "Export CSV..." : "Export CSV"}
          </button>
          <button className="btn-secondary" type="button" onClick={() => void handleExport("xlsx")} disabled={isExportingXlsx}>
            {isExportingXlsx ? "Export XLSX..." : "Export XLSX"}
          </button>
        </div>

        <TableFilters>
          <input
            className="form-control min-w-[220px]"
            value={filters.search}
            onChange={(event) => {
              setFilters((current) => ({ ...current, search: event.target.value }));
              setPage(1);
            }}
            placeholder="Cerca per nome, cognome o CF..."
          />
          <select
            className="form-control min-w-[180px]"
            value={filters.subjectType}
            onChange={(event) => {
              setFilters((current) => ({ ...current, subjectType: event.target.value }));
              setPage(1);
            }}
          >
            <option value="">Tutti i tipi</option>
            <option value="person">Persona fisica</option>
            <option value="company">Persona giuridica</option>
            <option value="unknown">Unknown</option>
          </select>
          <select
            className="form-control min-w-[160px]"
            value={filters.status}
            onChange={(event) => {
              setFilters((current) => ({ ...current, status: event.target.value }));
              setPage(1);
            }}
          >
            <option value="">Tutti gli stati</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="duplicate">Duplicate</option>
          </select>
          <input
            className="form-control w-20"
            value={filters.letter}
            onChange={(event) => {
              setFilters((current) => ({ ...current, letter: event.target.value.toUpperCase().slice(0, 1) }));
              setPage(1);
            }}
            placeholder="A-Z"
          />
          <select
            className="form-control min-w-[180px]"
            value={filters.requiresReview}
            onChange={(event) => {
              setFilters((current) => ({ ...current, requiresReview: event.target.value }));
              setPage(1);
            }}
          >
            <option value="">Tutte le revisioni</option>
            <option value="true">Solo da revisionare</option>
            <option value="false">Solo puliti</option>
          </select>
        </TableFilters>

        {normalizedSearch.length > 0 && normalizedSearch.length < 3 ? (
          <p className="mb-3 text-xs text-gray-400">Digita almeno 3 caratteri per avviare la ricerca.</p>
        ) : null}

        {loadError ? <p className="mb-3 text-sm text-red-600">{loadError}</p> : null}
        {isLoading ? <p className="mb-3 text-sm text-gray-500">Caricamento utenti in corso.</p> : null}

        <DataTable
          data={items}
          columns={columns}
          initialPageSize={100}
          emptyTitle="Nessun utente trovato"
          emptyDescription="Nessun record disponibile per i filtri correnti."
          onRowClick={(row) => setSelectedSubjectId(row.id)}
        />

        <div className="mt-4 flex items-center justify-between gap-3">
          <p className="text-sm text-gray-500">
            Pagina {page} di {pageCount} · {total} record
          </p>
          <div className="flex gap-2">
            <button className="btn-secondary" type="button" disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>
              Precedente
            </button>
            <button className="btn-secondary" type="button" disabled={page >= pageCount} onClick={() => setPage((current) => current + 1)}>
              Successiva
            </button>
          </div>
        </div>
      </article>

      {duplicateCfMessage ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4 py-6">
          <button
            aria-label="Chiudi avviso duplicato"
            className="absolute inset-0"
            onClick={() => setDuplicateCfMessage(null)}
            type="button"
          />
          <div className="relative z-10 w-full max-w-lg rounded-[28px] border border-red-100 bg-white p-6 shadow-[0_24px_64px_rgba(15,25,19,0.18)]">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-red-500">Codice fiscale duplicato</p>
            <h3 className="mt-2 text-xl font-medium text-gray-900">Utente gia presente nel registro</h3>
            <p className="mt-3 text-sm text-gray-600">{duplicateCfMessage}</p>
            <div className="mt-5 flex justify-end">
              <button className="btn-secondary" onClick={() => setDuplicateCfMessage(null)} type="button">
                Chiudi
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {selectedSubjectId ? (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 px-4 py-6 backdrop-blur-sm md:p-8">
          <button
            aria-label="Chiudi dettaglio utente"
            className="absolute inset-0"
            onClick={() => setSelectedSubjectId(null)}
            type="button"
          />
          <div className="relative z-10 max-h-[calc(100vh-2rem)] w-full max-w-4xl overflow-y-auto rounded-[28px] border border-gray-200 bg-[#F6F7F2] p-5 shadow-[0_30px_80px_rgba(15,25,19,0.18)] md:max-h-[calc(100vh-4rem)] md:p-6">
            <div className="mb-5 flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-medium uppercase tracking-[0.18em] text-gray-400">Dettaglio utente</p>
                <h3 className="mt-1 text-xl font-medium text-gray-900">Vista rapida del registro</h3>
              </div>
              <div className="flex items-center gap-3">
                <Link className="text-sm font-medium text-[#1D4E35]" href={`/utenze/${selectedSubjectId}`}>
                  Apri pagina completa
                </Link>
                <button className="btn-secondary" onClick={() => setSelectedSubjectId(null)} type="button">
                  Chiudi
                </button>
              </div>
            </div>

            {isSubjectModalLoading ? <p className="text-sm text-gray-500">Caricamento utente in corso.</p> : null}
            {subjectModalError ? <p className="text-sm text-red-600">{subjectModalError}</p> : null}
            {selectedSubject ? (
              <div className="space-y-6">
                <section className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-2xl border border-[#D9E8DF] bg-white p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Identita</p>
                    <h4 className="mt-2 text-lg font-medium text-[#1D4E35]">
                      {selectedSubject.person ? `${selectedSubject.person.cognome} ${selectedSubject.person.nome}` : selectedSubject.company?.ragione_sociale || "Utente"}
                    </h4>
                    <div className="mt-4 space-y-2 text-sm text-gray-600">
                      <p><span className="font-medium text-gray-900">Tipo:</span> {selectedSubject.subject_type}</p>
                      <p><span className="font-medium text-gray-900">Stato:</span> {selectedSubject.status}</p>
                      <p><span className="font-medium text-gray-900">Source name raw:</span> {selectedSubject.source_name_raw}</p>
                      <p><span className="font-medium text-gray-900">Lettera archivio:</span> {selectedSubject.nas_folder_letter || "n/d"}</p>
                    </div>
                  </div>
                  <div className="rounded-2xl border border-[#D9E8DF] bg-white p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Riferimenti</p>
                    <div className="mt-4 space-y-2 text-sm text-gray-600">
                      <p><span className="font-medium text-gray-900">Codice fiscale:</span> {selectedSubject.person?.codice_fiscale || selectedSubject.company?.codice_fiscale || "n/d"}</p>
                      <p><span className="font-medium text-gray-900">Partita IVA:</span> {selectedSubject.company?.partita_iva || "n/d"}</p>
                      <p><span className="font-medium text-gray-900">Percorso NAS:</span> {selectedSubject.nas_folder_path || "n/d"}</p>
                      <p><span className="font-medium text-gray-900">Aggiornato:</span> {formatDateTime(selectedSubject.updated_at)}</p>
                    </div>
                  </div>
                </section>

                {selectedSubject.person ? (
                  <section className="rounded-2xl border border-[#D9E8DF] bg-white p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Utenza persona</p>
                    <div className="mt-4 grid gap-3 md:grid-cols-2 text-sm text-gray-600">
                      <p><span className="font-medium text-gray-900">Email:</span> {selectedSubject.person.email || "n/d"}</p>
                      <p><span className="font-medium text-gray-900">Telefono:</span> {selectedSubject.person.telefono || "n/d"}</p>
                      <p><span className="font-medium text-gray-900">Comune nascita:</span> {selectedSubject.person.comune_nascita || "n/d"}</p>
                      <p><span className="font-medium text-gray-900">Comune residenza:</span> {selectedSubject.person.comune_residenza || "n/d"}</p>
                    </div>
                  </section>
                ) : null}

                {selectedSubject.company ? (
                  <section className="rounded-2xl border border-[#D9E8DF] bg-white p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Utenza societa</p>
                    <div className="mt-4 grid gap-3 md:grid-cols-2 text-sm text-gray-600">
                      <p><span className="font-medium text-gray-900">Ragione sociale:</span> {selectedSubject.company.ragione_sociale}</p>
                      <p><span className="font-medium text-gray-900">Partita IVA:</span> {selectedSubject.company.partita_iva}</p>
                      <p><span className="font-medium text-gray-900">PEC:</span> {selectedSubject.company.email_pec || "n/d"}</p>
                      <p><span className="font-medium text-gray-900">Telefono:</span> {selectedSubject.company.telefono || "n/d"}</p>
                    </div>
                  </section>
                ) : null}

                <section className="grid gap-4 md:grid-cols-3">
                  <div className="rounded-2xl border border-[#D9E8DF] bg-white p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Documenti</p>
                    <p className="mt-2 text-2xl font-semibold text-gray-900">{selectedSubject.documents.length}</p>
                  </div>
                  <div className="rounded-2xl border border-[#D9E8DF] bg-white p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Audit log</p>
                    <p className="mt-2 text-2xl font-semibold text-gray-900">{selectedSubject.audit_log.length}</p>
                  </div>
                  <div className="rounded-2xl border border-[#D9E8DF] bg-white p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Catasto</p>
                    <p className="mt-2 text-2xl font-semibold text-gray-900">{selectedSubject.catasto_documents.length}</p>
                  </div>
                </section>

                <section className="rounded-2xl border border-[#D9E8DF] bg-white p-4">
                  <div className="mb-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Documenti associati</p>
                    <p className="mt-1 text-sm text-gray-600">Clicca un documento per aprirne l&apos;anteprima senza lasciare la modal.</p>
                  </div>
                  {selectedSubject.documents.length === 0 ? (
                    <p className="text-sm text-gray-500">Nessun documento associato a questo utente.</p>
                  ) : (
                    <div className="space-y-3">
                      {selectedSubject.documents.map((document) => (
                        <button
                          key={document.id || document.nas_path}
                          type="button"
                          onClick={() => void handlePreviewDocument(document)}
                          className="flex w-full items-center justify-between gap-3 rounded-xl border border-gray-100 px-4 py-3 text-left transition hover:bg-gray-50"
                        >
                          <div className="min-w-0">
                            <p className="truncate text-sm font-medium text-gray-900">{document.filename}</p>
                            <p className="mt-1 truncate text-xs text-gray-500">{document.nas_path}</p>
                          </div>
                          <div className="shrink-0 text-right">
                            <p className="text-xs font-medium uppercase tracking-[0.12em] text-[#1D4E35]">{document.doc_type}</p>
                            <p className="mt-1 text-xs text-gray-400">{document.extension || "file"}</p>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </section>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      {previewDocument ? (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/55 px-4 py-6">
          <button
            aria-label="Chiudi anteprima documento"
            className="absolute inset-0"
            onClick={closePreviewModal}
            type="button"
          />
          <div className="relative z-10 flex h-full max-h-[92vh] w-full max-w-5xl flex-col rounded-2xl bg-white shadow-2xl">
            <div className="flex items-center justify-between gap-4 border-b border-gray-100 px-6 py-4">
              <div className="min-w-0">
                <p className="section-title">Anteprima documento</p>
                <p className="mt-1 truncate text-sm text-gray-500">{previewDocument.filename}</p>
              </div>
              <button className="btn-secondary" type="button" onClick={closePreviewModal}>
                Chiudi
              </button>
            </div>
            <div className="flex-1 overflow-hidden px-6 py-4">
              {isLoadingPreview ? <p className="text-sm text-gray-500">Caricamento anteprima...</p> : null}
              {previewError ? <p className="text-sm text-red-600">{previewError}</p> : null}
              {!isLoadingPreview && !previewError && previewUrl && previewKind === "pdf" ? (
                <iframe className="h-full min-h-[70vh] w-full rounded-xl border border-gray-200" src={previewUrl} title={previewDocument.filename} />
              ) : null}
              {!isLoadingPreview && !previewError && previewUrl && previewKind === "image" ? (
                <div className="flex h-full min-h-[70vh] items-center justify-center overflow-auto rounded-xl border border-gray-200 bg-gray-50 p-4">
                  <Image
                    src={previewUrl}
                    alt={previewDocument.filename}
                    width={1600}
                    height={1200}
                    unoptimized
                    className="max-h-full max-w-full rounded-lg object-contain"
                  />
                </div>
              ) : null}
              {!isLoadingPreview && !previewError && previewKind === "docx" ? (
                <div className="h-full min-h-[70vh] overflow-auto rounded-xl border border-gray-200 bg-white p-6">
                  {previewHtml ? (
                    <div className="prose prose-sm max-w-none text-gray-700" dangerouslySetInnerHTML={{ __html: previewHtml }} />
                  ) : (
                    <p className="text-sm text-gray-500">Nessun contenuto leggibile disponibile per questo file DOCX.</p>
                  )}
                </div>
              ) : null}
              {!isLoadingPreview && !previewError && previewKind === "spreadsheet" ? (
                <div className="h-full min-h-[70vh] overflow-auto rounded-xl border border-gray-200 bg-white p-4">
                  <div className="space-y-6">
                    {spreadsheetPreview.length > 0 ? spreadsheetPreview.map((sheet) => (
                      <section key={sheet.name}>
                        <p className="mb-3 text-sm font-medium text-gray-900">{sheet.name}</p>
                        {sheet.rows.length > 0 ? (
                          <div className="overflow-x-auto rounded-lg border border-gray-100">
                            <table className="min-w-full divide-y divide-gray-200 text-sm">
                              <tbody className="divide-y divide-gray-100 bg-white">
                                {sheet.rows.map((row, rowIndex) => (
                                  <tr key={`${sheet.name}-${rowIndex}`}>
                                    {row.map((cell, cellIndex) => (
                                      <td key={`${sheet.name}-${rowIndex}-${cellIndex}`} className="px-3 py-2 align-top text-gray-700">
                                        {cell || "—"}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ) : (
                          <p className="text-sm text-gray-500">Foglio senza celle valorizzate.</p>
                        )}
                      </section>
                    )) : (
                      <p className="text-sm text-gray-500">Nessun dato tabellare leggibile disponibile per questo file.</p>
                    )}
                  </div>
                </div>
              ) : null}
              {!isLoadingPreview && !previewError && previewKind === "text" ? (
                <div className="h-full min-h-[70vh] overflow-auto rounded-xl border border-gray-200 bg-white p-6">
                  <pre className="whitespace-pre-wrap break-words text-sm leading-6 text-gray-700">{textPreview || "File di testo vuoto."}</pre>
                </div>
              ) : null}
              {!isLoadingPreview && !previewError && previewUrl && previewKind === "download" ? (
                <div className="flex h-full min-h-[70vh] items-center justify-center rounded-xl border border-dashed border-gray-200 bg-gray-50 p-6 text-center">
                  <div>
                    <p className="text-sm font-medium text-gray-900">Anteprima inline non disponibile per questo formato.</p>
                    <a className="btn-primary mt-4 inline-flex" href={previewUrl} download={previewDocument.filename}>
                      Scarica documento
                    </a>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default function UtenzeSubjectsPage() {
  return (
    <UtenzeModulePage
      title="Utenti"
      description="Lista operativa degli utenti del Consorzio con filtri server-side e inserimento manuale."
      breadcrumb="Utenti"
    >
      {({ token }) => <SubjectsContent token={token} />}
    </UtenzeModulePage>
  );
}
