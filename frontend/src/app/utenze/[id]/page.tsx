"use client";

import Image from "next/image";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { UtenzeModulePage } from "@/components/utenze/utenze-module-page";
import {
  deleteUtenzeDocument,
  downloadUtenzeDocumentBlob,
  getUtenzeSubject,
  getUtenzeSubjectNasCandidates,
  getUtenzeSubjectNasImportStatus,
  importUtenzeSubjectFromNas,
  updateUtenzeDocument,
  updateUtenzeSubject,
  uploadUtenzeSubjectDocument,
} from "@/lib/api";
import { formatDateTime } from "@/lib/presentation";
import { cn } from "@/lib/cn";
import type {
  AnagraficaDocument,
  AnagraficaNasFolderCandidate,
  AnagraficaSubjectDetail,
  AnagraficaSubjectNasImportStatus,
  AnagraficaSubjectUpdateInput,
} from "@/types/api";

type DocumentPreviewKind = "pdf" | "image" | "docx" | "spreadsheet" | "text" | "download";

type SpreadsheetPreviewSheet = {
  name: string;
  rows: string[][];
};

type ManualUploadItem = {
  id: string;
  file: File;
  docType: string;
  notes: string;
};

const IMAGE_EXTENSIONS = new Set([".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"]);
const SPREADSHEET_EXTENSIONS = new Set([".xls", ".xlsx"]);
const TEXT_EXTENSIONS = new Set([".txt", ".csv", ".log", ".md", ".json", ".xml"]);
const DOCUMENT_TYPE_OPTIONS = [
  { value: "ingiunzione", label: "Ingiunzione" },
  { value: "notifica", label: "Notifica" },
  { value: "estratto_debito", label: "Estratto debito" },
  { value: "pratica_interna", label: "Pratica interna" },
  { value: "visura", label: "Visura" },
  { value: "corrispondenza", label: "Corrispondenza" },
  { value: "contratto", label: "Contratto" },
  { value: "altro", label: "Altro" },
] as const;

function isPreviewableImage(extension: string | null): boolean {
  return extension != null && IMAGE_EXTENSIONS.has(extension.toLowerCase());
}

function isPreviewableSpreadsheet(extension: string | null): boolean {
  return extension != null && SPREADSHEET_EXTENSIONS.has(extension.toLowerCase());
}

function isPreviewableText(extension: string | null): boolean {
  return extension != null && TEXT_EXTENSIONS.has(extension.toLowerCase());
}

function DetailContent({ token, subjectId }: { token: string; subjectId: string }) {
  const router = useRouter();
  const manualFileInputRef = useRef<HTMLInputElement | null>(null);
  const [subject, setSubject] = useState<AnagraficaSubjectDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isImportingFromNas, setIsImportingFromNas] = useState(false);
  const [nasCandidates, setNasCandidates] = useState<AnagraficaNasFolderCandidate[]>([]);
  const [nasImportStatus, setNasImportStatus] = useState<AnagraficaSubjectNasImportStatus | null>(null);
  const [selectedNasPath, setSelectedNasPath] = useState("");
  const [isLoadingNasCandidates, setIsLoadingNasCandidates] = useState(false);
  const [isSavingNasPath, setIsSavingNasPath] = useState(false);
  const [isLoadingNasStatus, setIsLoadingNasStatus] = useState(false);
  const [isManualUploadModalOpen, setIsManualUploadModalOpen] = useState(false);
  const [previewDocument, setPreviewDocument] = useState<AnagraficaDocument | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [previewKind, setPreviewKind] = useState<DocumentPreviewKind>("download");
  const [previewHtml, setPreviewHtml] = useState<string | null>(null);
  const [spreadsheetPreview, setSpreadsheetPreview] = useState<SpreadsheetPreviewSheet[]>([]);
  const [textPreview, setTextPreview] = useState<string | null>(null);
  const [isAuditLogExpanded, setIsAuditLogExpanded] = useState(false);
  const [isMetadataExpanded, setIsMetadataExpanded] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [isEnableEditConfirmOpen, setIsEnableEditConfirmOpen] = useState(false);
  const [manualUploadItems, setManualUploadItems] = useState<ManualUploadItem[]>([]);
  const [isUploadingManualDocument, setIsUploadingManualDocument] = useState(false);
  const [isManualDropActive, setIsManualDropActive] = useState(false);
  const [deleteDocumentTarget, setDeleteDocumentTarget] = useState<AnagraficaDocument | null>(null);
  const [deletePassword, setDeletePassword] = useState("");
  const [isDeletingDocument, setIsDeletingDocument] = useState(false);

  const [sourceNameRaw, setSourceNameRaw] = useState("");
  const [requiresReview, setRequiresReview] = useState(false);
  const [status, setStatus] = useState("active");
  const [displayOne, setDisplayOne] = useState("");
  const [displayTwo, setDisplayTwo] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [personDetails, setPersonDetails] = useState({
    data_nascita: "",
    comune_nascita: "",
    indirizzo: "",
    comune_residenza: "",
    cap: "",
    email: "",
    telefono: "",
    note: "",
  });
  const [companyDetails, setCompanyDetails] = useState({
    codice_fiscale: "",
    sede_legale: "",
    comune_sede: "",
    cap: "",
    email_pec: "",
    telefono: "",
    note: "",
  });

  useEffect(() => {
    async function loadSubject() {
      try {
        const response = await getUtenzeSubject(token, subjectId);
        setSubject(response);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore caricamento dettaglio soggetto");
      }
    }

    void loadSubject();
  }, [subjectId, token]);

  useEffect(() => {
    if (!subject) {
      return;
    }
    setIsEditMode(false);
    setIsEnableEditConfirmOpen(false);
    setSourceNameRaw(subject.source_name_raw);
    setRequiresReview(subject.requires_review);
    setStatus(subject.status);
    setSelectedNasPath(subject.nas_folder_path || "");
    if (subject.person) {
      setDisplayOne(subject.person.cognome);
      setDisplayTwo(subject.person.nome);
      setIdentifier(subject.person.codice_fiscale);
      setPersonDetails({
        data_nascita: subject.person.data_nascita || "",
        comune_nascita: subject.person.comune_nascita || "",
        indirizzo: subject.person.indirizzo || "",
        comune_residenza: subject.person.comune_residenza || "",
        cap: subject.person.cap || "",
        email: subject.person.email || "",
        telefono: subject.person.telefono || "",
        note: subject.person.note || "",
      });
    } else if (subject.company) {
      setDisplayOne(subject.company.ragione_sociale);
      setDisplayTwo(subject.company.forma_giuridica || "");
      setIdentifier(subject.company.partita_iva);
      setCompanyDetails({
        codice_fiscale: subject.company.codice_fiscale || "",
        sede_legale: subject.company.sede_legale || "",
        comune_sede: subject.company.comune_sede || "",
        cap: subject.company.cap || "",
        email_pec: subject.company.email_pec || "",
        telefono: subject.company.telefono || "",
        note: subject.company.note || "",
      });
    }
  }, [subject]);

  useEffect(() => {
    if (!isManualUploadModalOpen) {
      setManualUploadItems([]);
    }
  }, [isManualUploadModalOpen]);

  async function reloadSubject() {
    const response = await getUtenzeSubject(token, subjectId);
    setSubject(response);
  }

  const loadNasImportStatus = useCallback(async () => {
    setIsLoadingNasStatus(true);
    try {
      const response = await getUtenzeSubjectNasImportStatus(token, subjectId);
      setNasImportStatus(response);
    } catch (error) {
      setNasImportStatus({
        can_import_from_nas: false,
        missing_in_nas: true,
        matched_folder_path: null,
        matched_folder_name: null,
        total_files_in_nas: 0,
        pending_files_in_nas: 0,
        message: error instanceof Error ? error.message : "Verifica NAS non disponibile",
      });
    } finally {
      setIsLoadingNasStatus(false);
    }
  }, [token, subjectId]);

  async function handleSave() {
    if (!subject) {
      return;
    }
    setIsSaving(true);
    setSaveError(null);
    setSaveMessage(null);

    const payload: AnagraficaSubjectUpdateInput = {
      source_name_raw: sourceNameRaw,
      requires_review: requiresReview,
      status: status as "active" | "inactive" | "duplicate",
    };

    if (subject.person) {
      payload.person = {
        cognome: displayOne,
        nome: displayTwo,
        codice_fiscale: identifier,
        data_nascita: personDetails.data_nascita || null,
        comune_nascita: personDetails.comune_nascita || null,
        indirizzo: personDetails.indirizzo || null,
        comune_residenza: personDetails.comune_residenza || null,
        cap: personDetails.cap || null,
        email: personDetails.email || null,
        telefono: personDetails.telefono || null,
        note: personDetails.note || null,
      };
    } else if (subject.company) {
      payload.company = {
        ragione_sociale: displayOne,
        forma_giuridica: displayTwo || null,
        partita_iva: identifier,
        codice_fiscale: companyDetails.codice_fiscale || null,
        sede_legale: companyDetails.sede_legale || null,
        comune_sede: companyDetails.comune_sede || null,
        cap: companyDetails.cap || null,
        email_pec: companyDetails.email_pec || null,
        telefono: companyDetails.telefono || null,
        note: companyDetails.note || null,
      };
    }

    try {
      const response = await updateUtenzeSubject(token, subjectId, payload);
      setSubject(response);
      setSaveMessage("Scheda soggetto aggiornata.");
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Errore salvataggio soggetto");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDocumentTypeChange(documentId: string, docType: string) {
    try {
      await updateUtenzeDocument(token, documentId, { doc_type: docType });
      await reloadSubject();
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Errore aggiornamento documento");
    }
  }

  async function handleImportFromNas() {
    setIsImportingFromNas(true);
    setSaveError(null);
    setSaveMessage(null);

    try {
      const result = await importUtenzeSubjectFromNas(token, subjectId);
      await reloadSubject();
      await loadNasImportStatus();
      setSaveMessage(
        `Import NAS completato da ${result.matched_folder_name}: ${result.created_documents} documenti creati, ${result.updated_documents} aggiornati.`,
      );
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Errore import documenti da NAS");
    } finally {
      setIsImportingFromNas(false);
    }
  }

  async function handleLoadNasCandidates() {
    setIsLoadingNasCandidates(true);
    setSaveError(null);
    try {
      const response = await getUtenzeSubjectNasCandidates(token, subjectId);
      setNasCandidates(response);
      if (!selectedNasPath && response[0]?.nas_folder_path) {
        setSelectedNasPath(response[0].nas_folder_path);
      }
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Errore caricamento cartelle NAS candidate");
    } finally {
      setIsLoadingNasCandidates(false);
    }
  }

  async function handleSaveNasPath() {
    if (!selectedNasPath) {
      setSaveError("Seleziona una cartella NAS da salvare.");
      return;
    }

    const selectedCandidate = nasCandidates.find((item) => item.nas_folder_path === selectedNasPath);

    setIsSavingNasPath(true);
    setSaveError(null);
    setSaveMessage(null);
    try {
      const response = await updateUtenzeSubject(token, subjectId, {
        nas_folder_path: selectedNasPath,
        nas_folder_letter: selectedCandidate?.letter ?? subject?.nas_folder_letter ?? null,
      });
      setSubject(response);
      await loadNasImportStatus();
      setSaveMessage("Percorso NAS salvato sulla scheda soggetto.");
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Errore salvataggio percorso NAS");
    } finally {
      setIsSavingNasPath(false);
    }
  }

  async function handleManualUpload() {
    if (manualUploadItems.length === 0) {
      setSaveError("Seleziona almeno un file da caricare.");
      return;
    }

    setIsUploadingManualDocument(true);
    setSaveError(null);
    setSaveMessage(null);
    try {
      for (const item of manualUploadItems) {
        await uploadUtenzeSubjectDocument(token, subjectId, item.file, item.docType, item.notes || undefined);
      }
      await reloadSubject();
      await loadNasImportStatus();
      setManualUploadItems([]);
      setIsManualUploadModalOpen(false);
      setSaveMessage(
        manualUploadItems.length === 1
          ? "Documento caricato manualmente e associato al soggetto."
          : `${manualUploadItems.length} documenti caricati manualmente e associati al soggetto.`,
      );
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Errore caricamento manuale documento");
    } finally {
      setIsUploadingManualDocument(false);
    }
  }

  async function handleDeleteDocument() {
    if (!deleteDocumentTarget?.id) {
      setSaveError("Documento non valido per la cancellazione.");
      return;
    }
    const password = deletePassword.trim();
    if (!password) {
      setSaveError("Inserisci la password per cancellare il documento.");
      return;
    }

    setIsDeletingDocument(true);
    setSaveError(null);
    setSaveMessage(null);
    try {
      await deleteUtenzeDocument(token, deleteDocumentTarget.id, password);
      await reloadSubject();
      await loadNasImportStatus();
      setDeleteDocumentTarget(null);
      setDeletePassword("");
      setSaveMessage("Documento eliminato.");
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Errore eliminazione documento");
    } finally {
      setIsDeletingDocument(false);
    }
  }

  function handleManualFilesSelection(files: FileList | null) {
    if (!files || files.length === 0) {
      return;
    }

    const newItems = Array.from(files).map((file) => ({
      id: `${file.name}-${file.lastModified}-${crypto.randomUUID()}`,
      file,
      docType: "altro",
      notes: "",
    }));

    setManualUploadItems((current) => [...current, ...newItems]);
  }

  const handleManualDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      setIsManualDropActive(false);
      handleManualFilesSelection(event.dataTransfer?.files ?? null);
    },
    [handleManualFilesSelection],
  );

  function handleManualItemChange(itemId: string, updates: Partial<Pick<ManualUploadItem, "docType" | "notes">>) {
    setManualUploadItems((current) =>
      current.map((item) => (item.id === itemId ? { ...item, ...updates } : item)),
    );
  }

  function handleManualItemRemove(itemId: string) {
    setManualUploadItems((current) => current.filter((item) => item.id !== itemId));
  }

  const closePreviewModal = useCallback(() => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setPreviewUrl(null);
    setPreviewDocument(null);
    setPreviewError(null);
    setIsLoadingPreview(false);
    setPreviewKind("download");
    setPreviewHtml(null);
    setSpreadsheetPreview([]);
    setTextPreview(null);
  }, [previewUrl]);

  async function handlePreviewDocument(document: AnagraficaDocument) {
    if (!document.id) {
      setSaveError("Il documento non ha un identificativo valido per la preview.");
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

  useEffect(() => {
    if (!subject) {
      return;
    }
    void loadNasImportStatus();
  }, [loadNasImportStatus, subject]);

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  useEffect(() => {
    if (!isManualUploadModalOpen && !previewDocument) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape") {
        return;
      }

      if (previewDocument) {
        closePreviewModal();
        return;
      }

      if (isManualUploadModalOpen) {
        setIsManualUploadModalOpen(false);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [closePreviewModal, isManualUploadModalOpen, previewDocument]);

  if (loadError) {
    return (
      <article className="panel-card">
        <p className="text-sm font-medium text-red-700">Dettaglio non disponibile</p>
        <p className="mt-2 text-sm text-gray-600">{loadError}</p>
      </article>
    );
  }

  if (!subject) {
    return <article className="panel-card text-sm text-gray-500">Caricamento scheda soggetto.</article>;
  }

  const readOnlyControlClassName = !isEditMode ? "bg-gray-50 text-gray-500" : "";

  return (
    <div className="page-stack">
      {isEnableEditConfirmOpen ? (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
            <div>
              <p className="section-title">Abilita modalità modifica</p>
              <p className="section-copy mt-2">
                La scheda soggetto è in sola lettura per default. Vuoi abilitare la modifica dei dati, dei documenti e del collegamento NAS?
              </p>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button className="btn-secondary" type="button" onClick={() => setIsEnableEditConfirmOpen(false)}>
                Annulla
              </button>
              <button
                className="btn-primary"
                type="button"
                onClick={() => {
                  setIsEditMode(true);
                  setIsEnableEditConfirmOpen(false);
                }}
              >
                Abilita modifica
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm text-gray-500">Scheda soggetto del Consorzio</p>
          <p className="text-lg font-medium text-gray-900">
            {subject.person ? `${subject.person.cognome} ${subject.person.nome}` : subject.company?.ragione_sociale || subject.source_name_raw}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className={cn("inline-flex items-center rounded-full px-3 py-2 text-xs font-medium", isEditMode ? "bg-amber-50 text-amber-700" : "bg-gray-100 text-gray-600")}>
            {isEditMode ? "Modalità modifica attiva" : "Sola lettura"}
          </span>
          {isEditMode ? (
            <button className="btn-secondary" type="button" onClick={() => setIsEditMode(false)}>
              Termina modifica
            </button>
          ) : (
            <button className="btn-primary" type="button" onClick={() => setIsEnableEditConfirmOpen(true)}>
              Modifica
            </button>
          )}
          {isEditMode && nasImportStatus?.can_import_from_nas ? (
            <button className="btn-primary" type="button" onClick={() => void handleImportFromNas()} disabled={isImportingFromNas || isLoadingNasStatus}>
              {isImportingFromNas ? "Import in corso..." : "Importa documenti da NAS"}
            </button>
          ) : null}
          {isEditMode && !nasImportStatus?.can_import_from_nas ? (
            <button className="btn-primary" type="button" onClick={() => setIsManualUploadModalOpen(true)}>
              Nessun dato rilevato nel NAS, importa manualmente
            </button>
          ) : null}
          <button className="btn-secondary" type="button" onClick={() => router.push("/utenze/subjects")}>
            Torna alla lista
          </button>
        </div>
      </div>

      {nasImportStatus ? (
        <article className="panel-card">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="section-title">Stato import NAS</p>
              <p className="section-copy">{nasImportStatus.message}</p>
            </div>
            {nasImportStatus.matched_folder_name ? (
              <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">{nasImportStatus.matched_folder_name}</span>
            ) : null}
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">File NAS</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{nasImportStatus.total_files_in_nas}</p>
            </div>
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">Da importare</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{nasImportStatus.pending_files_in_nas}</p>
            </div>
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">Percorso rilevato</p>
              <p className="mt-2 break-all text-sm text-gray-900">{nasImportStatus.matched_folder_path || "Non disponibile"}</p>
            </div>
          </div>
        </article>
      ) : null}

      {isManualUploadModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 py-6">
          <div className="flex h-full max-h-[90vh] w-full max-w-5xl flex-col rounded-2xl bg-white shadow-2xl">
            <div className="border-b border-gray-100 px-6 py-5">
              <p className="section-title">Import manuale documento</p>
              <p className="section-copy mt-2">
                Carica uno o piu file locali e categorizzali subito per associarli al soggetto.
                {subject.nas_folder_path ? " I file verranno salvati in GAIA e sincronizzati anche sul NAS nella cartella GAIA_UPLOADS." : " I file verranno salvati in GAIA; il soggetto non ha ancora una cartella NAS collegata."}
              </p>
            </div>
            <div className="flex-1 overflow-hidden px-6 py-5">
              <div className="grid h-full min-h-0 gap-4 md:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
              <div className="flex min-h-0 flex-col rounded-xl border border-gray-200 bg-gray-50 p-4">
                <p className="text-sm font-medium text-gray-900">Documenti gia associati</p>
                {subject.documents.length === 0 ? (
                  <p className="mt-2 text-sm text-gray-500">Nessun documento presente.</p>
                ) : (
                  <div className="mt-3 min-h-0 flex-1 space-y-2 overflow-auto pr-1">
                    {subject.documents.map((document) => (
                      <div key={document.id || document.nas_path} className="rounded-lg border border-gray-200 bg-white px-3 py-2">
                        <div className="flex items-center justify-between gap-3">
                          <p className="truncate text-sm font-medium text-gray-900">{document.filename}</p>
                          <span className="rounded-full bg-gray-100 px-2 py-1 text-[11px] font-medium text-gray-700">{document.doc_type}</span>
                        </div>
                        <p className="mt-1 truncate text-xs text-gray-500">{document.nas_path}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex min-h-0 flex-col space-y-4">
                <div className="space-y-2">
                  <p className="text-sm font-medium text-gray-700">File</p>
                  <div
                    className={cn(
                      "relative rounded-xl border border-dashed bg-gray-50 px-4 py-6 transition",
                      isManualDropActive ? "border-[#1D4E35] bg-[#1D4E35]/5" : "border-gray-200 hover:bg-gray-100/60",
                      isUploadingManualDocument ? "pointer-events-none opacity-60" : "cursor-pointer",
                    )}
                    role="button"
                    tabIndex={0}
                    onClick={() => manualFileInputRef.current?.click()}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        manualFileInputRef.current?.click();
                      }
                    }}
                    onDragEnter={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      setIsManualDropActive(true);
                    }}
                    onDragOver={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      setIsManualDropActive(true);
                    }}
                    onDragLeave={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      setIsManualDropActive(false);
                    }}
                    onDrop={handleManualDrop}
                    aria-label="Trascina qui i file o clicca per selezionarli"
                  >
                    <div className="text-center">
                      <p className="text-sm font-medium text-gray-900">
                        Trascina qui i file oppure clicca per selezionarli
                      </p>
                      <p className="mt-1 text-xs text-gray-500">Puoi selezionare piu file e classificarli singolarmente prima del caricamento.</p>
                    </div>
                    <input
                      ref={manualFileInputRef}
                      className="sr-only"
                      type="file"
                      multiple
                      onChange={(event) => {
                        handleManualFilesSelection(event.target.files);
                        event.target.value = "";
                      }}
                    />
                  </div>
                </div>
                {manualUploadItems.length === 0 ? (
                  <div className="grid min-h-[14rem] place-items-center rounded-xl border border-dashed border-gray-200 bg-gray-50 px-4 py-8 text-center text-sm text-gray-500">
                    Nessun file selezionato. Puoi scegliere piu file e classificarli singolarmente prima del caricamento.
                  </div>
                ) : (
                  <div className="min-h-0 flex-1 space-y-3 overflow-auto pr-1">
                    {manualUploadItems.map((item, index) => (
                      <div key={item.id} className="rounded-xl border border-gray-200 bg-white p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <p className="truncate text-sm font-medium text-gray-900">{item.file.name}</p>
                            <p className="mt-1 text-xs text-gray-500">
                              File {index + 1} · {(item.file.size / 1024 / 1024).toFixed(2)} MB
                            </p>
                          </div>
                          <button
                            className="text-sm font-medium text-red-600 transition hover:text-red-700"
                            type="button"
                            onClick={() => handleManualItemRemove(item.id)}
                            disabled={isUploadingManualDocument}
                          >
                            Rimuovi
                          </button>
                        </div>
                        <div className="mt-4 space-y-4">
                          <label className="block text-sm font-medium text-gray-700">
                            Categoria documento
                            <select
                              className="form-control mt-1"
                              value={item.docType}
                              onChange={(event) => handleManualItemChange(item.id, { docType: event.target.value })}
                              disabled={isUploadingManualDocument}
                            >
                              {DOCUMENT_TYPE_OPTIONS.map((option) => (
                                <option key={option.value} value={option.value}>
                                  {option.label}
                                </option>
                              ))}
                            </select>
                          </label>
                            <label className="block text-sm font-medium text-gray-700">
                              Note
                              <textarea
                                className="form-textarea mt-1 min-h-24"
                                value={item.notes}
                                onChange={(event) => handleManualItemChange(item.id, { notes: event.target.value })}
                                disabled={isUploadingManualDocument}
                              />
                          </label>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
            </div>
            <div className="flex justify-end gap-3 border-t border-gray-100 px-6 py-4">
              <button
                className="btn-secondary"
                type="button"
                onClick={() => {
                  setManualUploadItems([]);
                  setIsManualUploadModalOpen(false);
                }}
                disabled={isUploadingManualDocument}
              >
                Annulla
              </button>
              <button className="btn-primary" type="button" onClick={() => void handleManualUpload()} disabled={isUploadingManualDocument}>
                {isUploadingManualDocument ? "Caricamento..." : manualUploadItems.length > 1 ? `Carica ${manualUploadItems.length} documenti` : "Carica documento"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {deleteDocumentTarget ? (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/50 px-4 py-6">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
            <div>
              <p className="section-title">Cancellazione documento</p>
              <p className="section-copy mt-2">
                Stai per eliminare <span className="font-medium text-gray-900">{deleteDocumentTarget.filename}</span>. Inserisci la password per continuare.
              </p>
            </div>
            <div className="mt-5 space-y-4">
              <label className="block text-sm font-medium text-gray-700">
                Password
                <input
                  className="form-control mt-1"
                  type="password"
                  value={deletePassword}
                  onChange={(event) => setDeletePassword(event.target.value)}
                  disabled={isDeletingDocument}
                  autoFocus
                />
              </label>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button
                className="btn-secondary"
                type="button"
                onClick={() => {
                  setDeleteDocumentTarget(null);
                  setDeletePassword("");
                }}
                disabled={isDeletingDocument}
              >
                Annulla
              </button>
              <button className="btn-primary" type="button" onClick={() => void handleDeleteDocument()} disabled={isDeletingDocument}>
                {isDeletingDocument ? "Eliminazione..." : "Elimina"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {previewDocument ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4 py-6">
          <div className="flex h-full max-h-[92vh] w-full max-w-5xl flex-col rounded-2xl bg-white shadow-2xl">
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
                    <div
                      className="prose prose-sm max-w-none text-gray-700"
                      dangerouslySetInnerHTML={{ __html: previewHtml }}
                    />
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

      <article className="panel-card">
          <div className="mb-4">
            <p className="section-title">Scheda anagrafica</p>
            <p className="section-copy">Dati principali e stato operativo del soggetto selezionato.</p>
          </div>
          {saveError ? <p className="mb-3 text-sm text-red-600">{saveError}</p> : null}
          {saveMessage ? <p className="mb-3 text-sm text-[#1D4E35]">{saveMessage}</p> : null}
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block text-sm font-medium text-gray-700 md:col-span-2">
              Source name raw
              <input className={cn("form-control mt-1", readOnlyControlClassName)} value={sourceNameRaw} onChange={(event) => setSourceNameRaw(event.target.value)} readOnly={!isEditMode} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              {subject.person ? "Cognome / ragione sociale" : "Ragione sociale"}
              <input className={cn("form-control mt-1", readOnlyControlClassName)} value={displayOne} onChange={(event) => setDisplayOne(event.target.value)} readOnly={!isEditMode} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              {subject.person ? "Nome" : "Forma giuridica"}
              <input className={cn("form-control mt-1", readOnlyControlClassName)} value={displayTwo} onChange={(event) => setDisplayTwo(event.target.value)} readOnly={!isEditMode} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              {subject.person ? "Codice fiscale" : "Partita IVA"}
              <input className={cn("form-control mt-1", readOnlyControlClassName)} value={identifier} onChange={(event) => setIdentifier(event.target.value)} readOnly={!isEditMode} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Stato
              <select className={cn("form-control mt-1", readOnlyControlClassName)} value={status} onChange={(event) => setStatus(event.target.value)} disabled={!isEditMode}>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="duplicate">Duplicate</option>
              </select>
            </label>
            <label className="flex items-center gap-3 text-sm font-medium text-gray-700 md:col-span-2">
              <input checked={requiresReview} onChange={(event) => setRequiresReview(event.target.checked)} type="checkbox" disabled={!isEditMode} />
              Richiede revisione
            </label>

            {subject.person ? (
              <>
                <label className="block text-sm font-medium text-gray-700">
                  Data nascita
                  <input
                    className={cn("form-control mt-1", readOnlyControlClassName)}
                    type="date"
                    value={personDetails.data_nascita}
                    onChange={(event) => setPersonDetails((current) => ({ ...current, data_nascita: event.target.value }))}
                    readOnly={!isEditMode}
                  />
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  Comune nascita
                  <input
                    className={cn("form-control mt-1", readOnlyControlClassName)}
                    value={personDetails.comune_nascita}
                    onChange={(event) => setPersonDetails((current) => ({ ...current, comune_nascita: event.target.value }))}
                    readOnly={!isEditMode}
                  />
                </label>
                <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                  Indirizzo
                  <input
                    className={cn("form-control mt-1", readOnlyControlClassName)}
                    value={personDetails.indirizzo}
                    onChange={(event) => setPersonDetails((current) => ({ ...current, indirizzo: event.target.value }))}
                    readOnly={!isEditMode}
                  />
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  Comune residenza
                  <input
                    className={cn("form-control mt-1", readOnlyControlClassName)}
                    value={personDetails.comune_residenza}
                    onChange={(event) => setPersonDetails((current) => ({ ...current, comune_residenza: event.target.value }))}
                    readOnly={!isEditMode}
                  />
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  CAP
                  <input
                    className={cn("form-control mt-1", readOnlyControlClassName)}
                    value={personDetails.cap}
                    onChange={(event) => setPersonDetails((current) => ({ ...current, cap: event.target.value }))}
                    readOnly={!isEditMode}
                  />
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  Email
                  <input
                    className={cn("form-control mt-1", readOnlyControlClassName)}
                    type="email"
                    value={personDetails.email}
                    onChange={(event) => setPersonDetails((current) => ({ ...current, email: event.target.value }))}
                    readOnly={!isEditMode}
                  />
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  Telefono
                  <input
                    className={cn("form-control mt-1", readOnlyControlClassName)}
                    value={personDetails.telefono}
                    onChange={(event) => setPersonDetails((current) => ({ ...current, telefono: event.target.value }))}
                    readOnly={!isEditMode}
                  />
                </label>
                <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                  Note
                  <textarea
                    className={cn("form-textarea mt-1 min-h-24", !isEditMode ? "bg-gray-50 text-gray-500" : "")}
                    value={personDetails.note}
                    onChange={(event) => setPersonDetails((current) => ({ ...current, note: event.target.value }))}
                    readOnly={!isEditMode}
                  />
                </label>
              </>
            ) : null}

            {subject.company ? (
              <>
                <label className="block text-sm font-medium text-gray-700">
                  Codice fiscale
                  <input
                    className={cn("form-control mt-1", readOnlyControlClassName)}
                    value={companyDetails.codice_fiscale}
                    onChange={(event) => setCompanyDetails((current) => ({ ...current, codice_fiscale: event.target.value }))}
                    readOnly={!isEditMode}
                  />
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  Telefono
                  <input
                    className={cn("form-control mt-1", readOnlyControlClassName)}
                    value={companyDetails.telefono}
                    onChange={(event) => setCompanyDetails((current) => ({ ...current, telefono: event.target.value }))}
                    readOnly={!isEditMode}
                  />
                </label>
                <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                  Sede legale
                  <input
                    className={cn("form-control mt-1", readOnlyControlClassName)}
                    value={companyDetails.sede_legale}
                    onChange={(event) => setCompanyDetails((current) => ({ ...current, sede_legale: event.target.value }))}
                    readOnly={!isEditMode}
                  />
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  Comune sede
                  <input
                    className={cn("form-control mt-1", readOnlyControlClassName)}
                    value={companyDetails.comune_sede}
                    onChange={(event) => setCompanyDetails((current) => ({ ...current, comune_sede: event.target.value }))}
                    readOnly={!isEditMode}
                  />
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  CAP
                  <input
                    className={cn("form-control mt-1", readOnlyControlClassName)}
                    value={companyDetails.cap}
                    onChange={(event) => setCompanyDetails((current) => ({ ...current, cap: event.target.value }))}
                    readOnly={!isEditMode}
                  />
                </label>
                <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                  PEC / Email
                  <input
                    className={cn("form-control mt-1", readOnlyControlClassName)}
                    type="email"
                    value={companyDetails.email_pec}
                    onChange={(event) => setCompanyDetails((current) => ({ ...current, email_pec: event.target.value }))}
                    readOnly={!isEditMode}
                  />
                </label>
                <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                  Note
                  <textarea
                    className={cn("form-textarea mt-1 min-h-24", !isEditMode ? "bg-gray-50 text-gray-500" : "")}
                    value={companyDetails.note}
                    onChange={(event) => setCompanyDetails((current) => ({ ...current, note: event.target.value }))}
                    readOnly={!isEditMode}
                  />
                </label>
              </>
            ) : null}
          </div>
          <div className="mt-4 flex justify-end">
            <button className="btn-primary" onClick={() => void handleSave()} type="button" disabled={!isEditMode || isSaving}>
              {isSaving ? "Salvataggio..." : "Salva scheda"}
            </button>
          </div>
      </article>

      <article className="panel-card">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
          <p className="section-title">Documenti associati</p>
          <p className="section-copy">Classificazione manuale e upload dal catalogo GAIA.</p>
          </div>
          {isEditMode ? (
            <button className="btn-secondary" type="button" onClick={() => setIsManualUploadModalOpen(true)}>
              Inserisci file
            </button>
          ) : null}
        </div>
        {subject.documents.length === 0 ? (
          <p className="text-sm text-gray-500">Nessun documento associato.</p>
        ) : (
          <div className="space-y-3">
            {subject.documents.map((document) => (
              <div
                key={document.id || document.nas_path}
                className="cursor-pointer rounded-lg border border-gray-100 px-4 py-3 transition hover:bg-gray-50"
                onClick={() => void handlePreviewDocument(document)}
                role="button"
                tabIndex={0}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    void handlePreviewDocument(document);
                  }
                }}
              >
                <div className="grid gap-3 md:grid-cols-[1.3fr_0.7fr_0.7fr_auto] md:items-center">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{document.filename}</p>
                    <p className="mt-1 break-all text-xs text-gray-500">{document.nas_path}</p>
                  </div>
                  <select
                    className={cn("form-control", readOnlyControlClassName)}
                    value={document.doc_type}
                    onClick={(event) => event.stopPropagation()}
                    onChange={(event) => {
                      if (document.id) {
                        void handleDocumentTypeChange(document.id, event.target.value);
                      }
                    }}
                    disabled={!isEditMode}
                  >
                    <option value="ingiunzione">Ingiunzione</option>
                    <option value="notifica">Notifica</option>
                    <option value="estratto_debito">Estratto debito</option>
                    <option value="pratica_interna">Pratica interna</option>
                    <option value="visura">Visura</option>
                    <option value="corrispondenza">Corrispondenza</option>
                    <option value="contratto">Contratto</option>
                    <option value="altro">Altro</option>
                  </select>
                  <span className="text-sm text-gray-500">{document.classification_source}</span>
                  <div className="flex items-center justify-end gap-3">
                    <button
                      className="text-sm font-medium text-[#1D4E35] transition hover:text-[#163a29]"
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        void handlePreviewDocument(document);
                      }}
                    >
                      Preview
                    </button>
                    {isEditMode && document.id ? (
                      <button
                        className="text-sm font-medium text-red-600 transition hover:text-red-700"
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          setSaveError(null);
                          setSaveMessage(null);
                          setDeleteDocumentTarget(document);
                          setDeletePassword("");
                        }}
                      >
                        Rimuovi
                      </button>
                    ) : null}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </article>

      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Correlazioni Catasto</p>
          <p className="section-copy">Visure e documenti Catasto correlati in sola lettura tramite codice fiscale.</p>
        </div>
        {subject.catasto_documents.length === 0 ? (
          <p className="text-sm text-gray-500">Nessuna correlazione Catasto disponibile per questo soggetto.</p>
        ) : (
          <div className="space-y-3">
            {subject.catasto_documents.map((item) => (
              <div key={item.id} className="rounded-lg border border-gray-100 px-4 py-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium text-gray-900">{item.filename}</p>
                  <span className="text-xs text-gray-400">{formatDateTime(item.created_at)}</span>
                </div>
                <p className="mt-2 text-sm text-gray-600">
                  {item.comune} · Fg. {item.foglio} · Part. {item.particella}
                  {item.subalterno ? ` · Sub. ${item.subalterno}` : ""}
                </p>
                <p className="mt-1 text-xs text-gray-500">
                  {item.catasto} · {item.tipo_visura} · {item.codice_fiscale || "CF non disponibile"}
                </p>
              </div>
            ))}
          </div>
        )}
      </article>

      <article className="panel-card">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="section-title">Override cartella NAS</p>
            <p className="section-copy">Carica le cartelle candidate trovate per lettera archivio, seleziona quella corretta e salvala sulla scheda.</p>
          </div>
          <button className="btn-secondary" type="button" onClick={() => void handleLoadNasCandidates()} disabled={!isEditMode || isLoadingNasCandidates}>
            {isLoadingNasCandidates ? "Ricerca cartelle..." : "Trova cartelle candidate"}
          </button>
        </div>

        <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
          <div className="space-y-3">
            <label className="block text-sm font-medium text-gray-700">
              Percorso NAS selezionato
              <input
                className={cn("form-control mt-1", readOnlyControlClassName)}
                value={selectedNasPath}
                onChange={(event) => setSelectedNasPath(event.target.value)}
                placeholder="/volume1/.../CartellaSoggetto"
                readOnly={!isEditMode}
              />
            </label>
            <div className="flex justify-end">
              <button className="btn-primary" type="button" onClick={() => void handleSaveNasPath()} disabled={!isEditMode || isSavingNasPath}>
                {isSavingNasPath ? "Salvataggio..." : "Salva percorso NAS"}
              </button>
            </div>
          </div>

          <div>
            {nasCandidates.length === 0 ? (
              <p className="text-sm text-gray-500">Nessuna cartella candidata caricata. Avvia la ricerca per vedere le opzioni trovate sul NAS.</p>
            ) : (
              <div className="space-y-3">
                {nasCandidates.map((candidate) => (
                  <label key={candidate.nas_folder_path} className={cn("flex gap-3 rounded-lg border border-gray-100 px-4 py-3 transition", isEditMode ? "cursor-pointer hover:bg-gray-50" : "cursor-default bg-gray-50/50")}>
                    <input
                      type="radio"
                      name="nas-candidate"
                      checked={selectedNasPath === candidate.nas_folder_path}
                      onChange={() => setSelectedNasPath(candidate.nas_folder_path)}
                      disabled={!isEditMode}
                    />
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-medium text-gray-900">{candidate.folder_name}</p>
                        <span className="rounded-full bg-gray-100 px-2 py-1 text-[11px] font-medium text-gray-700">score {candidate.score}</span>
                        <span className="rounded-full bg-sky-50 px-2 py-1 text-[11px] font-medium text-sky-700">{candidate.subject_type}</span>
                      </div>
                      <p className="mt-1 break-all text-xs text-gray-500">{candidate.nas_folder_path}</p>
                      <p className="mt-2 text-xs text-gray-500">
                        confidenza {Math.round(candidate.confidence * 100)}% · {candidate.codice_fiscale || candidate.partita_iva || "identificativo non disponibile"} · review {candidate.requires_review ? "si" : "no"}
                      </p>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>
        </div>
      </article>

      <article className="panel-card">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="section-title">Audit log</p>
            <p className="section-copy">Tracce minime delle operazioni effettuate sul soggetto.</p>
          </div>
          <button className="btn-secondary" type="button" onClick={() => setIsAuditLogExpanded((current) => !current)}>
            {isAuditLogExpanded ? "Riduci" : "Espandi"}
          </button>
        </div>
        {!isAuditLogExpanded ? (
          <p className="mt-4 text-sm text-gray-500">
            Audit log ridotto di default. {subject.audit_log.length === 0 ? "Nessun evento registrato." : `${subject.audit_log.length} eventi disponibili.`}
          </p>
        ) : subject.audit_log.length === 0 ? (
          <p className="mt-4 text-sm text-gray-500">Nessun evento registrato.</p>
        ) : (
          <div className="mt-4 space-y-3">
            {subject.audit_log.map((item) => (
              <div key={item.id} className="rounded-lg border border-gray-100 px-4 py-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium text-gray-900">{item.action}</p>
                  <span className="text-xs text-gray-400">{formatDateTime(item.changed_at)}</span>
                </div>
                <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs text-gray-500">
                  {JSON.stringify(item.diff_json, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        )}
      </article>

      <article className="panel-card">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="section-title">Metadati archivio</p>
            <p className="section-copy">Informazioni tecniche sul collegamento NAS e sullo stato archivistico del soggetto.</p>
          </div>
          <button className="btn-secondary" type="button" onClick={() => setIsMetadataExpanded((current) => !current)}>
            {isMetadataExpanded ? "Riduci" : "Espandi"}
          </button>
        </div>
        {!isMetadataExpanded ? (
          <p className="mt-4 text-sm text-gray-500">
            Metadati ridotti di default. {subject.nas_folder_path ? "Percorso NAS collegato disponibile." : "Nessun percorso NAS collegato."}
          </p>
        ) : (
          <dl className="mt-5 grid gap-4 md:grid-cols-2">
            <div>
              <dt className="label-caption">Tipo soggetto</dt>
              <dd className="mt-1 text-sm text-gray-800">{subject.subject_type}</dd>
            </div>
            <div>
              <dt className="label-caption">Lettera archivio</dt>
              <dd className="mt-1 text-sm text-gray-800">{subject.nas_folder_letter || "—"}</dd>
            </div>
            <div className="md:col-span-2">
              <dt className="label-caption">Percorso NAS</dt>
              <dd className="mt-1 break-all text-sm text-gray-800">{subject.nas_folder_path || "—"}</dd>
            </div>
            <div>
              <dt className="label-caption">Importato il</dt>
              <dd className="mt-1 text-sm text-gray-800">{formatDateTime(subject.imported_at)}</dd>
            </div>
            <div>
              <dt className="label-caption">Aggiornato il</dt>
              <dd className="mt-1 text-sm text-gray-800">{formatDateTime(subject.updated_at)}</dd>
            </div>
            <div>
              <dt className="label-caption">Creato il</dt>
              <dd className="mt-1 text-sm text-gray-800">{formatDateTime(subject.created_at)}</dd>
            </div>
            <div>
              <dt className="label-caption">Richiede revisione</dt>
              <dd className="mt-1 text-sm text-gray-800">{subject.requires_review ? "Si" : "No"}</dd>
            </div>
          </dl>
        )}
      </article>
    </div>
  );
}

export default function UtenzeSubjectDetailPage() {
  const params = useParams<{ id: string }>();
  return (
    <UtenzeModulePage
      title="Dettaglio soggetto"
      description="Scheda utenza completa del soggetto, documenti associati e audit log."
      breadcrumb={params.id}
    >
      {({ token }) => <DetailContent token={token} subjectId={params.id} />}
    </UtenzeModulePage>
  );
}
