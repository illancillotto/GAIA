"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AnagraficaModulePage } from "@/components/anagrafica/anagrafica-module-page";
import {
  deleteAnagraficaDocument,
  downloadAnagraficaDocumentBlob,
  getAnagraficaSubjectNasCandidates,
  getAnagraficaSubjectNasImportStatus,
  getAnagraficaSubject,
  importAnagraficaSubjectFromNas,
  updateAnagraficaDocument,
  updateAnagraficaSubject,
  uploadAnagraficaSubjectDocument,
} from "@/lib/api";
import { formatDateTime } from "@/lib/presentation";
import type {
  AnagraficaDocument,
  AnagraficaNasFolderCandidate,
  AnagraficaSubjectDetail,
  AnagraficaSubjectNasImportStatus,
  AnagraficaSubjectUpdateInput,
} from "@/types/api";

function DetailContent({ token, subjectId }: { token: string; subjectId: string }) {
  const router = useRouter();
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
  const [documentPendingDeletion, setDocumentPendingDeletion] = useState<AnagraficaDocument | null>(null);
  const [isDeletingDocument, setIsDeletingDocument] = useState(false);
  const [manualFile, setManualFile] = useState<File | null>(null);
  const [manualDocType, setManualDocType] = useState("altro");
  const [manualNotes, setManualNotes] = useState("");
  const [isUploadingManualDocument, setIsUploadingManualDocument] = useState(false);

  const [sourceNameRaw, setSourceNameRaw] = useState("");
  const [requiresReview, setRequiresReview] = useState(false);
  const [status, setStatus] = useState("active");
  const [displayOne, setDisplayOne] = useState("");
  const [displayTwo, setDisplayTwo] = useState("");
  const [identifier, setIdentifier] = useState("");

  useEffect(() => {
    async function loadSubject() {
      try {
        const response = await getAnagraficaSubject(token, subjectId);
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
    setSourceNameRaw(subject.source_name_raw);
    setRequiresReview(subject.requires_review);
    setStatus(subject.status);
    setSelectedNasPath(subject.nas_folder_path || "");
    if (subject.person) {
      setDisplayOne(subject.person.cognome);
      setDisplayTwo(subject.person.nome);
      setIdentifier(subject.person.codice_fiscale);
    } else if (subject.company) {
      setDisplayOne(subject.company.ragione_sociale);
      setDisplayTwo(subject.company.forma_giuridica || "");
      setIdentifier(subject.company.partita_iva);
    }
  }, [subject]);

  async function reloadSubject() {
    const response = await getAnagraficaSubject(token, subjectId);
    setSubject(response);
  }

  const loadNasImportStatus = useCallback(async () => {
    setIsLoadingNasStatus(true);
    try {
      const response = await getAnagraficaSubjectNasImportStatus(token, subjectId);
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
        data_nascita: subject.person.data_nascita,
        comune_nascita: subject.person.comune_nascita,
        indirizzo: subject.person.indirizzo,
        comune_residenza: subject.person.comune_residenza,
        cap: subject.person.cap,
        email: subject.person.email,
        telefono: subject.person.telefono,
        note: subject.person.note,
      };
    } else if (subject.company) {
      payload.company = {
        ragione_sociale: displayOne,
        forma_giuridica: displayTwo || null,
        partita_iva: identifier,
        codice_fiscale: subject.company.codice_fiscale,
        sede_legale: subject.company.sede_legale,
        comune_sede: subject.company.comune_sede,
        cap: subject.company.cap,
        email_pec: subject.company.email_pec,
        telefono: subject.company.telefono,
        note: subject.company.note,
      };
    }

    try {
      const response = await updateAnagraficaSubject(token, subjectId, payload);
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
      await updateAnagraficaDocument(token, documentId, { doc_type: docType });
      await reloadSubject();
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Errore aggiornamento documento");
    }
  }

  async function handleDeleteDocument(documentId: string) {
    setIsDeletingDocument(true);
    try {
      await deleteAnagraficaDocument(token, documentId);
      await reloadSubject();
      setDocumentPendingDeletion(null);
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Errore rimozione documento");
    } finally {
      setIsDeletingDocument(false);
    }
  }

  async function handleImportFromNas() {
    setIsImportingFromNas(true);
    setSaveError(null);
    setSaveMessage(null);

    try {
      const result = await importAnagraficaSubjectFromNas(token, subjectId);
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
      const response = await getAnagraficaSubjectNasCandidates(token, subjectId);
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
      const response = await updateAnagraficaSubject(token, subjectId, {
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
    if (!manualFile) {
      setSaveError("Seleziona un file da caricare.");
      return;
    }

    setIsUploadingManualDocument(true);
    setSaveError(null);
    setSaveMessage(null);
    try {
      await uploadAnagraficaSubjectDocument(token, subjectId, manualFile, manualDocType, manualNotes || undefined);
      await reloadSubject();
      await loadNasImportStatus();
      setManualFile(null);
      setManualDocType("altro");
      setManualNotes("");
      setIsManualUploadModalOpen(false);
      setSaveMessage("Documento caricato manualmente e associato al soggetto.");
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Errore caricamento manuale documento");
    } finally {
      setIsUploadingManualDocument(false);
    }
  }

  function closePreviewModal() {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setPreviewUrl(null);
    setPreviewDocument(null);
    setPreviewError(null);
    setIsLoadingPreview(false);
  }

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

    try {
      const blob = await downloadAnagraficaDocumentBlob(token, document.id);
      const objectUrl = URL.createObjectURL(blob);
      setPreviewUrl(objectUrl);
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

  return (
    <div className="page-stack">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm text-gray-500">Scheda soggetto del Consorzio</p>
          <p className="text-lg font-medium text-gray-900">
            {subject.person ? `${subject.person.cognome} ${subject.person.nome}` : subject.company?.ragione_sociale || subject.source_name_raw}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {nasImportStatus?.can_import_from_nas ? (
            <button className="btn-primary" type="button" onClick={() => void handleImportFromNas()} disabled={isImportingFromNas || isLoadingNasStatus}>
              {isImportingFromNas ? "Import in corso..." : "Importa documenti da NAS"}
            </button>
          ) : (
            <button className="btn-primary" type="button" onClick={() => setIsManualUploadModalOpen(true)}>
              Nessun dato rilevato nel NAS, importa manualmente
            </button>
          )}
          <button className="btn-secondary" type="button" onClick={() => router.push("/anagrafica/subjects")}>
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-2xl">
            <div className="mb-4">
              <p className="section-title">Import manuale documento</p>
              <p className="section-copy mt-2">Carica un file locale e categorizzalo subito per associarlo al soggetto.</p>
            </div>
            <div className="mb-4 rounded-xl border border-gray-200 bg-gray-50 p-4">
              <p className="text-sm font-medium text-gray-900">Documenti gia associati</p>
              {subject.documents.length === 0 ? (
                <p className="mt-2 text-sm text-gray-500">Nessun documento presente.</p>
              ) : (
                <div className="mt-3 space-y-2">
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
            <div className="space-y-4">
              <label className="block text-sm font-medium text-gray-700">
                File
                <input
                  className="form-control mt-1"
                  type="file"
                  onChange={(event) => setManualFile(event.target.files?.[0] ?? null)}
                />
              </label>
              <label className="block text-sm font-medium text-gray-700">
                Categoria documento
                <select className="form-control mt-1" value={manualDocType} onChange={(event) => setManualDocType(event.target.value)}>
                  <option value="ingiunzione">Ingiunzione</option>
                  <option value="notifica">Notifica</option>
                  <option value="estratto_debito">Estratto debito</option>
                  <option value="pratica_interna">Pratica interna</option>
                  <option value="visura">Visura</option>
                  <option value="corrispondenza">Corrispondenza</option>
                  <option value="contratto">Contratto</option>
                  <option value="altro">Altro</option>
                </select>
              </label>
              <label className="block text-sm font-medium text-gray-700">
                Note
                <textarea className="form-control mt-1 min-h-24" value={manualNotes} onChange={(event) => setManualNotes(event.target.value)} />
              </label>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button className="btn-secondary" type="button" onClick={() => setIsManualUploadModalOpen(false)} disabled={isUploadingManualDocument}>
                Annulla
              </button>
              <button className="btn-primary" type="button" onClick={() => void handleManualUpload()} disabled={isUploadingManualDocument}>
                {isUploadingManualDocument ? "Caricamento..." : "Carica documento"}
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
              {!isLoadingPreview && !previewError && previewUrl && previewDocument.is_pdf ? (
                <iframe className="h-full min-h-[70vh] w-full rounded-xl border border-gray-200" src={previewUrl} title={previewDocument.filename} />
              ) : null}
              {!isLoadingPreview && !previewError && previewUrl && !previewDocument.is_pdf ? (
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

      {documentPendingDeletion ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
            <div>
              <p className="section-title">Conferma rimozione documento</p>
              <p className="section-copy mt-2">
                Stai per rimuovere <span className="font-medium text-gray-900">{documentPendingDeletion.filename}</span> dai documenti associati.
              </p>
              <p className="mt-3 text-sm text-gray-500">L&apos;operazione rimuove il documento dal catalogo GAIA del soggetto corrente.</p>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button
                className="btn-secondary"
                type="button"
                onClick={() => setDocumentPendingDeletion(null)}
                disabled={isDeletingDocument}
              >
                Annulla
              </button>
              <button
                className="rounded-full bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60"
                type="button"
                onClick={() => {
                  if (documentPendingDeletion.id) {
                    void handleDeleteDocument(documentPendingDeletion.id);
                  }
                }}
                disabled={isDeletingDocument}
              >
                {isDeletingDocument ? "Rimozione..." : "Conferma rimozione"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
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
              <input className="form-control mt-1" value={sourceNameRaw} onChange={(event) => setSourceNameRaw(event.target.value)} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              {subject.person ? "Cognome / ragione sociale" : "Ragione sociale"}
              <input className="form-control mt-1" value={displayOne} onChange={(event) => setDisplayOne(event.target.value)} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              {subject.person ? "Nome" : "Forma giuridica"}
              <input className="form-control mt-1" value={displayTwo} onChange={(event) => setDisplayTwo(event.target.value)} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              {subject.person ? "Codice fiscale" : "Partita IVA"}
              <input className="form-control mt-1" value={identifier} onChange={(event) => setIdentifier(event.target.value)} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Stato
              <select className="form-control mt-1" value={status} onChange={(event) => setStatus(event.target.value)}>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="duplicate">Duplicate</option>
              </select>
            </label>
            <label className="flex items-center gap-3 text-sm font-medium text-gray-700 md:col-span-2">
              <input checked={requiresReview} onChange={(event) => setRequiresReview(event.target.checked)} type="checkbox" />
              Richiede revisione
            </label>
          </div>
          <div className="mt-4 flex justify-end">
            <button className="btn-primary" onClick={() => void handleSave()} type="button" disabled={isSaving}>
              {isSaving ? "Salvataggio..." : "Salva scheda"}
            </button>
          </div>
        </article>

        <article className="panel-card">
          <p className="section-title">Metadati archivio</p>
          <dl className="mt-5 space-y-4">
            <div>
              <dt className="label-caption">Tipo soggetto</dt>
              <dd className="mt-1 text-sm text-gray-800">{subject.subject_type}</dd>
            </div>
            <div>
              <dt className="label-caption">Lettera archivio</dt>
              <dd className="mt-1 text-sm text-gray-800">{subject.nas_folder_letter || "—"}</dd>
            </div>
            <div>
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
          </dl>
        </article>
      </div>

      <article className="panel-card">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="section-title">Override cartella NAS</p>
            <p className="section-copy">Carica le cartelle candidate trovate per lettera archivio, seleziona quella corretta e salvala sulla scheda.</p>
          </div>
          <button className="btn-secondary" type="button" onClick={() => void handleLoadNasCandidates()} disabled={isLoadingNasCandidates}>
            {isLoadingNasCandidates ? "Ricerca cartelle..." : "Trova cartelle candidate"}
          </button>
        </div>

        <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
          <div className="space-y-3">
            <label className="block text-sm font-medium text-gray-700">
              Percorso NAS selezionato
              <input
                className="form-control mt-1"
                value={selectedNasPath}
                onChange={(event) => setSelectedNasPath(event.target.value)}
                placeholder="/volume1/.../CartellaSoggetto"
              />
            </label>
            <div className="flex justify-end">
              <button className="btn-primary" type="button" onClick={() => void handleSaveNasPath()} disabled={isSavingNasPath}>
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
                  <label key={candidate.nas_folder_path} className="flex cursor-pointer gap-3 rounded-lg border border-gray-100 px-4 py-3 transition hover:bg-gray-50">
                    <input
                      type="radio"
                      name="nas-candidate"
                      checked={selectedNasPath === candidate.nas_folder_path}
                      onChange={() => setSelectedNasPath(candidate.nas_folder_path)}
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
        <div className="mb-4">
          <p className="section-title">Documenti associati</p>
          <p className="section-copy">Classificazione manuale e rimozione dal catalogo GAIA.</p>
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
                    className="form-control"
                    value={document.doc_type}
                    onClick={(event) => event.stopPropagation()}
                    onChange={(event) => {
                      if (document.id) {
                        void handleDocumentTypeChange(document.id, event.target.value);
                      }
                    }}
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
                    <button
                      className="text-sm font-medium text-red-600 transition hover:text-red-700"
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        setDocumentPendingDeletion(document);
                      }}
                    >
                      Rimuovi
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </article>

      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Audit log</p>
          <p className="section-copy">Tracce minime delle operazioni effettuate sul soggetto.</p>
        </div>
        {subject.audit_log.length === 0 ? (
          <p className="text-sm text-gray-500">Nessun evento registrato.</p>
        ) : (
          <div className="space-y-3">
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
    </div>
  );
}

export default function AnagraficaSubjectDetailPage() {
  const params = useParams<{ id: string }>();
  return (
    <AnagraficaModulePage
      title="Dettaglio soggetto"
      description="Scheda anagrafica completa del soggetto, documenti associati e audit log."
      breadcrumb={params.id}
    >
      {({ token }) => <DetailContent token={token} subjectId={params.id} />}
    </AnagraficaModulePage>
  );
}
