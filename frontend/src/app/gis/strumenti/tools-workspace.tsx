"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  createGisShapefileImport,
  createGisShapefileImportChangeRequests,
  listGisCatalogLayers,
  previewGisShapefileImport,
  publishGisShapefileImport,
  rejectGisShapefileImport,
} from "@/lib/api/gis";
import type {
  GisCatalogLayer,
  GisShapefileImport,
  GisShapefileImportPreview,
} from "@/types/gis";

import { ConfirmationDialog } from "../catalogo/catalog-dialog";
import { GisActivityCenter } from "./activity-center";
import { GisQgisTools } from "./qgis-tools";

type PendingImportAction = "publish" | "reject";

function readableError(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

function inferLayerName(filename: string): string {
  return filename
    .replace(/\.zip$/i, "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 120);
}

export function GisToolsWorkspace({ token }: { token: string | null }) {
  const [layers, setLayers] = useState<GisCatalogLayer[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [workspace, setWorkspace] = useState("rete");
  const [title, setTitle] = useState("");
  const [layerName, setLayerName] = useState("");
  const [sourceSrid, setSourceSrid] = useState("");
  const [encoding, setEncoding] = useState("");
  const [selectedImport, setSelectedImport] = useState<GisShapefileImport | null>(null);
  const [preview, setPreview] = useState<GisShapefileImportPreview | null>(null);
  const [targetLayerId, setTargetLayerId] = useState("");
  const [justification, setJustification] = useState("");
  const [pendingAction, setPendingAction] = useState<PendingImportAction | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [historyVersion, setHistoryVersion] = useState(0);

  const editableLayers = layers.filter(
    (layer) => layer.is_active && layer.source_type === "postgis" && layer.can_edit,
  );

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    void listGisCatalogLayers(token)
      .then((response) => {
        if (cancelled) return;
        setLayers(response.items);
        const firstEditable = response.items.find(
          (layer) => layer.is_active && layer.source_type === "postgis" && layer.can_edit,
        );
        setTargetLayerId(firstEditable?.id ?? "");
      })
      .catch((loadError: unknown) => {
        if (!cancelled) setError(readableError(loadError, "Catalogo GIS non disponibile"));
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  function selectFile(nextFile: File | null) {
    setFile(nextFile);
    setPreview(null);
    if (!nextFile) return;
    const inferredName = inferLayerName(nextFile.name);
    setLayerName(inferredName);
    setTitle((current) => current || inferredName.replace(/_/g, " "));
  }

  async function uploadImport() {
    if (!token || !file || !workspace.trim() || !title.trim() || !layerName) {
      setError("Scegli un file ZIP e indica area e titolo della mappa.");
      return;
    }
    const parsedSrid = sourceSrid.trim() ? Number.parseInt(sourceSrid, 10) : undefined;
    if (parsedSrid !== undefined && (!Number.isInteger(parsedSrid) || parsedSrid < 1)) {
      setError("Il sistema di coordinate deve essere un numero valido.");
      return;
    }
    setBusy("upload");
    setError(null);
    try {
      const result = await createGisShapefileImport(token, {
        file,
        workspace: workspace.trim(),
        domainModule: workspace === "rete" ? "network" : workspace,
        targetLayerName: layerName,
        targetLayerTitle: title.trim(),
        officialSource: "shapefile_upload",
        sourceSrid: parsedSrid,
        encoding,
      });
      setSelectedImport(result);
      setNotice(`${result.target_layer_title} è stato controllato e salvato nell'area di prova.`);
      setHistoryVersion((value) => value + 1);
      await loadPreview(result);
    } catch (uploadError) {
      setError(readableError(uploadError, "Import non riuscito"));
    } finally {
      setBusy(null);
    }
  }

  async function loadPreview(item: GisShapefileImport) {
    const currentToken = token as string;
    setSelectedImport(item);
    if (item.status !== "validated" && item.status !== "published") {
      setPreview(null);
      return;
    }
    setBusy("preview");
    setError(null);
    try {
      setPreview(await previewGisShapefileImport(currentToken, item.id, 10, 0));
    } catch (previewError) {
      setError(readableError(previewError, "Anteprima non disponibile"));
    } finally {
      setBusy(null);
    }
  }

  async function confirmImportAction() {
    const currentToken = token as string;
    const currentImport = selectedImport as GisShapefileImport;
    const action = pendingAction as PendingImportAction;
    setBusy(action);
    setError(null);
    try {
      const updated = action === "publish"
        ? await publishGisShapefileImport(currentToken, currentImport.id)
        : await rejectGisShapefileImport(currentToken, currentImport.id);
      setSelectedImport(updated);
      setPreview(action === "reject" ? null : preview);
      setPendingAction(null);
      setNotice(action === "publish" ? "Import pubblicato nel catalogo." : "Import rigettato e area di prova rimossa.");
      setHistoryVersion((value) => value + 1);
    } catch (actionError) {
      setError(readableError(actionError, "Operazione import non riuscita"));
    } finally {
      setBusy(null);
    }
  }

  async function createGuidedChanges() {
    if (!token || !selectedImport || !targetLayerId || !justification.trim()) {
      setError("Scegli la mappa da correggere e descrivi il motivo della proposta.");
      return;
    }
    setBusy("changes");
    setError(null);
    let offset = 0;
    let created = 0;
    let existing = 0;
    try {
      while (true) {
        const result = await createGisShapefileImportChangeRequests(
          token,
          selectedImport.id,
          { targetLayerId, justification: justification.trim(), limit: 100, offset },
        );
        created += result.created_count;
        existing += result.existing_count;
        if (!result.has_more || result.returned_count === 0) break;
        offset += result.returned_count;
      }
      setNotice(`${created} proposte create${existing ? `, ${existing} già presenti` : ""}.`);
      setHistoryVersion((value) => value + 1);
    } catch (changeError) {
      setError(readableError(changeError, "Creazione proposte non riuscita"));
    } finally {
      setBusy(null);
    }
  }

  if (!token) {
    return <p className="rounded-2xl border border-[#dce6dc] bg-white px-4 py-3 text-sm font-semibold text-[#1D4E35]" role="status">Verifica sessione GIS...</p>;
  }

  return (
    <div className="space-y-6">
      <section className="rounded-[30px] border border-[#b9cdbd] bg-[linear-gradient(135deg,_#173020,_#6b5b32)] p-5 text-white shadow-xl sm:p-7">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#d6e8bd]">Area operatori</p>
        <h2 className="mt-2 text-3xl font-semibold">Import e strumenti GIS</h2>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-[#edf4e7]">Qui trovi soltanto attività tecniche. Per consultare una mappa torna al catalogo semplice.</p>
        <Link className="mt-5 inline-flex font-semibold underline underline-offset-4" href="/gis/catalogo">Torna al catalogo</Link>
      </section>

      {notice ? <p className="rounded-2xl border border-[#bcd6c2] bg-[#edf8ef] px-4 py-3 text-sm font-semibold text-[#1D4E35]" role="status" aria-live="polite">{notice}</p> : null}
      {error ? <p className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700" role="alert">{error}</p> : null}

      <section className="rounded-[28px] border border-[#d9dfd6] bg-white p-5 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#526a59]">Percorso guidato</p>
        <h3 className="mt-2 text-xl font-semibold text-gray-950">1. Carica una nuova fonte</h3>
        <p className="mt-2 text-sm leading-6 text-gray-600">Il file ZIP deve contenere SHP, SHX, DBF e PRJ. Il controllo avviene prima di qualsiasi pubblicazione.</p>
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <label className="text-sm font-semibold text-gray-800">File shapefile ZIP<input className="form-control mt-2 text-base" type="file" accept=".zip,application/zip" onChange={(event) => selectFile(event.target.files?.[0] ?? null)} /></label>
          <label className="text-sm font-semibold text-gray-800">Area<select className="form-control mt-2 text-base" value={workspace} onChange={(event) => setWorkspace(event.target.value)}><option value="rete">Rete</option><option value="catasto">Catasto</option><option value="riordino">Riordino</option></select></label>
          <label className="text-sm font-semibold text-gray-800 md:col-span-2">Titolo comprensibile<input className="form-control mt-2 text-base" value={title} placeholder="Es. Condotte rilevate agosto 2026" onChange={(event) => setTitle(event.target.value)} /></label>
        </div>
        <details className="mt-4 rounded-2xl border border-gray-100 bg-gray-50 p-4">
          <summary className="cursor-pointer text-sm font-semibold text-gray-700">Impostazioni tecniche facoltative</summary>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <label className="text-sm font-semibold text-gray-800">Nome tecnico<input className="form-control mt-2" value={layerName} onChange={(event) => setLayerName(event.target.value)} /></label>
            <label className="text-sm font-semibold text-gray-800">Sistema coordinate<input className="form-control mt-2" inputMode="numeric" value={sourceSrid} placeholder="Rilevato dal PRJ" onChange={(event) => setSourceSrid(event.target.value)} /></label>
            <label className="text-sm font-semibold text-gray-800">Codifica testo<input className="form-control mt-2" value={encoding} placeholder="Automatica" onChange={(event) => setEncoding(event.target.value)} /></label>
          </div>
        </details>
        <button className="btn-primary mt-5" type="button" disabled={busy === "upload"} onClick={() => void uploadImport()}>{busy === "upload" ? "Controllo in corso..." : "Controlla e carica"}</button>
      </section>

      {selectedImport ? (
        <section className="rounded-[28px] border border-[#d9dfd6] bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#526a59]">Import selezionato</p>
          <h3 className="mt-2 text-xl font-semibold text-gray-950">2. Controlla e decidi</h3>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <ImportFact label="Mappa" value={selectedImport.target_layer_title} />
            <ImportFact label="Stato" value={selectedImport.status} />
            <ImportFact label="Elementi" value={String(selectedImport.feature_count)} />
          </div>
          <div className="mt-4 flex flex-col gap-3 sm:flex-row">
            {(selectedImport.status === "validated" || selectedImport.status === "published") ? <button className="btn-secondary" type="button" disabled={busy === "preview"} onClick={() => void loadPreview(selectedImport)}>Mostra anteprima</button> : null}
            {selectedImport.status === "validated" ? <button className="btn-primary" type="button" onClick={() => setPendingAction("publish")}>Pubblica nel catalogo</button> : null}
            {selectedImport.status !== "rejected" && selectedImport.status !== "published" ? <button className="btn-secondary" type="button" onClick={() => setPendingAction("reject")}>Rigetta import</button> : null}
          </div>
          {preview ? <ImportPreview preview={preview} /> : null}

          {(selectedImport.status === "validated" || selectedImport.status === "published") && editableLayers.length > 0 ? (
            <div className="mt-6 rounded-2xl border border-[#e2e9e3] bg-[#f8faf8] p-4">
              <h4 className="font-semibold text-gray-950">3. Proponi correzioni a una mappa esistente</h4>
              <p className="mt-1 text-sm leading-6 text-gray-600">Ogni elemento importato diventa una proposta revisionabile. La mappa ufficiale non viene cambiata subito.</p>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <label className="text-sm font-semibold text-gray-800">Mappa da correggere<select className="form-control mt-2 text-base" value={targetLayerId} onChange={(event) => setTargetLayerId(event.target.value)}>{editableLayers.map((layer) => <option key={layer.id} value={layer.id}>{layer.title}</option>)}</select></label>
                <label className="text-sm font-semibold text-gray-800">Motivo della proposta<textarea className="form-control mt-2 min-h-24 text-base" value={justification} onChange={(event) => setJustification(event.target.value)} /></label>
              </div>
              <button className="btn-primary mt-4" type="button" disabled={busy === "changes"} onClick={() => void createGuidedChanges()}>{busy === "changes" ? "Creazione proposte..." : "Crea proposte di modifica"}</button>
            </div>
          ) : null}
        </section>
      ) : null}

      <GisActivityCenter key={historyVersion} token={token} layers={layers} onResumeImport={(item) => void loadPreview(item)} />
      <GisQgisTools token={token} />

      {pendingAction && selectedImport ? (
        <ConfirmationDialog
          title={pendingAction === "publish" ? "Pubblicare questa mappa?" : "Rigettare questo import?"}
          description={selectedImport.target_layer_title}
          consequences={pendingAction === "publish" ? ["La mappa sarà visibile nel catalogo agli utenti autorizzati.", "I dati resteranno in sola lettura finché non viene configurata una policy diversa."] : ["L'area di prova verrà rimossa.", "L'operazione resterà registrata nello storico."]}
          confirmLabel={pendingAction === "publish" ? "Conferma pubblicazione" : "Conferma rigetto"}
          busy={busy === pendingAction}
          error={error}
          tone={pendingAction === "publish" ? "primary" : "destructive"}
          onCancel={() => setPendingAction(null)}
          onConfirm={() => void confirmImportAction()}
        />
      ) : null}
    </div>
  );
}

function ImportFact({ label, value }: { label: string; value: string }) {
  return <div className="rounded-2xl border border-[#e2e9e3] bg-[#f8faf8] p-4"><p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#526a59]">{label}</p><p className="mt-2 font-semibold text-gray-950">{value}</p></div>;
}

function ImportPreview({ preview }: { preview: GisShapefileImportPreview }) {
  return (
    <div className="mt-5 overflow-x-auto rounded-2xl border border-[#e2e9e3]" role="status">
      <table className="min-w-full text-left text-sm"><caption className="px-4 py-3 text-left font-semibold text-gray-950">Anteprima dei primi {preview.returned_count} elementi</caption><tbody>{preview.features.map((feature) => <tr key={feature.feature_seq} className="border-t border-[#e2e9e3]"><th className="px-4 py-3 font-semibold text-gray-700">Elemento {feature.feature_seq}</th><td className="px-4 py-3 text-gray-600">{Object.entries(feature.attributes).slice(0, 4).map(([key, value]) => `${key}: ${String(value)}`).join(" · ") || "Nessun attributo"}</td></tr>)}</tbody></table>
    </div>
  );
}
