"use client";

import { useCallback, useDeferredValue, useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { AnagraficaModulePage } from "@/components/anagrafica/anagrafica-module-page";
import { DataTable } from "@/components/table/data-table";
import { TableFilters } from "@/components/table/table-filters";
import { createAnagraficaSubject, downloadAnagraficaExportBlob, getAnagraficaSubjects, importAnagraficaSubjectsCsv } from "@/lib/api";
import { formatDateTime } from "@/lib/presentation";
import type { AnagraficaCsvImportResult, AnagraficaSubjectCreateInput, AnagraficaSubjectListItem } from "@/types/api";

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

function SubjectsContent({ token }: { token: string }) {
  const [items, setItems] = useState<AnagraficaSubjectListItem[]>([]);
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
  const [sourceNameRaw, setSourceNameRaw] = useState("");
  const [letter, setLetter] = useState("");
  const [personSurname, setPersonSurname] = useState("");
  const [personName, setPersonName] = useState("");
  const [personCf, setPersonCf] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [companyVat, setCompanyVat] = useState("");
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvImportResult, setCsvImportResult] = useState<AnagraficaCsvImportResult | null>(null);

  const deferredSearch = useDeferredValue(filters.search);
  const normalizedSearch = deferredSearch.trim();
  const effectiveSearch = normalizedSearch.length === 0 || normalizedSearch.length >= 3 ? normalizedSearch || undefined : undefined;

  const refreshSubjects = useCallback(async (targetPage: number = page) => {
    const response = await getAnagraficaSubjects(token, {
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
        setLoadError(error instanceof Error ? error.message : "Errore caricamento soggetti");
      } finally {
        setIsLoading(false);
      }
    }

    void loadSubjects();
  }, [page, refreshSubjects]);

  const columns = useMemo<ColumnDef<AnagraficaSubjectListItem>[]>(
    () => [
      {
        header: "Soggetto",
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
    setIsSaving(true);
    setSaveError(null);
    setSaveMessage(null);

    const payload: AnagraficaSubjectCreateInput = {
      subject_type: createType,
      source_name_raw: sourceNameRaw || (createType === "person" ? `${personSurname}_${personName}_${personCf}` : `${companyName}_${companyVat}`),
      nas_folder_letter: letter || null,
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
      await createAnagraficaSubject(token, payload);
      setSaveMessage("Soggetto creato correttamente.");
      setSourceNameRaw("");
      setLetter("");
      setPersonSurname("");
      setPersonName("");
      setPersonCf("");
      setCompanyName("");
      setCompanyVat("");
      setPage(1);
      await refreshSubjects(1);
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Errore creazione soggetto");
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
      const result = await importAnagraficaSubjectsCsv(token, csvFile, setCsvUploadProgress);
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
      const blob = await downloadAnagraficaExportBlob(token, {
        format,
        search: filters.search || undefined,
        subjectType: filters.subjectType || undefined,
        status: filters.status || undefined,
        letter: filters.letter || undefined,
        requiresReview: filters.requiresReview === "" ? undefined : filters.requiresReview === "true",
      });
      triggerDownload(blob, `anagrafica-export.${format}`);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore export anagrafica");
    } finally {
      setter(false);
    }
  }

  return (
    <div className="page-stack">
      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Nuovo soggetto manuale</p>
          <p className="section-copy">Inserimento rapido per soggetti del Consorzio non ancora importati dal NAS.</p>
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
            <input className="form-control mt-1" value={letter} onChange={(event) => setLetter(event.target.value.toUpperCase().slice(0, 1))} placeholder="R" />
          </label>
          <label className="block text-sm font-medium text-gray-700 xl:col-span-2">
            Source name raw
            <input className="form-control mt-1" value={sourceNameRaw} onChange={(event) => setSourceNameRaw(event.target.value)} placeholder="Opzionale: nome origine cartella o etichetta sorgente" />
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
            {isSaving ? "Salvataggio..." : "Crea soggetto"}
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
          <p className="section-title">Registro soggetti</p>
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
        {isLoading ? <p className="mb-3 text-sm text-gray-500">Caricamento soggetti in corso.</p> : null}

        <DataTable
          data={items}
          columns={columns}
          initialPageSize={100}
          emptyTitle="Nessun soggetto trovato"
          emptyDescription="Nessun record disponibile per i filtri correnti."
          onRowClick={(row) => {
            window.location.href = `/anagrafica/${row.id}`;
          }}
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
    </div>
  );
}

export default function AnagraficaSubjectsPage() {
  return (
    <AnagraficaModulePage
      title="Soggetti"
      description="Lista operativa delle anagrafiche del Consorzio con filtri server-side e inserimento manuale."
      breadcrumb="Soggetti"
    >
      {({ token }) => <SubjectsContent token={token} />}
    </AnagraficaModulePage>
  );
}
