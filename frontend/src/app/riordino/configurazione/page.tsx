"use client";

import { useEffect, useState } from "react";

import { RiordinoModulePage } from "@/components/riordino/module-page";
import { formatRiordinoDate, formatRiordinoLabel } from "@/components/riordino/shared/format";
import {
  createRiordinoDocumentType,
  createRiordinoIssueType,
  deleteRiordinoDocumentType,
  deleteRiordinoIssueType,
  listRiordinoDocumentTypes,
  listRiordinoIssueTypes,
  listRiordinoMunicipalities,
  updateRiordinoDocumentType,
  updateRiordinoIssueType,
} from "@/lib/riordino-api";
import { getStoredAccessToken } from "@/lib/auth";
import type { RiordinoDocumentTypeConfig, RiordinoIssueTypeConfig } from "@/types/riordino";

const ISSUE_CATEGORIES = ["administrative", "technical", "cadastral", "documentary", "gis"];
const ISSUE_SEVERITIES = ["low", "medium", "high", "blocking"];

export default function RiordinoConfigPage() {
  const [token, setToken] = useState<string | null>(null);
  const [documentTypes, setDocumentTypes] = useState<RiordinoDocumentTypeConfig[]>([]);
  const [issueTypes, setIssueTypes] = useState<RiordinoIssueTypeConfig[]>([]);
  const [municipalities, setMunicipalities] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [documentForm, setDocumentForm] = useState({
    code: "",
    label: "",
    description: "",
    sort_order: 0,
    is_active: true,
  });
  const [issueForm, setIssueForm] = useState({
    code: "",
    label: "",
    category: "documentary",
    default_severity: "medium",
    description: "",
    sort_order: 0,
    is_active: true,
  });

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  useEffect(() => {
    if (!token) {
      return;
    }
    const currentToken = token;

    async function loadData() {
      try {
        const [documentTypeItems, issueTypeItems, municipalityItems] = await Promise.all([
          listRiordinoDocumentTypes(currentToken),
          listRiordinoIssueTypes(currentToken),
          listRiordinoMunicipalities(currentToken),
        ]);
        setDocumentTypes(documentTypeItems);
        setIssueTypes(issueTypeItems);
        setMunicipalities(municipalityItems);
        setError(null);
      } catch (currentError) {
        setError(currentError instanceof Error ? currentError.message : "Impossibile caricare la configurazione");
      }
    }

    void loadData();
  }, [token]);

  async function refreshData() {
    if (!token) {
      return;
    }
    const currentToken = token;
    const [documentTypeItems, issueTypeItems, municipalityItems] = await Promise.all([
      listRiordinoDocumentTypes(currentToken),
      listRiordinoIssueTypes(currentToken),
      listRiordinoMunicipalities(currentToken),
    ]);
    setDocumentTypes(documentTypeItems);
    setIssueTypes(issueTypeItems);
    setMunicipalities(municipalityItems);
  }

  async function handleCreateDocumentType() {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      await createRiordinoDocumentType(token, {
        ...documentForm,
        description: documentForm.description || null,
      });
      setDocumentForm({ code: "", label: "", description: "", sort_order: 0, is_active: true });
      await refreshData();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Impossibile creare la tipologia documento");
    } finally {
      setBusy(false);
    }
  }

  async function handleToggleDocumentType(item: RiordinoDocumentTypeConfig) {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      await updateRiordinoDocumentType(token, item.id, { is_active: !item.is_active });
      await refreshData();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Impossibile aggiornare la tipologia documento");
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteDocumentType(id: string) {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      await deleteRiordinoDocumentType(token, id);
      await refreshData();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Impossibile eliminare la tipologia documento");
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateIssueType() {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      await createRiordinoIssueType(token, {
        ...issueForm,
        description: issueForm.description || null,
      });
      setIssueForm({
        code: "",
        label: "",
        category: "documentary",
        default_severity: "medium",
        description: "",
        sort_order: 0,
        is_active: true,
      });
      await refreshData();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Impossibile creare la tipologia issue");
    } finally {
      setBusy(false);
    }
  }

  async function handleToggleIssueType(item: RiordinoIssueTypeConfig) {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      await updateRiordinoIssueType(token, item.id, { is_active: !item.is_active });
      await refreshData();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Impossibile aggiornare la tipologia issue");
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteIssueType(id: string) {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      await deleteRiordinoIssueType(token, id);
      await refreshData();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Impossibile eliminare la tipologia issue");
    } finally {
      setBusy(false);
    }
  }

  return (
    <RiordinoModulePage
      title="Configurazione Riordino"
      description="Gestione tipologie documento, tipologie issue e comuni gia presenti nel dominio Riordino."
      breadcrumb="Riordino"
      requiredSection="riordino.config"
      requiredRoles={["admin", "super_admin"]}
    >
      {error ? (
        <article className="panel-card border border-red-100 bg-red-50/60">
          <p className="text-sm font-medium text-red-700">Errore configurazione</p>
          <p className="mt-1 text-sm text-red-600">{error}</p>
        </article>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-2">
        <article className="panel-card">
          <p className="section-title">Tipologie documento</p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <input className="form-control" placeholder="Codice" value={documentForm.code} onChange={(event) => setDocumentForm((current) => ({ ...current, code: event.target.value }))} />
            <input className="form-control" placeholder="Etichetta" value={documentForm.label} onChange={(event) => setDocumentForm((current) => ({ ...current, label: event.target.value }))} />
            <textarea className="form-control min-h-24 md:col-span-2" placeholder="Descrizione" value={documentForm.description} onChange={(event) => setDocumentForm((current) => ({ ...current, description: event.target.value }))} />
            <input className="form-control" type="number" placeholder="Sort order" value={documentForm.sort_order} onChange={(event) => setDocumentForm((current) => ({ ...current, sort_order: Number(event.target.value) || 0 }))} />
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <input type="checkbox" checked={documentForm.is_active} onChange={(event) => setDocumentForm((current) => ({ ...current, is_active: event.target.checked }))} />
              Attiva
            </label>
            <button className="btn-primary md:col-span-2" disabled={busy || !documentForm.code.trim() || !documentForm.label.trim()} onClick={() => void handleCreateDocumentType()} type="button">
              Crea tipologia documento
            </button>
          </div>
          <div className="mt-4 space-y-3">
            {documentTypes.map((item) => (
              <div key={item.id} className="rounded-xl border border-gray-100 px-4 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-semibold text-gray-900">{item.label}</p>
                  <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{item.code}</span>
                  <span className={`rounded-full px-2 py-0.5 text-xs ${item.is_active ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-600"}`}>
                    {item.is_active ? "attiva" : "disattiva"}
                  </span>
                </div>
                <p className="mt-1 text-sm text-gray-500">{item.description || "Nessuna descrizione"} • ordine {item.sort_order}</p>
                <p className="mt-1 text-xs text-gray-400">Aggiornata il {formatRiordinoDate(item.updated_at, true)}</p>
                <div className="mt-3 flex gap-2">
                  <button className="btn-secondary" disabled={busy} onClick={() => void handleToggleDocumentType(item)} type="button">
                    {item.is_active ? "Disattiva" : "Attiva"}
                  </button>
                  <button className="btn-secondary" disabled={busy} onClick={() => void handleDeleteDocumentType(item.id)} type="button">
                    Elimina
                  </button>
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="panel-card">
          <p className="section-title">Tipologie issue</p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <input className="form-control" placeholder="Codice" value={issueForm.code} onChange={(event) => setIssueForm((current) => ({ ...current, code: event.target.value }))} />
            <input className="form-control" placeholder="Etichetta" value={issueForm.label} onChange={(event) => setIssueForm((current) => ({ ...current, label: event.target.value }))} />
            <select className="form-control" value={issueForm.category} onChange={(event) => setIssueForm((current) => ({ ...current, category: event.target.value }))}>
              {ISSUE_CATEGORIES.map((item) => (
                <option key={item} value={item}>{formatRiordinoLabel(item)}</option>
              ))}
            </select>
            <select className="form-control" value={issueForm.default_severity} onChange={(event) => setIssueForm((current) => ({ ...current, default_severity: event.target.value }))}>
              {ISSUE_SEVERITIES.map((item) => (
                <option key={item} value={item}>{formatRiordinoLabel(item)}</option>
              ))}
            </select>
            <textarea className="form-control min-h-24 md:col-span-2" placeholder="Descrizione" value={issueForm.description} onChange={(event) => setIssueForm((current) => ({ ...current, description: event.target.value }))} />
            <input className="form-control" type="number" placeholder="Sort order" value={issueForm.sort_order} onChange={(event) => setIssueForm((current) => ({ ...current, sort_order: Number(event.target.value) || 0 }))} />
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <input type="checkbox" checked={issueForm.is_active} onChange={(event) => setIssueForm((current) => ({ ...current, is_active: event.target.checked }))} />
              Attiva
            </label>
            <button className="btn-primary md:col-span-2" disabled={busy || !issueForm.code.trim() || !issueForm.label.trim()} onClick={() => void handleCreateIssueType()} type="button">
              Crea tipologia issue
            </button>
          </div>
          <div className="mt-4 space-y-3">
            {issueTypes.map((item) => (
              <div key={item.id} className="rounded-xl border border-gray-100 px-4 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-semibold text-gray-900">{item.label}</p>
                  <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{item.code}</span>
                  <span className={`rounded-full px-2 py-0.5 text-xs ${item.is_active ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-600"}`}>
                    {item.is_active ? "attiva" : "disattiva"}
                  </span>
                </div>
                <p className="mt-1 text-sm text-gray-500">
                  {formatRiordinoLabel(item.category)} • severita default {formatRiordinoLabel(item.default_severity)} • ordine {item.sort_order}
                </p>
                <p className="mt-1 text-sm text-gray-500">{item.description || "Nessuna descrizione"}</p>
                <div className="mt-3 flex gap-2">
                  <button className="btn-secondary" disabled={busy} onClick={() => void handleToggleIssueType(item)} type="button">
                    {item.is_active ? "Disattiva" : "Attiva"}
                  </button>
                  <button className="btn-secondary" disabled={busy} onClick={() => void handleDeleteIssueType(item.id)} type="button">
                    Elimina
                  </button>
                </div>
              </div>
            ))}
          </div>
        </article>
      </div>

      <article className="panel-card">
        <p className="section-title">Comuni rilevati</p>
        <p className="section-copy mt-1">L&apos;elenco deriva dalle pratiche presenti nel dominio.</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {municipalities.length === 0 ? (
            <p className="text-sm text-gray-500">Nessun comune disponibile.</p>
          ) : (
            municipalities.map((item) => (
              <span key={item} className="rounded-full bg-[#EAF3E8] px-3 py-1 text-sm text-[#1D4E35]">
                {item}
              </span>
            ))
          )}
        </div>
      </article>
    </RiordinoModulePage>
  );
}
