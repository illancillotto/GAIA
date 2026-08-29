import Link from "next/link";

import type { GisShapefileImportPreview } from "@/types/gis";

import { ConfirmationDialog } from "../catalogo/catalog-dialog";
import {
  canPreviewImport,
  canProposeChanges,
  canPublishImport,
  canRejectImport,
} from "./tools-workspace-helpers";
import type { GisToolsWorkspaceView } from "./use-gis-tools-workspace";

export function GisToolsSessionStatus() {
  return <p className="rounded-2xl border border-[#dce6dc] bg-white px-4 py-3 text-sm font-semibold text-[#1D4E35]" role="status">Verifica sessione GIS...</p>;
}

export function GisToolsHero() {
  return (
    <section className="rounded-[30px] border border-[#b9cdbd] bg-[linear-gradient(135deg,_#173020,_#6b5b32)] p-5 text-white shadow-xl sm:p-7">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#d6e8bd]">Area operatori</p>
      <h2 className="mt-2 text-3xl font-semibold">Import e strumenti GIS</h2>
      <p className="mt-3 max-w-3xl text-sm leading-6 text-[#edf4e7]">Qui trovi soltanto attività tecniche. Per consultare una mappa torna al catalogo semplice.</p>
      <Link className="mt-5 inline-flex font-semibold underline underline-offset-4" href="/gis/catalogo">Torna al catalogo</Link>
    </section>
  );
}

export function GisToolsFeedback({ notice, error }: { notice: string | null; error: string | null }) {
  return (
    <>
      {notice ? <p className="rounded-2xl border border-[#bcd6c2] bg-[#edf8ef] px-4 py-3 text-sm font-semibold text-[#1D4E35]" role="status" aria-live="polite">{notice}</p> : null}
      {error ? <p className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700" role="alert">{error}</p> : null}
    </>
  );
}

export function GisToolsUploadSection({ tools }: { tools: GisToolsWorkspaceView }) {
  return (
    <section className="rounded-[28px] border border-[#d9dfd6] bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#526a59]">Percorso guidato</p>
      <h3 className="mt-2 text-xl font-semibold text-gray-950">1. Carica una nuova fonte</h3>
      <p className="mt-2 text-sm leading-6 text-gray-600">Il file ZIP deve contenere SHP, SHX, DBF e PRJ. Il controllo avviene prima di qualsiasi pubblicazione.</p>
      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <label className="text-sm font-semibold text-gray-800">File shapefile ZIP<input className="form-control mt-2 text-base" type="file" accept=".zip,application/zip" onChange={(event) => tools.selectFile(event.target.files?.[0] ?? null)} /></label>
        <label className="text-sm font-semibold text-gray-800">Area<select className="form-control mt-2 text-base" value={tools.workspace} onChange={(event) => tools.setWorkspace(event.target.value)}><option value="rete">Rete</option><option value="catasto">Catasto</option><option value="riordino">Riordino</option></select></label>
        <label className="text-sm font-semibold text-gray-800 md:col-span-2">Titolo comprensibile<input className="form-control mt-2 text-base" value={tools.title} placeholder="Es. Condotte rilevate agosto 2026" onChange={(event) => tools.setTitle(event.target.value)} /></label>
      </div>
      <details className="mt-4 rounded-2xl border border-gray-100 bg-gray-50 p-4">
        <summary className="cursor-pointer text-sm font-semibold text-gray-700">Impostazioni tecniche facoltative</summary>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          <label className="text-sm font-semibold text-gray-800">Nome tecnico<input className="form-control mt-2" value={tools.layerName} onChange={(event) => tools.setLayerName(event.target.value)} /></label>
          <label className="text-sm font-semibold text-gray-800">Sistema coordinate<input className="form-control mt-2" inputMode="numeric" value={tools.sourceSrid} placeholder="Rilevato dal PRJ" onChange={(event) => tools.setSourceSrid(event.target.value)} /></label>
          <label className="text-sm font-semibold text-gray-800">Codifica testo<input className="form-control mt-2" value={tools.encoding} placeholder="Automatica" onChange={(event) => tools.setEncoding(event.target.value)} /></label>
        </div>
      </details>
      <button className="btn-primary mt-5" type="button" disabled={tools.busy === "upload"} onClick={() => tools.uploadImport()}>{tools.busy === "upload" ? "Controllo in corso..." : "Controlla e carica"}</button>
    </section>
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

function ImportDecisionActions({
  tools,
  selectedImport,
}: {
  tools: GisToolsWorkspaceView;
  selectedImport: NonNullable<GisToolsWorkspaceView["selectedImport"]>;
}) {
  return (
    <div className="mt-4 flex flex-col gap-3 sm:flex-row">
      {canPreviewImport(selectedImport) ? <button className="btn-secondary" type="button" disabled={tools.busy === "preview"} onClick={() => tools.loadPreview(selectedImport)}>Mostra anteprima</button> : null}
      {canPublishImport(selectedImport) ? <button className="btn-primary" type="button" onClick={() => tools.setPendingAction("publish")}>Pubblica nel catalogo</button> : null}
      {canRejectImport(selectedImport) ? <button className="btn-secondary" type="button" onClick={() => tools.setPendingAction("reject")}>Rigetta import</button> : null}
    </div>
  );
}

function ImportChangeRequests({
  tools,
  selectedImport,
}: {
  tools: GisToolsWorkspaceView;
  selectedImport: NonNullable<GisToolsWorkspaceView["selectedImport"]>;
}) {
  if (!canProposeChanges(selectedImport, tools.editableLayers.length)) return null;
  return (
    <div className="mt-6 rounded-2xl border border-[#e2e9e3] bg-[#f8faf8] p-4">
      <h4 className="font-semibold text-gray-950">3. Proponi correzioni a una mappa esistente</h4>
      <p className="mt-1 text-sm leading-6 text-gray-600">Ogni elemento importato diventa una proposta revisionabile. La mappa ufficiale non viene cambiata subito.</p>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <label className="text-sm font-semibold text-gray-800">Mappa da correggere<select className="form-control mt-2 text-base" value={tools.targetLayerId} onChange={(event) => tools.setTargetLayerId(event.target.value)}>{tools.editableLayers.map((layer) => <option key={layer.id} value={layer.id}>{layer.title}</option>)}</select></label>
        <label className="text-sm font-semibold text-gray-800">Motivo della proposta<textarea className="form-control mt-2 min-h-24 text-base" value={tools.justification} onChange={(event) => tools.setJustification(event.target.value)} /></label>
      </div>
      <button className="btn-primary mt-4" type="button" disabled={tools.busy === "changes"} onClick={() => tools.createGuidedChanges()}>{tools.busy === "changes" ? "Creazione proposte..." : "Crea proposte di modifica"}</button>
    </div>
  );
}

export function GisToolsImportSection({ tools }: { tools: GisToolsWorkspaceView }) {
  if (!tools.selectedImport) return null;
  return (
    <section className="rounded-[28px] border border-[#d9dfd6] bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#526a59]">Import selezionato</p>
      <h3 className="mt-2 text-xl font-semibold text-gray-950">2. Controlla e decidi</h3>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <ImportFact label="Mappa" value={tools.selectedImport.target_layer_title} />
        <ImportFact label="Stato" value={tools.selectedImport.status} />
        <ImportFact label="Elementi" value={String(tools.selectedImport.feature_count)} />
      </div>
      <ImportDecisionActions tools={tools} selectedImport={tools.selectedImport} />
      {tools.preview ? <ImportPreview preview={tools.preview} /> : null}
      <ImportChangeRequests tools={tools} selectedImport={tools.selectedImport} />
    </section>
  );
}

export function GisToolsImportConfirmation({ tools }: { tools: GisToolsWorkspaceView }) {
  if (!tools.pendingAction || !tools.selectedImport) return null;
  const publishing = tools.pendingAction === "publish";
  return (
    <ConfirmationDialog
      title={publishing ? "Pubblicare questa mappa?" : "Rigettare questo import?"}
      description={tools.selectedImport.target_layer_title}
      consequences={publishing ? ["La mappa sarà visibile nel catalogo agli utenti autorizzati.", "I dati resteranno in sola lettura finché non viene configurata una policy diversa."] : ["L'area di prova verrà rimossa.", "L'operazione resterà registrata nello storico."]}
      confirmLabel={publishing ? "Conferma pubblicazione" : "Conferma rigetto"}
      busy={tools.busy === tools.pendingAction}
      error={tools.error}
      tone={publishing ? "primary" : "destructive"}
      onCancel={tools.cancelPendingAction}
      onConfirm={tools.confirmImportAction}
    />
  );
}
