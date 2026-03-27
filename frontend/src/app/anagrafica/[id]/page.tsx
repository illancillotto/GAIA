"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AnagraficaModulePage } from "@/components/anagrafica/anagrafica-module-page";
import { deleteAnagraficaDocument, getAnagraficaSubject, updateAnagraficaDocument, updateAnagraficaSubject } from "@/lib/api";
import { formatDateTime } from "@/lib/presentation";
import type { AnagraficaSubjectDetail, AnagraficaSubjectUpdateInput } from "@/types/api";

function DetailContent({ token, subjectId }: { token: string; subjectId: string }) {
  const router = useRouter();
  const [subject, setSubject] = useState<AnagraficaSubjectDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

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
    try {
      await deleteAnagraficaDocument(token, documentId);
      await reloadSubject();
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Errore rimozione documento");
    }
  }

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
        <button className="btn-secondary" type="button" onClick={() => router.push("/anagrafica/subjects")}>
          Torna alla lista
        </button>
      </div>

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
        <div className="mb-4">
          <p className="section-title">Documenti associati</p>
          <p className="section-copy">Classificazione manuale e rimozione dal catalogo GAIA.</p>
        </div>
        {subject.documents.length === 0 ? (
          <p className="text-sm text-gray-500">Nessun documento associato.</p>
        ) : (
          <div className="space-y-3">
            {subject.documents.map((document) => (
              <div key={document.id || document.nas_path} className="rounded-lg border border-gray-100 px-4 py-3">
                <div className="grid gap-3 md:grid-cols-[1.3fr_0.7fr_0.7fr_auto] md:items-center">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{document.filename}</p>
                    <p className="mt-1 break-all text-xs text-gray-500">{document.nas_path}</p>
                  </div>
                  <select
                    className="form-control"
                    value={document.doc_type}
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
                  <button
                    className="text-sm font-medium text-red-600 transition hover:text-red-700"
                    type="button"
                    onClick={() => {
                      if (document.id) {
                        void handleDeleteDocument(document.id);
                      }
                    }}
                  >
                    Rimuovi
                  </button>
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
