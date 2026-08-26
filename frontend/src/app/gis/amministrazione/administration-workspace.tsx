"use client";

import Link from "next/link";
import { type Dispatch, type SetStateAction, useEffect, useState } from "react";

import {
  createGisCatalogLayer,
  getGisQgisGovernance,
  listGisCatalogLayers,
  requestGisCatalogLayerExport,
  setGisCatalogLayerActive,
  updateGisCatalogLayerMetadata,
} from "@/lib/api/gis";
import type {
  GisCatalogLayer,
  GisCatalogLayerExport,
  GisQgisGovernanceResponse,
} from "@/types/gis";

import { ConfirmationDialog } from "../catalogo/catalog-dialog";
import { GisRuntimeHealthPanel } from "../catalogo/runtime-health-panel";
import { GisActivityCenter } from "../strumenti/activity-center";
import { GisPermissionsPanel } from "./permissions-panel";

type CreateLayerForm = {
  workspace: string;
  name: string;
  title: string;
  description: string;
  domainModule: string;
  officialSource: string;
  postgisSchema: string;
  postgisTable: string;
  geometryColumn: string;
  geometryType: string;
  srid: string;
  featureIdColumn: string;
  martinLayerId: string;
};

type MetadataForm = {
  title: string;
  description: string;
  ogcServiceUrl: string;
  qgisProjectPath: string;
  nasExportRoot: string;
};

type ExportForm = {
  versionLabel: string;
  nasPath: string;
};

type PendingLifecycle = {
  layer: GisCatalogLayer;
  nextActive: boolean;
};

const initialCreateForm: CreateLayerForm = {
  workspace: "rete",
  name: "",
  title: "",
  description: "",
  domainModule: "network",
  officialSource: "network",
  postgisSchema: "network",
  postgisTable: "",
  geometryColumn: "geometry",
  geometryType: "MULTILINESTRING",
  srid: "4326",
  featureIdColumn: "id",
  martinLayerId: "",
};

function metadataFormFromLayer(layer: GisCatalogLayer): MetadataForm {
  return {
    title: layer.title,
    description: layer.description ?? "",
    ogcServiceUrl: layer.ogc_service_url ?? "",
    qgisProjectPath: layer.qgis_project_path ?? "",
    nasExportRoot: layer.nas_export_root ?? "",
  };
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

export function GisAdministrationWorkspace({ token }: { token: string | null }) {
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const catalog = useAdministrationCatalog(token, setError);

  if (!token || catalog.loading) {
    return (
      <p className="rounded-2xl border border-[#dce6dc] bg-white px-4 py-3 text-sm font-semibold text-[#1D4E35]" role="status">
        Caricamento amministrazione GIS...
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <AdministrationHeader />
      <AdministrationFeedback error={error} notice={notice} onDismiss={() => setNotice(null)} />
      <CreateLayerSection
        token={token}
        onCreated={catalog.addLayer}
        onError={setError}
        onNotice={setNotice}
      />
      <GisPermissionsPanel token={token} layers={catalog.layers} />
      <GisActivityCenter token={token} layers={catalog.layers} showAudit />
      <GisRuntimeHealthPanel token={token} />
      <ExistingLayersSection
        token={token}
        layers={catalog.layers}
        selectedLayer={catalog.selectedLayer}
        selectedLayerId={catalog.selectedLayerId}
        error={error}
        onChoose={catalog.chooseLayer}
        onReplace={catalog.replaceLayer}
        onError={setError}
        onNotice={setNotice}
      />
      <GovernanceSection governance={catalog.governance} />
    </div>
  );
}

type ErrorSetter = Dispatch<SetStateAction<string | null>>;

function useAdministrationCatalog(token: string | null, setError: ErrorSetter) {
  const [layers, setLayers] = useState<GisCatalogLayer[]>([]);
  const [selectedLayerId, setSelectedLayerId] = useState("");
  const [governance, setGovernance] = useState<GisQgisGovernanceResponse | null>(null);
  const [loading, setLoading] = useState(Boolean(token));

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    void Promise.all([listGisCatalogLayers(token), getGisQgisGovernance(token)])
      .then(([catalog, qgisGovernance]) => {
        if (cancelled) return;
        setLayers(catalog.items);
        setGovernance(qgisGovernance);
        setSelectedLayerId(catalog.items[0]?.id ?? "");
      })
      .catch((loadError: unknown) => {
        if (!cancelled) setError(errorMessage(loadError, "Amministrazione GIS non disponibile"));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [setError, token]);

  const selectedLayer = layers.find((layer) => layer.id === selectedLayerId) ?? layers[0];
  return {
    layers,
    selectedLayer,
    selectedLayerId,
    governance,
    loading,
    chooseLayer(layerId: string) {
      setSelectedLayerId(layerId);
      setError(null);
    },
    addLayer(layer: GisCatalogLayer) {
      setLayers((current) => [...current, layer]);
      setSelectedLayerId(layer.id);
    },
    replaceLayer(updated: GisCatalogLayer) {
      setLayers((current) => current.map((layer) => (layer.id === updated.id ? updated : layer)));
    },
  };
}

function AdministrationHeader() {
  return (
    <section className="rounded-[30px] border border-[#c5d6c8] bg-[linear-gradient(135deg,_#183322,_#315538)] p-5 text-white shadow-xl sm:p-7">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#c6ddbd]">Area riservata</p>
      <h2 className="mt-2 text-3xl font-semibold">Amministrazione GIS</h2>
      <p className="mt-3 max-w-3xl text-sm leading-6 text-[#e7f0e4]">
        Qui gli amministratori registrano le sorgenti, aggiornano le informazioni, gestiscono la disponibilità e avviano gli export. Il catalogo pubblico resta semplice.
      </p>
      <Link className="mt-5 inline-flex text-sm font-semibold text-white underline underline-offset-4" href="/gis/catalogo">
        Torna al catalogo delle mappe
      </Link>
    </section>
  );
}

function AdministrationFeedback({ error, notice, onDismiss }: { error: string | null; notice: string | null; onDismiss: () => void }) {
  return (
    <>
      {error ? <p className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700" role="alert">{error}</p> : null}
      {notice ? (
        <div className="flex flex-col gap-3 rounded-2xl border border-[#bcd6c2] bg-[#edf8ef] px-4 py-3 text-sm text-[#1D4E35] sm:flex-row sm:items-center sm:justify-between" role="status" aria-live="polite">
          <p className="font-semibold">{notice}</p>
          <button className="btn-secondary" type="button" onClick={onDismiss}>Chiudi messaggio</button>
        </div>
      ) : null}
    </>
  );
}

type OperationFeedback = {
  onError: ErrorSetter;
  onNotice: Dispatch<SetStateAction<string | null>>;
};

function CreateLayerSection({ token, onCreated, onError, onNotice }: OperationFeedback & { token: string; onCreated: (layer: GisCatalogLayer) => void }) {
  const [form, setForm] = useState<CreateLayerForm>(initialCreateForm);
  const [busy, setBusy] = useState(false);

  async function createLayer() {
    const srid = Number.parseInt(form.srid, 10);
    if (!form.workspace.trim() || !form.name.trim() || !form.title.trim() || !form.postgisTable.trim() || !Number.isInteger(srid) || srid < 1) {
      onError("Compila area, nome, titolo, tabella PostGIS e un sistema coordinate valido.");
      return;
    }
    setBusy(true);
    onError(null);
    try {
      const created = await createGisCatalogLayer(token, {
        workspace: form.workspace.trim(), name: form.name.trim(), title: form.title.trim(),
        description: form.description, domainModule: form.domainModule, sourceType: "postgis",
        officialSource: form.officialSource, postgisSchema: form.postgisSchema,
        postgisTable: form.postgisTable, geometryColumn: form.geometryColumn,
        geometryType: form.geometryType, srid, featureIdColumn: form.featureIdColumn,
        martinLayerId: form.martinLayerId,
      });
      onCreated(created);
      setForm(initialCreateForm);
      onNotice(`${created.title} è stato aggiunto al catalogo.`);
    } catch (createError) {
      onError(errorMessage(createError, "Creazione layer non riuscita"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-[28px] border border-[#d9dfd6] bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#526a59]">Nuova sorgente</p>
      <h3 className="mt-2 text-xl font-semibold text-gray-950">Registra una mappa PostGIS</h3>
      <p className="mt-2 text-sm leading-6 text-gray-600">Questa operazione registra una tabella già esistente: non crea né modifica dati nel database.</p>
      <CreateLayerFields form={form} setForm={setForm} />
      <button className="btn-primary mt-5" type="button" disabled={busy} onClick={() => void createLayer()}>
        {busy ? "Registrazione..." : "Registra nuova mappa"}
      </button>
    </section>
  );
}

function CreateLayerFields({ form, setForm }: { form: CreateLayerForm; setForm: Dispatch<SetStateAction<CreateLayerForm>> }) {
  const update = (field: keyof CreateLayerForm) => (value: string) => setForm((current) => ({ ...current, [field]: value }));
  return (
    <>
      <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <AdminField label="Area di lavoro" value={form.workspace} onChange={update("workspace")} />
        <AdminField label="Nome tecnico" value={form.name} onChange={update("name")} />
        <AdminField label="Titolo visibile" value={form.title} onChange={update("title")} />
        <AdminField label="Dominio responsabile" value={form.domainModule} onChange={update("domainModule")} />
        <AdminField label="Fonte ufficiale" value={form.officialSource} onChange={update("officialSource")} />
        <AdminField label="Tabella PostGIS" value={form.postgisTable} onChange={update("postgisTable")} />
        <label className="text-sm font-semibold text-gray-800 md:col-span-2 xl:col-span-3">
          Descrizione per gli utenti
          <textarea className="form-control mt-2 min-h-24 text-base" value={form.description} onChange={(event) => update("description")(event.target.value)} />
        </label>
      </div>
      <details className="mt-4 rounded-2xl border border-gray-100 bg-gray-50 p-4">
        <summary className="cursor-pointer text-sm font-semibold text-gray-700">Configurazione tecnica PostGIS e tile</summary>
        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <AdminField label="Schema PostGIS" value={form.postgisSchema} onChange={update("postgisSchema")} />
          <AdminField label="Colonna geometria" value={form.geometryColumn} onChange={update("geometryColumn")} />
          <AdminField label="Tipo geometria" value={form.geometryType} onChange={update("geometryType")} />
          <AdminField label="Sistema coordinate (SRID)" value={form.srid} inputMode="numeric" onChange={update("srid")} />
          <AdminField label="Campo identificativo" value={form.featureIdColumn} onChange={update("featureIdColumn")} />
          <AdminField label="Layer tile Martin (facoltativo)" value={form.martinLayerId} onChange={update("martinLayerId")} />
        </div>
      </details>
    </>
  );
}

function ExistingLayersSection(props: OperationFeedback & {
  token: string; layers: GisCatalogLayer[]; selectedLayer?: GisCatalogLayer;
  selectedLayerId: string; error: string | null; onChoose: (id: string) => void;
  onReplace: (layer: GisCatalogLayer) => void;
}) {
  return (
    <section className="rounded-[28px] border border-[#d9dfd6] bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#526a59]">Mappe esistenti</p>
      <h3 className="mt-2 text-xl font-semibold text-gray-950">Informazioni, disponibilità ed export</h3>
      {!props.selectedLayer ? <p className="mt-4 text-sm text-gray-600">Nessuna mappa amministrabile.</p> : (
        <>
          <label className="mt-5 block text-sm font-semibold text-gray-800">
            Scegli la mappa
            <select className="form-control mt-2 text-base" value={props.selectedLayerId} onChange={(event) => props.onChoose(event.target.value)}>
              {props.layers.map((layer) => <option key={layer.id} value={layer.id}>{layer.title} · {layer.workspace}</option>)}
            </select>
          </label>
          <div className="mt-5 grid gap-5 xl:grid-cols-2">
            <LayerMetadataPanel key={`metadata:${props.selectedLayer.id}`} {...props} layer={props.selectedLayer} />
            <LayerExportPanel key={`export:${props.selectedLayer.id}`} {...props} layer={props.selectedLayer} />
          </div>
        </>
      )}
    </section>
  );
}

function LayerMetadataPanel({ token, layer, error, onReplace, onError, onNotice }: OperationFeedback & { token: string; layer: GisCatalogLayer; error: string | null; onReplace: (layer: GisCatalogLayer) => void }) {
  const [form, setForm] = useState(() => metadataFormFromLayer(layer));
  const [busy, setBusy] = useState(false);

  async function saveMetadata() {
    if (!form.title.trim()) {
      onError("Il titolo visibile è obbligatorio.");
      return;
    }
    setBusy(true);
    onError(null);
    try {
      const updated = await updateGisCatalogLayerMetadata(token, layer.id, form);
      onReplace(updated);
      setForm(metadataFormFromLayer(updated));
      onNotice(`Informazioni di ${updated.title} aggiornate.`);
    } catch (metadataError) {
      onError(errorMessage(metadataError, "Aggiornamento informazioni non riuscito"));
    } finally {
      setBusy(false);
    }
  }

  const update = (field: keyof MetadataForm) => (value: string) => setForm((current) => ({ ...current, [field]: value }));
  return (
    <div className="rounded-2xl border border-[#e2e9e3] bg-[#f8faf8] p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div><h4 className="font-semibold text-gray-950">Informazioni visibili</h4><p className="mt-1 text-sm text-gray-600">Aggiorna testi e collegamenti senza modificare tabella o geometria.</p></div>
        <LayerLifecycleControl token={token} layer={layer} error={error} onReplace={onReplace} onError={onError} onNotice={onNotice} />
      </div>
      <div className="mt-4 grid gap-4">
        <AdminField label="Titolo visibile" value={form.title} onChange={update("title")} />
        <label className="text-sm font-semibold text-gray-800">Descrizione<textarea className="form-control mt-2 min-h-24 text-base" value={form.description} onChange={(event) => update("description")(event.target.value)} /></label>
        <AdminField label="URL servizio OGC (facoltativo)" value={form.ogcServiceUrl} onChange={update("ogcServiceUrl")} />
        <AdminField label="Percorso progetto QGIS (facoltativo)" value={form.qgisProjectPath} onChange={update("qgisProjectPath")} />
        <AdminField label="Cartella NAS export" value={form.nasExportRoot} onChange={update("nasExportRoot")} />
      </div>
      <button className="btn-primary mt-4" type="button" disabled={busy} onClick={() => void saveMetadata()}>{busy ? "Salvataggio..." : "Salva informazioni"}</button>
    </div>
  );
}

function LayerLifecycleControl({ token, layer, error, onReplace, onError, onNotice }: OperationFeedback & { token: string; layer: GisCatalogLayer; error: string | null; onReplace: (layer: GisCatalogLayer) => void }) {
  const [pending, setPending] = useState<PendingLifecycle | null>(null);
  const [busy, setBusy] = useState(false);
  async function confirmLifecycle() {
    const lifecycle = pending as PendingLifecycle;
    setBusy(true);
    onError(null);
    try {
      const updated = await setGisCatalogLayerActive(token, lifecycle.layer.id, lifecycle.nextActive);
      onReplace(updated);
      setPending(null);
      onNotice(`${updated.title} è ora ${updated.is_active ? "attiva" : "non attiva"}.`);
    } catch (lifecycleError) {
      onError(errorMessage(lifecycleError, "Cambio stato non riuscito"));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <button className="btn-secondary" type="button" onClick={() => setPending({ layer, nextActive: !layer.is_active })}>{layer.is_active ? "Rendi non attiva" : "Riattiva mappa"}</button>
      {pending ? <ConfirmationDialog
        title={pending.nextActive ? "Riattivare questa mappa?" : "Rendere non attiva questa mappa?"}
        description={`${pending.layer.title} cambierà disponibilità nel catalogo GIS.`}
        consequences={[pending.nextActive ? "La mappa tornerà visibile agli utenti autorizzati." : "La mappa non sarà più proposta nella consultazione ordinaria.", "La modifica sarà registrata nello storico di audit GIS."]}
        confirmLabel={pending.nextActive ? "Conferma riattivazione" : "Conferma disattivazione"}
        busy={busy} error={error} tone={pending.nextActive ? "primary" : "destructive"}
        onCancel={() => setPending(null)} onConfirm={() => void confirmLifecycle()}
      /> : null}
    </>
  );
}

function LayerExportPanel({ token, layer, onError, onNotice }: OperationFeedback & { token: string; layer: GisCatalogLayer }) {
  const [form, setForm] = useState<ExportForm>({ versionLabel: "", nasPath: layer.nas_export_root ?? "" });
  const [latestExport, setLatestExport] = useState<GisCatalogLayerExport | null>(null);
  const [busy, setBusy] = useState(false);
  async function requestExport() {
    setBusy(true);
    onError(null);
    try {
      const exported = await requestGisCatalogLayerExport(token, layer.id, form);
      setLatestExport(exported);
      onNotice(`Export ${exported.version_label} completato.`);
    } catch (exportError) {
      onError(errorMessage(exportError, "Export shapefile non riuscito"));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="rounded-2xl border border-[#e2e9e3] bg-[#f8faf8] p-4">
      <h4 className="font-semibold text-gray-950">Export shapefile governato</h4>
      <p className="mt-1 text-sm leading-6 text-gray-600">Crea una versione ZIP sul NAS configurato per il layer.</p>
      <div className="mt-4 grid gap-4">
        <AdminField label="Etichetta versione (facoltativa)" value={form.versionLabel} onChange={(value) => setForm((current) => ({ ...current, versionLabel: value }))} />
        <AdminField label="Cartella NAS (facoltativa se già configurata)" value={form.nasPath} onChange={(value) => setForm((current) => ({ ...current, nasPath: value }))} />
      </div>
      <button className="btn-primary mt-4" type="button" disabled={busy} onClick={() => void requestExport()}>{busy ? "Esportazione..." : "Crea export shapefile"}</button>
      {latestExport ? <div className="mt-4 rounded-xl border border-[#c8dccb] bg-white p-3 text-sm text-gray-700" role="status">
        <p className="font-semibold text-[#1D4E35]">Export {latestExport.status}</p><p className="mt-1 break-all">{latestExport.nas_path}</p>
        <p className="mt-1 font-mono text-xs text-gray-500">{latestExport.checksum_sha256 || "Checksum non disponibile"}</p>
      </div> : null}
    </div>
  );
}

function GovernanceSection({ governance }: { governance: GisQgisGovernanceResponse | null }) {
  return (
    <section className="rounded-[28px] border border-[#d9dfd6] bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#526a59]">QGIS Desktop</p>
      <h3 className="mt-2 text-xl font-semibold text-gray-950">Governance generata</h3>
      {governance ? <>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <AdminSummary label="Schema governato" value={governance.schema} />
          <AdminSummary label="Layer pubblicabili" value={String(governance.layers.length)} />
          <AdminSummary label="Istruzioni SQL" value={String(governance.statements.length)} />
        </div>
        <details className="mt-4 rounded-2xl border border-gray-100 bg-gray-50 p-4">
          <summary className="cursor-pointer text-sm font-semibold text-gray-700">Mostra SQL per l&apos;operatore database</summary>
          <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap rounded-xl bg-[#17231d] p-4 text-xs text-[#d7eadb]">{governance.sql}</pre>
        </details>
      </> : <p className="mt-4 text-sm text-gray-600">Governance QGIS non disponibile.</p>}
    </section>
  );
}

function AdminField({
  label,
  value,
  inputMode,
  onChange,
}: {
  label: string;
  value: string;
  inputMode?: "numeric";
  onChange: (value: string) => void;
}) {
  return (
    <label className="text-sm font-semibold text-gray-800">
      {label}
      <input className="form-control mt-2 text-base" value={value} inputMode={inputMode} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function AdminSummary({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-[#e2e9e3] bg-[#f8faf8] p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#526a59]">{label}</p>
      <p className="mt-2 text-xl font-semibold text-gray-950">{value}</p>
    </div>
  );
}
