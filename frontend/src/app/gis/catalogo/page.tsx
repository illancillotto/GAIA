"use client";

import Link from "next/link";
import { startTransition, useEffect, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { RefreshIcon } from "@/components/ui/icons";
import { getStoredAccessToken } from "@/lib/auth";
import {
  createGisLayerChangeRequest,
  createGisLayerAnnotation,
  createGisShapefileImportChangeRequests,
  createGisShapefileImport,
  downloadGisQgisProject,
  getGisCatalogDashboard,
  getGisOgcPoc,
  listGisCatalogLayers,
  listGisChangeRequests,
  listGisLayerAnnotations,
  listGisLayerPermissions,
  previewGisShapefileImport,
  publishGisShapefileImport,
  rejectGisShapefileImport,
  revokeGisLayerPermission,
  setGisChangeRequestStatus,
  setGisLayerAnnotationStatus,
  updateGisChangeRequest,
  updateGisLayerAnnotation,
  upsertGisLayerPermission,
} from "@/lib/api/gis";
import type {
  GisCatalogAccessLevel,
  GisCatalogAnnotation,
  GisCatalogAnnotationStatus,
  GisCatalogChangeRequest,
  GisCatalogChangeRequestStatus,
  GisCatalogChangeRequestType,
  GisCatalogDashboardResponse,
  GisCatalogHealthStatus,
  GisCatalogLayer,
  GisCatalogLayerFilters,
  GisCatalogLayerPermission,
  GisOgcPocResponse,
  GisShapefileImport,
  GisShapefileImportChangeRequestResponse,
  GisShapefileImportPreview,
  GisShapefileImportStatus,
} from "@/types/gis";

type ActiveFilter = "all" | "active" | "inactive";

type FilterState = {
  workspace: string;
  domainModule: string;
  sourceType: string;
  officialSource: string;
  active: ActiveFilter;
};

type PermissionFormState = {
  principalType: "role" | "user";
  principalKey: string;
  accessLevel: GisCatalogAccessLevel;
};

type AnnotationFormState = {
  featureId: string;
  title: string;
  body: string;
};

type AnnotationStatusFilter = "all" | GisCatalogAnnotationStatus;

type AnnotationFilterState = {
  status: AnnotationStatusFilter;
  featureId: string;
};

type ChangeRequestStatusFilter = "all" | GisCatalogChangeRequestStatus;

type ChangeRequestFilterState = {
  status: ChangeRequestStatusFilter;
};

type ChangeRequestFormState = {
  featureId: string;
  changeType: GisCatalogChangeRequestType;
  payload: string;
  justification: string;
  reviewNotes: string;
};

type ShapefileImportFormState = {
  workspace: string;
  domainModule: string;
  targetLayerName: string;
  targetLayerTitle: string;
  officialSource: string;
  sourceSrid: string;
  encoding: string;
};

type ImportChangeRequestFormState = {
  targetLayerId: string;
  justification: string;
  limit: string;
  offset: string;
};

const initialFilters: FilterState = {
  workspace: "",
  domainModule: "",
  sourceType: "",
  officialSource: "",
  active: "all",
};

const initialPermissionForm: PermissionFormState = {
  principalType: "role",
  principalKey: "viewer",
  accessLevel: "viewer",
};

const initialAnnotationForm: AnnotationFormState = {
  featureId: "",
  title: "",
  body: "",
};

const initialAnnotationFilters: AnnotationFilterState = {
  status: "all",
  featureId: "",
};

const initialChangeRequestFilters: ChangeRequestFilterState = {
  status: "all",
};

const initialChangeRequestForm: ChangeRequestFormState = {
  featureId: "",
  changeType: "attribute_update",
  payload: '{\n  "after": {}\n}',
  justification: "",
  reviewNotes: "",
};

const initialShapefileImportForm: ShapefileImportFormState = {
  workspace: "rete",
  domainModule: "network",
  targetLayerName: "",
  targetLayerTitle: "",
  officialSource: "shapefile_upload",
  sourceSrid: "",
  encoding: "",
};

const initialImportChangeRequestForm: ImportChangeRequestFormState = {
  targetLayerId: "",
  justification: "",
  limit: "25",
  offset: "0",
};

const gisAccessLevels: GisCatalogAccessLevel[] = ["viewer", "annotator", "editor", "approver", "admin"];
const annotationStatuses: GisCatalogAnnotationStatus[] = ["open", "in_review", "closed", "rejected"];
const changeRequestStatuses: GisCatalogChangeRequestStatus[] = ["submitted", "needs_changes", "approved", "rejected", "applied"];
const changeRequestTypes: GisCatalogChangeRequestType[] = ["attribute_update", "geometry_update", "feature_create", "feature_delete"];
const applicationRoleOptions = ["viewer", "operator", "reviewer", "hr_manager", "admin", "super_admin"];

const accessLevelDescriptions: Record<GisCatalogAccessLevel, string> = {
  viewer: "consultare",
  annotator: "consultare e aggiungere note",
  editor: "proporre modifiche",
  approver: "approvare le modifiche",
  admin: "amministrare il layer",
};

const annotationStatusLabels: Record<GisCatalogAnnotationStatus, string> = {
  open: "Aperta",
  in_review: "In revisione",
  closed: "Chiusa",
  rejected: "Rigettata",
};

const changeRequestStatusLabels: Record<GisCatalogChangeRequestStatus, string> = {
  submitted: "Inviata",
  needs_changes: "Da correggere",
  approved: "Approvata",
  rejected: "Rigettata",
  applied: "Applicata",
};

const changeRequestTypeLabels: Record<GisCatalogChangeRequestType, string> = {
  attribute_update: "Modifica attributi",
  geometry_update: "Modifica geometria",
  feature_create: "Nuovo elemento",
  feature_delete: "Eliminazione elemento",
};

const shapefileImportStatusLabels: Record<GisShapefileImportStatus, string> = {
  uploaded: "caricato",
  validated: "controllato e valido",
  rejected: "rigettato",
  published: "pubblicato",
  failed: "fallito",
};

function toApiFilters(filters: FilterState): GisCatalogLayerFilters {
  const apiFilters: GisCatalogLayerFilters = {};
  if (filters.workspace.trim()) apiFilters.workspace = filters.workspace.trim();
  if (filters.domainModule.trim()) apiFilters.domainModule = filters.domainModule.trim();
  if (filters.sourceType.trim()) apiFilters.sourceType = filters.sourceType.trim();
  if (filters.officialSource.trim()) apiFilters.officialSource = filters.officialSource.trim();
  if (filters.active === "active") apiFilters.isActive = true;
  if (filters.active === "inactive") apiFilters.isActive = false;
  return apiFilters;
}

function formatValue(value: string | number | null | undefined): string {
  if (value == null || value === "") return "Non configurato";
  return String(value);
}

function metadataObject(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function metadataLabel(value: unknown): string {
  if (value == null || value === "") return "Non configurato";
  return String(value);
}

function qgisMode(layer: GisCatalogLayer): string {
  const qgis = metadataObject(layer.metadata.qgis);
  return metadataLabel(qgis?.mode);
}

function tileProvider(layer: GisCatalogLayer): string {
  const tiles = metadataObject(layer.metadata.tiles);
  return metadataLabel(tiles?.provider);
}

function domainWorkspaceHref(layer: GisCatalogLayer): string | null {
  if (layer.workspace === "catasto" || layer.domain_module === "catasto") return "/catasto/gis";
  return null;
}

function updateFilterValue(filters: FilterState, key: keyof FilterState, value: string): FilterState {
  return { ...filters, [key]: value } as FilterState;
}

function updatePermissionForm(
  form: PermissionFormState,
  key: keyof PermissionFormState,
  value: string,
): PermissionFormState {
  if (key === "principalType") {
    const principalType = value === "user" ? "user" : "role";
    return {
      ...form,
      principalType,
      principalKey: principalType === "role" ? "viewer" : "",
    };
  }
  if (key === "accessLevel") {
    return { ...form, accessLevel: value as GisCatalogAccessLevel };
  }
  return { ...form, principalKey: value };
}

function updateAnnotationForm(
  form: AnnotationFormState,
  key: keyof AnnotationFormState,
  value: string,
): AnnotationFormState {
  return { ...form, [key]: value };
}

function updateChangeRequestForm(
  form: ChangeRequestFormState,
  key: keyof ChangeRequestFormState,
  value: string,
): ChangeRequestFormState {
  if (key === "changeType") return { ...form, changeType: value as GisCatalogChangeRequestType };
  return { ...form, [key]: value };
}

function updateShapefileImportForm(
  form: ShapefileImportFormState,
  key: keyof ShapefileImportFormState,
  value: string,
): ShapefileImportFormState {
  return { ...form, [key]: value };
}

function normalizeLayerSlug(value: string): string {
  const withoutExtension = value.replace(/\.[^.]+$/, "");
  return (
    withoutExtension
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "") || "shapefile_upload"
  );
}

function titleFromSlug(value: string): string {
  return value
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function inferLayerFromFilename(filename: string, layers: GisCatalogLayer[]): GisCatalogLayer | undefined {
  const fileSlug = normalizeLayerSlug(filename);
  const postgisLayers = layers.filter((layer) => layer.is_active && layer.source_type === "postgis");
  return postgisLayers.find((layer) => {
    const layerSlug = normalizeLayerSlug(layer.name);
    return fileSlug === layerSlug || fileSlug.startsWith(`${layerSlug}_`) || fileSlug.includes(`_${layerSlug}_`);
  });
}

function inferShapefileImportForm(
  file: File,
  layers: GisCatalogLayer[],
  currentForm: ShapefileImportFormState,
): ShapefileImportFormState {
  const fileSlug = normalizeLayerSlug(file.name);
  const matchedLayer = inferLayerFromFilename(file.name, layers);
  const targetLayerName = `${matchedLayer?.name ?? fileSlug}_upload`;
  const targetLayerTitle = `${matchedLayer?.title ?? titleFromSlug(fileSlug)} upload`;
  return {
    ...currentForm,
    workspace: matchedLayer?.workspace || currentForm.workspace || "import",
    domainModule: matchedLayer?.domain_module || currentForm.domainModule,
    targetLayerName,
    targetLayerTitle,
    officialSource: currentForm.officialSource || "shapefile_upload",
    sourceSrid: currentForm.sourceSrid,
  };
}

function updateImportChangeRequestForm(
  form: ImportChangeRequestFormState,
  key: keyof ImportChangeRequestFormState,
  value: string,
): ImportChangeRequestFormState {
  return { ...form, [key]: value };
}

function downloadBrowserBlob(blob: Blob, filename: string): void {
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}

function toAnnotationApiFilters(filters: AnnotationFilterState) {
  return {
    status: filters.status === "all" ? undefined : filters.status,
    featureId: filters.featureId,
  };
}

function toChangeRequestApiFilters(layer: GisCatalogLayer, filters: ChangeRequestFilterState) {
  return {
    layerId: layer.id,
    status: filters.status === "all" ? undefined : filters.status,
  };
}

function parseJsonObject(value: string): Record<string, unknown> | null {
  try {
    const parsed = JSON.parse(value) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
    return parsed as Record<string, unknown>;
  } catch {
    return null;
  }
}

function prettyJson(value: Record<string, unknown>): string {
  return JSON.stringify(value, null, 2);
}

function changeRequestPayloadLabel(changeRequest: GisCatalogChangeRequest): string {
  const labels: Record<GisCatalogChangeRequestType, string> = {
    attribute_update: "Diff attributi",
    geometry_update: "Diff geometria",
    feature_create: "Nuova feature",
    feature_delete: "Feature da eliminare",
  };
  return `${labels[changeRequest.change_type]}\n${prettyJson(changeRequest.payload)}`;
}

const healthStatusLabels: Record<GisCatalogHealthStatus, string> = {
  ok: "OK",
  warning: "Warning",
  critical: "Critical",
};

const healthStatusClasses: Record<GisCatalogHealthStatus, string> = {
  ok: "bg-[#EAF3E8] text-[#1D4E35]",
  warning: "bg-[#FFF6D8] text-[#76560C]",
  critical: "bg-[#FFE5E1] text-[#9A2B1F]",
};

const catalogGuides = [
  {
    eyebrow: "01",
    title: "Che cos'e un layer",
    body: "Un layer e una mappa tematica: ad esempio le particelle catastali o le condotte irrigue. Ogni scheda qui sotto descrive una di queste mappe.",
  },
  {
    eyebrow: "02",
    title: "Import shapefile",
    body: "Chi riceve dati geografici da fornitori o rilievi puo caricarli qui in sicurezza: GAIA li controlla prima e nulla viene sovrascritto in automatico.",
  },
  {
    eyebrow: "03",
    title: "QGIS Desktop",
    body: "I tecnici che usano il programma QGIS possono scaricare un progetto gia pronto con tutte le mappe a cui hanno accesso.",
  },
  {
    eyebrow: "04",
    title: "Note e richieste",
    body: "Su ogni mappa puoi lasciare note o proporre correzioni: una persona autorizzata le rivede e decide se applicarle. Nulla cambia senza approvazione.",
  },
];

const shapefileRequirements = [".shp", ".shx", ".dbf", ".prj"];

const shapefilePipeline = [
  "Carica un file .zip completo: GAIA riconosce da solo la maggior parte delle informazioni.",
  "GAIA controlla il contenuto (geometrie, coordinate, campi) e segnala eventuali problemi.",
  "I dati finiscono in un'area di prova: puoi guardarli senza toccare nulla di ufficiale.",
  "Controlla e correggi, se serve, i campi proposti (area di lavoro, nome, titolo).",
  "Alla fine scegli tu: pubblicare come nuova mappa oppure proporre modifiche a una mappa ufficiale.",
];

const qgisDesktopModes = [
  "Scarica il progetto unico .qgz: dentro trovi il progetto QGIS, un elenco dei layer e un README operativo.",
  "Aprilo da QGIS Desktop dopo aver configurato il servizio PostGIS gaia_gis sul PC.",
  "Il file include solo i layer che puoi vedere: aree di prova e registri applicativi restano fuori.",
];

const layerFactDescriptions = {
  postgis: "Tabella o vista usata dal layer quando la sorgente e PostGIS.",
  geometry: "Tipo geometrico e sistema di riferimento: servono per mappa, export e QGIS.",
  martin: "Identificativo del tile server Martin, se il layer e pubblicato come tile.",
  featureId: "Campo stabile usato per collegare note e change request a una feature.",
  sourceType: "Tecnologia o registro da cui arriva il layer nel catalogo.",
  officialSource: "Sistema autorevole da cui il dato deve essere considerato valido.",
  qgisMode: "Modalita prevista per QGIS Desktop: read-only, controlled edit o non pubblicato.",
  tileProvider: "Motore che serve le tile al viewer quando configurato.",
} as const;

function GisCatalogWorkspace({ token }: { token: string | null }) {
  const [filters, setFilters] = useState<FilterState>(initialFilters);
  const [layers, setLayers] = useState<GisCatalogLayer[]>([]);
  const [dashboard, setDashboard] = useState<GisCatalogDashboardResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [permissionsLayerId, setPermissionsLayerId] = useState<string | null>(null);
  const [permissions, setPermissions] = useState<GisCatalogLayerPermission[]>([]);
  const [permissionForm, setPermissionForm] = useState<PermissionFormState>(initialPermissionForm);
  const [permissionError, setPermissionError] = useState<string | null>(null);
  const [permissionBusy, setPermissionBusy] = useState<string | null>(null);
  const [annotationsLayerId, setAnnotationsLayerId] = useState<string | null>(null);
  const [annotations, setAnnotations] = useState<GisCatalogAnnotation[]>([]);
  const [annotationFilters, setAnnotationFilters] = useState<AnnotationFilterState>(initialAnnotationFilters);
  const [annotationForm, setAnnotationForm] = useState<AnnotationFormState>(initialAnnotationForm);
  const [editingAnnotationId, setEditingAnnotationId] = useState<string | null>(null);
  const [annotationError, setAnnotationError] = useState<string | null>(null);
  const [annotationBusy, setAnnotationBusy] = useState<string | null>(null);
  const [changeRequestsLayerId, setChangeRequestsLayerId] = useState<string | null>(null);
  const [changeRequests, setChangeRequests] = useState<GisCatalogChangeRequest[]>([]);
  const [changeRequestFilters, setChangeRequestFilters] = useState<ChangeRequestFilterState>(initialChangeRequestFilters);
  const [changeRequestForm, setChangeRequestForm] = useState<ChangeRequestFormState>(initialChangeRequestForm);
  const [editingChangeRequestId, setEditingChangeRequestId] = useState<string | null>(null);
  const [changeRequestError, setChangeRequestError] = useState<string | null>(null);
  const [changeRequestBusy, setChangeRequestBusy] = useState<string | null>(null);
  const [shapefileImportForm, setShapefileImportForm] = useState<ShapefileImportFormState>(initialShapefileImportForm);
  const [shapefileImportFile, setShapefileImportFile] = useState<File | null>(null);
  const [shapefileImportResult, setShapefileImportResult] = useState<GisShapefileImport | null>(null);
  const [shapefileImportPreview, setShapefileImportPreview] = useState<GisShapefileImportPreview | null>(null);
  const [shapefileImportPreviewOpen, setShapefileImportPreviewOpen] = useState(false);
  const [shapefileImportError, setShapefileImportError] = useState<string | null>(null);
  const [shapefileImportPreviewError, setShapefileImportPreviewError] = useState<string | null>(null);
  const [shapefileImportBusy, setShapefileImportBusy] = useState<"upload" | "preview" | "publish" | "reject" | null>(null);
  const [importChangeRequestForm, setImportChangeRequestForm] = useState<ImportChangeRequestFormState>(initialImportChangeRequestForm);
  const [importChangeRequestResult, setImportChangeRequestResult] = useState<GisShapefileImportChangeRequestResponse | null>(null);
  const [importChangeRequestError, setImportChangeRequestError] = useState<string | null>(null);
  const [importChangeRequestBusy, setImportChangeRequestBusy] = useState(false);
  const [qgisProjectBusy, setQgisProjectBusy] = useState(false);
  const [qgisProjectError, setQgisProjectError] = useState<string | null>(null);
  const [ogcPoc, setOgcPoc] = useState<GisOgcPocResponse | null>(null);
  const [ogcPocBusy, setOgcPocBusy] = useState(false);
  const [ogcPocError, setOgcPocError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setIsLoading(false);
      return;
    }

    let isCancelled = false;
    const currentToken = token;
    async function loadInitialCatalog() {
      setIsLoading(true);
      try {
        const [response, dashboardResponse] = await Promise.all([
          listGisCatalogLayers(currentToken),
          getGisCatalogDashboard(currentToken),
        ]);
        /* v8 ignore next -- defensive cleanup guard for unmounted requests */
        if (isCancelled) return;
        setLayers(response.items);
        setDashboard(dashboardResponse);
        setLoadError(null);
      } catch (error) {
        /* v8 ignore next -- defensive cleanup guard for unmounted requests */
        if (isCancelled) return;
        setLoadError(error instanceof Error ? error.message : "Errore caricamento catalogo GIS");
      } finally {
        /* v8 ignore next -- defensive cleanup guard for unmounted requests */
        if (!isCancelled) setIsLoading(false);
      }
    }

    void loadInitialCatalog();
    return () => {
      isCancelled = true;
    };
  }, [token]);

  async function loadCatalog(nextFilters: FilterState) {
    const currentToken = token as string;
    setIsLoading(true);
    try {
      const [response, dashboardResponse] = await Promise.all([
        listGisCatalogLayers(currentToken, toApiFilters(nextFilters)),
        getGisCatalogDashboard(currentToken),
      ]);
      setLayers(response.items);
      setDashboard(dashboardResponse);
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore caricamento catalogo GIS");
    } finally {
      setIsLoading(false);
    }
  }

  function setFilter(key: keyof FilterState, value: string) {
    startTransition(() => {
      setFilters((currentFilters) => updateFilterValue(currentFilters, key, value));
    });
  }

  function resetFilters() {
    startTransition(() => {
      setFilters(initialFilters);
    });
    void loadCatalog(initialFilters);
  }

  async function loadPermissions(layer: GisCatalogLayer) {
    const currentToken = token as string;
    setPermissionsLayerId(layer.id);
    setPermissionBusy(`load:${layer.id}`);
    setPermissionError(null);
    try {
      const response = await listGisLayerPermissions(currentToken, layer.id);
      setPermissions(response);
    } catch (error) {
      setPermissions([]);
      setPermissionError(error instanceof Error ? error.message : "Errore caricamento permessi GIS");
    } finally {
      setPermissionBusy(null);
    }
  }

  function togglePermissionPanel(layer: GisCatalogLayer) {
    if (permissionsLayerId === layer.id) {
      setPermissionsLayerId(null);
      setPermissions([]);
      setPermissionError(null);
      return;
    }
    setPermissionForm(initialPermissionForm);
    void loadPermissions(layer);
  }

  async function savePermission(layer: GisCatalogLayer) {
    const principalKey = permissionForm.principalKey.trim();
    if (!principalKey) {
      setPermissionError("Principal richiesto.");
      return;
    }

    const currentToken = token as string;
    setPermissionBusy(`save:${layer.id}`);
    setPermissionError(null);
    try {
      await upsertGisLayerPermission(currentToken, layer.id, {
        principalType: permissionForm.principalType,
        principalKey,
        accessLevel: permissionForm.accessLevel,
      });
      const response = await listGisLayerPermissions(currentToken, layer.id);
      setPermissions(response);
    } catch (error) {
      setPermissionError(error instanceof Error ? error.message : "Errore salvataggio permesso GIS");
    } finally {
      setPermissionBusy(null);
    }
  }

  async function revokePermission(layer: GisCatalogLayer, permissionId: string) {
    const currentToken = token as string;
    setPermissionBusy(`revoke:${permissionId}`);
    setPermissionError(null);
    try {
      await revokeGisLayerPermission(currentToken, layer.id, permissionId);
      setPermissions((currentItems) => currentItems.filter((item) => item.id !== permissionId));
    } catch (error) {
      setPermissionError(error instanceof Error ? error.message : "Errore revoca permesso GIS");
    } finally {
      setPermissionBusy(null);
    }
  }

  async function loadAnnotations(layer: GisCatalogLayer, filters: AnnotationFilterState = annotationFilters) {
    const currentToken = token as string;
    setAnnotationsLayerId(layer.id);
    setAnnotationBusy(`load:${layer.id}`);
    setAnnotationError(null);
    try {
      const response = await listGisLayerAnnotations(currentToken, layer.id, toAnnotationApiFilters(filters));
      setAnnotations(response);
    } catch (error) {
      setAnnotations([]);
      setAnnotationError(error instanceof Error ? error.message : "Errore caricamento annotazioni GIS");
    } finally {
      setAnnotationBusy(null);
    }
  }

  function toggleAnnotationPanel(layer: GisCatalogLayer) {
    if (annotationsLayerId === layer.id) {
      setAnnotationsLayerId(null);
      setAnnotations([]);
      setAnnotationError(null);
      setEditingAnnotationId(null);
      return;
    }
    setAnnotationFilters(initialAnnotationFilters);
    setAnnotationForm(initialAnnotationForm);
    setEditingAnnotationId(null);
    void loadAnnotations(layer, initialAnnotationFilters);
  }

  function editAnnotation(annotation: GisCatalogAnnotation) {
    setEditingAnnotationId(annotation.id);
    setAnnotationForm({
      featureId: annotation.feature_id ?? "",
      title: annotation.title,
      body: annotation.body,
    });
  }

  function resetAnnotationForm() {
    setEditingAnnotationId(null);
    setAnnotationForm(initialAnnotationForm);
  }

  async function saveAnnotation(layer: GisCatalogLayer) {
    const title = annotationForm.title.trim();
    const body = annotationForm.body.trim();
    if (!title || !body) {
      setAnnotationError("Titolo e testo annotazione sono richiesti.");
      return;
    }

    const currentToken = token as string;
    setAnnotationBusy(`save:${layer.id}`);
    setAnnotationError(null);
    try {
      if (editingAnnotationId) {
        await updateGisLayerAnnotation(currentToken, layer.id, editingAnnotationId, { title, body });
      } else {
        await createGisLayerAnnotation(currentToken, layer.id, {
          featureId: annotationForm.featureId,
          title,
          body,
          attachmentRefs: [],
        });
      }
      resetAnnotationForm();
      const response = await listGisLayerAnnotations(currentToken, layer.id, toAnnotationApiFilters(annotationFilters));
      setAnnotations(response);
    } catch (error) {
      setAnnotationError(error instanceof Error ? error.message : "Errore salvataggio annotazione GIS");
    } finally {
      setAnnotationBusy(null);
    }
  }

  async function changeAnnotationStatus(
    layer: GisCatalogLayer,
    annotationId: string,
    nextStatus: Exclude<GisCatalogAnnotationStatus, "open">,
  ) {
    const currentToken = token as string;
    setAnnotationBusy(`status:${annotationId}:${nextStatus}`);
    setAnnotationError(null);
    try {
      const updated = await setGisLayerAnnotationStatus(currentToken, layer.id, annotationId, nextStatus);
      setAnnotations((currentItems) => currentItems.map((item) => (item.id === updated.id ? updated : item)));
    } catch (error) {
      setAnnotationError(error instanceof Error ? error.message : "Errore stato annotazione GIS");
    } finally {
      setAnnotationBusy(null);
    }
  }

  async function loadChangeRequests(layer: GisCatalogLayer, filters: ChangeRequestFilterState) {
    const currentToken = token as string;
    setChangeRequestsLayerId(layer.id);
    setChangeRequestBusy(`load:${layer.id}`);
    setChangeRequestError(null);
    try {
      const response = await listGisChangeRequests(currentToken, toChangeRequestApiFilters(layer, filters));
      setChangeRequests(response);
    } catch (error) {
      setChangeRequests([]);
      setChangeRequestError(error instanceof Error ? error.message : "Errore caricamento change request GIS");
    } finally {
      setChangeRequestBusy(null);
    }
  }

  function toggleChangeRequestPanel(layer: GisCatalogLayer) {
    if (changeRequestsLayerId === layer.id) {
      setChangeRequestsLayerId(null);
      setChangeRequests([]);
      setChangeRequestError(null);
      setEditingChangeRequestId(null);
      return;
    }
    setChangeRequestFilters(initialChangeRequestFilters);
    setChangeRequestForm(initialChangeRequestForm);
    setEditingChangeRequestId(null);
    void loadChangeRequests(layer, initialChangeRequestFilters);
  }

  function editChangeRequest(changeRequest: GisCatalogChangeRequest) {
    setEditingChangeRequestId(changeRequest.id);
    setChangeRequestForm({
      featureId: changeRequest.feature_id ?? "",
      changeType: changeRequest.change_type,
      payload: prettyJson(changeRequest.payload),
      justification: changeRequest.justification ?? "",
      reviewNotes: "",
    });
  }

  function resetChangeRequestForm() {
    setEditingChangeRequestId(null);
    setChangeRequestForm(initialChangeRequestForm);
  }

  async function saveChangeRequest(layer: GisCatalogLayer) {
    const payload = parseJsonObject(changeRequestForm.payload);
    if (!payload) {
      setChangeRequestError("Payload JSON oggetto richiesto.");
      return;
    }

    const currentToken = token as string;
    setChangeRequestBusy(`save:${layer.id}`);
    setChangeRequestError(null);
    try {
      if (editingChangeRequestId) {
        await updateGisChangeRequest(currentToken, editingChangeRequestId, {
          featureId: changeRequestForm.featureId,
          changeType: changeRequestForm.changeType,
          payload,
          justification: changeRequestForm.justification,
        });
      } else {
        await createGisLayerChangeRequest(currentToken, layer.id, {
          featureId: changeRequestForm.featureId,
          changeType: changeRequestForm.changeType,
          payload,
          justification: changeRequestForm.justification,
        });
      }
      resetChangeRequestForm();
      const response = await listGisChangeRequests(currentToken, toChangeRequestApiFilters(layer, changeRequestFilters));
      setChangeRequests(response);
    } catch (error) {
      setChangeRequestError(error instanceof Error ? error.message : "Errore salvataggio change request GIS");
    } finally {
      setChangeRequestBusy(null);
    }
  }

  async function changeChangeRequestStatus(
    changeRequestId: string,
    nextStatus: Exclude<GisCatalogChangeRequestStatus, "submitted">,
  ) {
    const currentToken = token as string;
    setChangeRequestBusy(`status:${changeRequestId}:${nextStatus}`);
    setChangeRequestError(null);
    try {
      const updated = await setGisChangeRequestStatus(
        currentToken,
        changeRequestId,
        nextStatus,
        changeRequestForm.reviewNotes,
      );
      setChangeRequests((currentItems) => currentItems.map((item) => (item.id === updated.id ? updated : item)));
      setChangeRequestForm((currentForm) => ({ ...currentForm, reviewNotes: "" }));
    } catch (error) {
      setChangeRequestError(error instanceof Error ? error.message : "Errore stato change request GIS");
    } finally {
      setChangeRequestBusy(null);
    }
  }

  function setShapefileImportValue(key: keyof ShapefileImportFormState, value: string) {
    startTransition(() => {
      setShapefileImportForm((currentForm) => updateShapefileImportForm(currentForm, key, value));
    });
  }

  function handleShapefileFileChange(file: File | null) {
    setShapefileImportFile(file);
    setShapefileImportResult(null);
    setShapefileImportPreview(null);
    setShapefileImportPreviewOpen(false);
    setShapefileImportPreviewError(null);
    setImportChangeRequestResult(null);
    setImportChangeRequestError(null);
    if (!file) return;
    const matchedLayer = inferLayerFromFilename(file.name, layers);
    setShapefileImportForm((currentForm) => inferShapefileImportForm(file, layers, currentForm));
    if (matchedLayer?.can_edit) {
      setImportChangeRequestForm((currentForm) => ({ ...currentForm, targetLayerId: matchedLayer.id }));
    }
  }

  function setImportChangeRequestValue(key: keyof ImportChangeRequestFormState, value: string) {
    startTransition(() => {
      setImportChangeRequestForm((currentForm) => updateImportChangeRequestForm(currentForm, key, value));
    });
  }

  async function submitShapefileImport() {
    const currentToken = token as string;
    const workspace = shapefileImportForm.workspace.trim();
    const targetLayerName = shapefileImportForm.targetLayerName.trim();
    const targetLayerTitle = shapefileImportForm.targetLayerTitle.trim();
    const sourceSridInput = shapefileImportForm.sourceSrid.trim();
    const sourceSrid = sourceSridInput ? Number.parseInt(sourceSridInput, 10) : undefined;
    const hasInvalidSourceSrid = sourceSridInput !== "" && (!Number.isInteger(sourceSrid) || (sourceSrid ?? 0) < 1);
    if (!shapefileImportFile) {
      setShapefileImportError("Scegli un file .zip dello shapefile prima di continuare.");
      return;
    }
    if (!workspace || !targetLayerName || !targetLayerTitle || hasInvalidSourceSrid) {
      setShapefileImportError("Compila area di lavoro, nome layer e titolo visibile. Inserisci SRID solo se non e leggibile dal .prj.");
      return;
    }

    setShapefileImportBusy("upload");
    setShapefileImportError(null);
    setShapefileImportPreview(null);
    setShapefileImportPreviewError(null);
    try {
      const response = await createGisShapefileImport(currentToken, {
        file: shapefileImportFile,
        workspace,
        domainModule: shapefileImportForm.domainModule,
        targetLayerName,
        targetLayerTitle,
        officialSource: shapefileImportForm.officialSource,
        sourceSrid,
        encoding: shapefileImportForm.encoding,
      });
      setShapefileImportResult(response);
      try {
        const preview = await previewGisShapefileImport(currentToken, response.id, 5, 0);
        setShapefileImportPreview(preview);
        setShapefileImportPreviewOpen(true);
      } catch (previewError) {
        setShapefileImportPreviewError(previewError instanceof Error ? previewError.message : "Errore preview import shapefile GIS");
      }
      const defaultTargetLayer = layers.find(
        (layer) => layer.is_active && layer.source_type === "postgis" && layer.can_edit && layer.workspace === workspace && layer.name === targetLayerName,
      );
      setImportChangeRequestForm((currentForm) => ({
        ...currentForm,
        targetLayerId: currentForm.targetLayerId || defaultTargetLayer?.id || "",
      }));
      setImportChangeRequestResult(null);
      setImportChangeRequestError(null);
    } catch (error) {
      setShapefileImportError(error instanceof Error ? error.message : "Errore import shapefile GIS");
    } finally {
      setShapefileImportBusy(null);
    }
  }

  async function rejectShapefileImportResult(importId: string) {
    const currentToken = token as string;
    setShapefileImportBusy("reject");
    setShapefileImportError(null);
    try {
      const response = await rejectGisShapefileImport(currentToken, importId);
      setShapefileImportResult(response);
      setShapefileImportPreview(null);
      setShapefileImportPreviewOpen(false);
      setShapefileImportPreviewError(null);
      setImportChangeRequestResult(null);
      setImportChangeRequestError(null);
    } catch (error) {
      setShapefileImportError(error instanceof Error ? error.message : "Errore reject import shapefile GIS");
    } finally {
      setShapefileImportBusy(null);
    }
  }

  async function loadShapefileImportPreview(importId: string) {
    const currentToken = token as string;
    setShapefileImportBusy("preview");
    setShapefileImportPreviewError(null);
    try {
      const response = await previewGisShapefileImport(currentToken, importId, 5, 0);
      setShapefileImportPreview(response);
      setShapefileImportPreviewOpen(true);
    } catch (error) {
      setShapefileImportPreviewError(error instanceof Error ? error.message : "Errore preview import shapefile GIS");
    } finally {
      setShapefileImportBusy(null);
    }
  }

  async function publishShapefileImportResult(importId: string) {
    const currentToken = token as string;
    setShapefileImportBusy("publish");
    setShapefileImportError(null);
    try {
      const response = await publishGisShapefileImport(currentToken, importId);
      setShapefileImportResult(response);
      void loadCatalog(filters);
    } catch (error) {
      setShapefileImportError(error instanceof Error ? error.message : "Errore publish import shapefile GIS");
    } finally {
      setShapefileImportBusy(null);
    }
  }

  async function createChangeRequestsFromImport(importId: string) {
    const currentToken = token as string;
    const targetLayerId = importChangeRequestForm.targetLayerId.trim();
    const limit = Number.parseInt(importChangeRequestForm.limit, 10);
    const offset = Number.parseInt(importChangeRequestForm.offset, 10);
    if (!targetLayerId || !Number.isInteger(limit) || limit < 1 || limit > 100 || !Number.isInteger(offset) || offset < 0) {
      setImportChangeRequestError("Seleziona un layer ufficiale e usa limite 1-100 con offset positivo.");
      return;
    }

    setImportChangeRequestBusy(true);
    setImportChangeRequestError(null);
    try {
      const response = await createGisShapefileImportChangeRequests(currentToken, importId, {
        targetLayerId,
        justification: importChangeRequestForm.justification,
        limit,
        offset,
      });
      setImportChangeRequestResult(response);
      const targetLayer = layers.find((layer) => layer.id === targetLayerId);
      /* v8 ignore next -- defensive guard for stale catalogs after permission changes */
      if (targetLayer) void loadChangeRequests(targetLayer, changeRequestFilters);
    } catch (error) {
      setImportChangeRequestError(error instanceof Error ? error.message : "Errore creazione change request da import");
    } finally {
      setImportChangeRequestBusy(false);
    }
  }

  async function downloadQgisProject() {
    const currentToken = token as string;
    setQgisProjectBusy(true);
    setQgisProjectError(null);
    try {
      const blob = await downloadGisQgisProject(currentToken);
      downloadBrowserBlob(blob, "gaia-gis-platform.qgz");
    } catch (error) {
      setQgisProjectError(error instanceof Error ? error.message : "Errore download progetto QGIS");
    } finally {
      setQgisProjectBusy(false);
    }
  }

  async function loadOgcPoc() {
    const currentToken = token as string;
    setOgcPocBusy(true);
    setOgcPocError(null);
    try {
      const response = await getGisOgcPoc(currentToken);
      setOgcPoc(response);
    } catch (error) {
      setOgcPocError(error instanceof Error ? error.message : "Errore caricamento POC OGC");
    } finally {
      setOgcPocBusy(false);
    }
  }

  function applyAnnotationFilters(layer: GisCatalogLayer) {
    void loadAnnotations(layer, annotationFilters);
  }

  function applyChangeRequestFilters(layer: GisCatalogLayer) {
    void loadChangeRequests(layer, changeRequestFilters);
  }

  const fallbackWorkspaces = new Set<string>();
  let fallbackInactiveCount = 0;
  let fallbackOfficialPostgisCount = 0;
  for (const layer of layers) {
    fallbackWorkspaces.add(layer.workspace);
    if (!layer.is_active) fallbackInactiveCount += 1;
    if (layer.official_source === "postgis") fallbackOfficialPostgisCount += 1;
  }
  const importChangeRequestTargetLayers = layers.filter(
    (layer) => layer.is_active && layer.source_type === "postgis" && layer.can_edit,
  );

  if (!token) {
    return (
      <article className="rounded-[28px] border border-[#d8e4db] bg-white p-6 shadow-sm">
        <p className="text-sm font-semibold text-[#1D4E35]">Sessione catalogo in caricamento.</p>
        <p className="mt-2 text-sm text-gray-500">Il catalogo GIS viene caricato dopo la verifica della sessione GAIA.</p>
      </article>
    );
  }

  return (
    <div className="space-y-6">
      <section className="relative overflow-hidden rounded-[36px] border border-[#b7c9b3] bg-[#132018] text-white shadow-[0_26px_80px_rgba(25,48,32,0.26)]">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_12%,rgba(205,231,182,0.26),transparent_32%),radial-gradient(circle_at_88%_6%,rgba(122,173,151,0.32),transparent_28%),linear-gradient(135deg,#132018_0%,#243a27_48%,#6b5b32_100%)]" />
        <div className="absolute -bottom-20 right-10 h-52 w-52 rounded-full border border-white/15 bg-white/10 blur-sm" />
        <div className="relative grid gap-8 p-6 lg:grid-cols-[1.45fr_0.85fr] lg:p-9">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[#d6e8bd]">GAIA GIS Platform</p>
            <h2 className="mt-5 text-4xl font-semibold tracking-tight lg:text-5xl">Catalogo delle mappe</h2>
            <p className="mt-5 max-w-2xl text-base leading-7 text-[#edf4e7]">
              Qui trovi tutte le mappe (layer) disponibili in GAIA. Per ogni mappa vedi subito di cosa si tratta,
              se e aggiornata e cosa puoi farci: consultarla, lasciare una nota o proporre una correzione.
            </p>
            <div className="mt-6 flex flex-wrap gap-2 text-xs font-semibold uppercase tracking-[0.16em]">
              <span className="rounded-full border border-white/15 bg-white/10 px-3 py-2 text-[#eef7e8]">Layer = una mappa tematica</span>
              <span className="rounded-full border border-white/15 bg-white/10 px-3 py-2 text-[#eef7e8]">Workspace = gruppo di mappe</span>
              <span className="rounded-full border border-white/15 bg-white/10 px-3 py-2 text-[#eef7e8]">Permesso = cosa puoi fare</span>
            </div>
          </div>
          <div className="rounded-[30px] border border-white/15 bg-[#f8f5dc]/95 p-5 text-[#17231d] shadow-[0_18px_44px_rgba(0,0,0,0.18)]">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#6a7340]">In sintesi</p>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <MetricTile label="Mappe disponibili" value={String(dashboard?.total_layers ?? layers.length)} />
              <MetricTile label="Gruppi di mappe" value={String(dashboard?.workspace_count ?? fallbackWorkspaces.size)} />
              <MetricTile
                label="Fonti ufficiali"
                value={String(dashboard?.official_source_counts.postgis ?? fallbackOfficialPostgisCount)}
              />
              <MetricTile label="Non attive" value={String(dashboard?.inactive_layers ?? fallbackInactiveCount)} />
            </div>
            <p className="mt-4 rounded-2xl bg-[#17231d] px-4 py-3 text-xs leading-5 text-[#dcebd0]">
              Non serve conoscere i termini tecnici: ogni scheda spiega in chiaro cosa contiene la mappa e cosa puoi
              fare. I dettagli tecnici restano disponibili, ma nascosti di default.
            </p>
          </div>
        </div>
      </section>

      <details className="group rounded-[28px] border border-[#d9dfd6] bg-white shadow-sm">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3 p-5 [&::-webkit-details-marker]:hidden">
          <span>
            <span className="block text-xs font-semibold uppercase tracking-[0.22em] text-[#66816d]">Guida rapida</span>
            <span className="mt-1 block text-lg font-semibold text-gray-950">Come funziona il catalogo, in parole semplici</span>
          </span>
          <span className="rounded-full bg-[#EAF3E8] px-4 py-2 text-xs font-semibold text-[#1D4E35] group-open:hidden">Apri la guida</span>
          <span className="hidden rounded-full bg-gray-100 px-4 py-2 text-xs font-semibold text-gray-600 group-open:inline">Chiudi la guida</span>
        </summary>
        <div className="grid gap-3 px-5 pb-5 md:grid-cols-2 xl:grid-cols-4">
          {catalogGuides.map((guide) => (
            <GuideCard key={guide.title} eyebrow={guide.eyebrow} title={guide.title} body={guide.body} />
          ))}
        </div>
      </details>

      <section className="rounded-[28px] border border-[#d9dfd6] bg-white p-5 shadow-sm">
        <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#66816d]">Cerca una mappa</p>
            <h3 className="mt-2 text-xl font-semibold text-gray-950">Filtra l&apos;elenco delle mappe qui sotto</h3>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-500">
              Puoi restringere l&apos;elenco per gruppo di mappe (workspace) o per stato. Cercare non modifica nessun
              dato: e solo un modo per trovare prima quello che ti serve.
            </p>
          </div>
          <span className="rounded-full bg-[#f4f0d0] px-4 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-[#6a7340]">
            Solo consultazione
          </span>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
            Workspace
            <span className="mt-1 block normal-case tracking-normal text-gray-400">Il gruppo di mappe, per esempio catasto o rete.</span>
            <input
              className="form-control mt-2"
              value={filters.workspace}
              aria-label="Workspace"
              onChange={(event) => setFilter("workspace", event.target.value)}
              placeholder="catasto"
            />
          </label>
          <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
            Dominio
            <span className="mt-1 block normal-case tracking-normal text-gray-400">Il modulo GAIA responsabile del dato.</span>
            <input
              className="form-control mt-2"
              value={filters.domainModule}
              aria-label="Dominio"
              onChange={(event) => setFilter("domainModule", event.target.value)}
              placeholder="catasto"
            />
          </label>
          <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
            Stato
            <span className="mt-1 block normal-case tracking-normal text-gray-400">Mostra tutte le mappe o solo quelle in uso.</span>
            <select
              className="form-control mt-2"
              value={filters.active}
              aria-label="Stato"
              onChange={(event) => setFilter("active", event.target.value)}
            >
              <option value="all">Tutte</option>
              <option value="active">Solo attive</option>
              <option value="inactive">Solo non attive</option>
            </select>
          </label>
        </div>
        <details className="mt-4 rounded-2xl border border-gray-100 bg-gray-50 p-4">
          <summary className="cursor-pointer text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
            Filtri tecnici (facoltativi)
          </summary>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
              Source
              <span className="mt-1 block normal-case tracking-normal text-gray-400">Tecnologia che alimenta il layer, per esempio postgis.</span>
              <input
                className="form-control mt-2"
                value={filters.sourceType}
                aria-label="Source"
                onChange={(event) => setFilter("sourceType", event.target.value)}
                placeholder="postgis"
              />
            </label>
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
              Ufficiale
              <span className="mt-1 block normal-case tracking-normal text-gray-400">Sistema autorevole da cui arriva il dato valido.</span>
              <input
                className="form-control mt-2"
                value={filters.officialSource}
                aria-label="Ufficiale"
                onChange={(event) => setFilter("officialSource", event.target.value)}
                placeholder="postgis"
              />
            </label>
          </div>
        </details>
        <div className="mt-4 flex flex-wrap gap-3">
          <button className="btn-primary" type="button" disabled={isLoading} onClick={() => void loadCatalog(filters)}>
            {isLoading ? "Caricamento..." : "Applica filtri"}
          </button>
          <button className="btn-secondary" type="button" disabled={isLoading} onClick={resetFilters}>
            Reset
          </button>
        </div>
      </section>

      {loadError ? (
        <article className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-700">
          {loadError}
        </article>
      ) : null}

      {layers.length === 0 && !isLoading ? (
        <article className="rounded-[28px] border border-dashed border-[#b8cabb] bg-[#f7faf7] p-8 text-center">
          <p className="text-lg font-semibold text-gray-900">Nessuna mappa trovata con questi filtri</p>
          <p className="mt-2 text-sm text-gray-500">
            Prova ad allargare i filtri con il pulsante Reset. Se ti aspettavi di vedere una mappa, chiedi a chi
            amministra il GIS di verificare i permessi del tuo account.
          </p>
        </article>
      ) : (
        <div className="grid gap-4">
          {layers.map((layer) => {
            const workspaceHref = domainWorkspaceHref(layer);
            return (
              <article key={layer.id} className="rounded-[28px] border border-[#d9dfd6] bg-white p-5 shadow-sm">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-[#EAF3E8] px-3 py-1 text-xs font-semibold text-[#1D4E35]">
                        Workspace: {layer.workspace}
                      </span>
                      <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-600">
                        Stato: {layer.is_active ? "in uso" : "non attiva"}
                      </span>
                      <span className="rounded-full bg-[#eef3f9] px-3 py-1 text-xs font-semibold text-[#315d80]">
                        Permesso effettivo: puoi {accessLevelDescriptions[layer.effective_access_level]}
                      </span>
                    </div>
                    <h3 className="mt-3 text-xl font-semibold text-gray-950">{layer.title}</h3>
                    <p className="mt-1 text-sm text-gray-500">{formatValue(layer.description)}</p>
                    <p className="mt-2 text-xs leading-5 text-gray-500">
                      Curata dal modulo {layer.domain_module}. Fonte dei dati: {layer.official_source}.
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {workspaceHref ? (
                      <Link className="btn-secondary" href={workspaceHref}>
                        Apri workspace Catasto
                      </Link>
                    ) : null}
                    {layer.can_manage ? (
                      <button className="btn-secondary" type="button" onClick={() => togglePermissionPanel(layer)}>
                        {permissionsLayerId === layer.id ? "Chiudi permessi" : "Gestisci permessi"}
                      </button>
                    ) : null}
                    {layer.can_view ? (
                      <button className="btn-secondary" type="button" onClick={() => toggleAnnotationPanel(layer)}>
                        {annotationsLayerId === layer.id ? "Chiudi note" : "Note"}
                      </button>
                    ) : null}
                    {layer.can_view ? (
                      <button className="btn-secondary" type="button" onClick={() => toggleChangeRequestPanel(layer)}>
                        {changeRequestsLayerId === layer.id ? "Chiudi richieste di modifica" : "Richieste di modifica"}
                      </button>
                    ) : null}
                  </div>
                </div>

                <details className="mt-5 rounded-2xl border border-gray-100 bg-gray-50 p-4">
                  <summary className="cursor-pointer text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                    Dettagli tecnici (per operatori GIS)
                  </summary>
                  <p className="mt-3 font-mono text-xs text-gray-400">{layer.name}</p>
                  <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                    <CatalogFact
                      label="PostGIS"
                      value={`${formatValue(layer.postgis_schema)}.${formatValue(layer.postgis_table)}`}
                      description={layerFactDescriptions.postgis}
                    />
                    <CatalogFact
                      label="Geometry"
                      value={`${formatValue(layer.geometry_type)} - SRID ${formatValue(layer.srid)}`}
                      description={layerFactDescriptions.geometry}
                    />
                    <CatalogFact
                      label="Martin layer"
                      value={formatValue(layer.martin_layer_id)}
                      description={layerFactDescriptions.martin}
                    />
                    <CatalogFact
                      label="Feature id"
                      value={formatValue(layer.feature_id_column)}
                      description={layerFactDescriptions.featureId}
                    />
                    <CatalogFact label="Source type" value={layer.source_type} description={layerFactDescriptions.sourceType} />
                    <CatalogFact
                      label="Official source"
                      value={layer.official_source}
                      description={layerFactDescriptions.officialSource}
                    />
                    <CatalogFact label="QGIS mode" value={qgisMode(layer)} description={layerFactDescriptions.qgisMode} />
                    <CatalogFact label="Tile provider" value={tileProvider(layer)} description={layerFactDescriptions.tileProvider} />
                  </div>
                </details>

                {permissionsLayerId === layer.id && layer.can_manage ? (
                  <section className="mt-5 rounded-[24px] border border-[#d9dfd6] bg-[#f7faf7] p-4">
                    <p className="mb-3 text-sm leading-6 text-gray-600">
                      Qui decidi chi puo vedere o modificare questa mappa. Puoi dare un permesso a un ruolo (tutte le
                      persone con quel ruolo) o a un singolo utente.
                    </p>
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-end">
                      <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                        Principal
                        <select
                          className="form-control mt-2"
                          value={permissionForm.principalType}
                          onChange={(event) => setPermissionForm((currentForm) => updatePermissionForm(currentForm, "principalType", event.target.value))}
                        >
                          <option value="role">Ruolo</option>
                          <option value="user">Utente</option>
                        </select>
                      </label>
                      {permissionForm.principalType === "role" ? (
                        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                          Chiave ruolo
                          <select
                            className="form-control mt-2"
                            value={permissionForm.principalKey}
                            onChange={(event) => setPermissionForm((currentForm) => updatePermissionForm(currentForm, "principalKey", event.target.value))}
                          >
                            {applicationRoleOptions.map((role) => (
                              <option key={role} value={role}>
                                {role}
                              </option>
                            ))}
                          </select>
                        </label>
                      ) : (
                        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                          ID utente
                          <input
                            className="form-control mt-2"
                            value={permissionForm.principalKey}
                            onChange={(event) => setPermissionForm((currentForm) => updatePermissionForm(currentForm, "principalKey", event.target.value))}
                            placeholder="123"
                          />
                        </label>
                      )}
                      <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                        Livello GIS
                        <select
                          className="form-control mt-2"
                          value={permissionForm.accessLevel}
                          onChange={(event) => setPermissionForm((currentForm) => updatePermissionForm(currentForm, "accessLevel", event.target.value))}
                        >
                          {gisAccessLevels.map((level) => (
                            <option key={level} value={level}>
                              {level} - {accessLevelDescriptions[level]}
                            </option>
                          ))}
                        </select>
                      </label>
                      <button
                        className="btn-primary"
                        type="button"
                        disabled={permissionBusy === `save:${layer.id}`}
                        onClick={() => void savePermission(layer)}
                      >
                        {permissionBusy === `save:${layer.id}` ? "Salvataggio..." : "Salva permesso"}
                      </button>
                    </div>

                    {permissionError ? <p className="mt-3 text-sm font-medium text-red-700">{permissionError}</p> : null}

                    <div className="mt-4 grid gap-2">
                      {permissionBusy === `load:${layer.id}` ? (
                        <p className="text-sm text-gray-500">Caricamento permessi...</p>
                      ) : permissions.length === 0 ? (
                        <p className="text-sm text-gray-500">Nessun permesso esplicito configurato.</p>
                      ) : (
                        permissions.map((permission) => (
                          <div key={permission.id} className="flex flex-col gap-3 rounded-2xl border border-white bg-white p-3 shadow-sm md:flex-row md:items-center md:justify-between">
                            <div>
                              <p className="text-sm font-semibold text-gray-900">
                                {permission.principal_type}:{permission.principal_key}
                              </p>
                              <p className="mt-1 text-xs text-gray-500">
                                Livello {permission.access_level}: puo {accessLevelDescriptions[permission.access_level]}
                              </p>
                            </div>
                            <button
                              className="btn-secondary"
                              type="button"
                              disabled={permissionBusy === `revoke:${permission.id}`}
                              onClick={() => void revokePermission(layer, permission.id)}
                            >
                              {permissionBusy === `revoke:${permission.id}` ? "Revoca..." : "Revoca"}
                            </button>
                          </div>
                        ))
                      )}
                    </div>
                  </section>
                ) : null}

                {annotationsLayerId === layer.id ? (
                  <section className="mt-5 rounded-[24px] border border-[#d9dfd6] bg-white p-4 shadow-sm">
                    <p className="mb-3 text-sm leading-6 text-gray-600">
                      Le note servono a segnalare qualcosa su questa mappa, ad esempio un dato da verificare sul campo.
                      Non modificano i dati.
                    </p>
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-end">
                      <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                        Stato note
                        <select
                          className="form-control mt-2"
                          value={annotationFilters.status}
                          onChange={(event) => setAnnotationFilters((currentFilters) => ({
                            ...currentFilters,
                            status: event.target.value as AnnotationStatusFilter,
                          }))}
                        >
                          <option value="all">Tutte</option>
                          {annotationStatuses.map((status) => (
                            <option key={status} value={status}>
                              {annotationStatusLabels[status]}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                        Feature id
                        <input
                          className="form-control mt-2"
                          value={annotationFilters.featureId}
                          onChange={(event) => setAnnotationFilters((currentFilters) => ({ ...currentFilters, featureId: event.target.value }))}
                          placeholder="parcel-1"
                        />
                      </label>
                      <button className="btn-secondary" type="button" onClick={() => applyAnnotationFilters(layer)}>
                        Filtra note
                      </button>
                    </div>

                    {layer.can_annotate ? (
                      <div className="mt-4 grid gap-3 rounded-2xl border border-[#edf2ee] bg-[#f7faf7] p-4 md:grid-cols-[0.7fr_1fr_1.4fr_auto] md:items-end">
                        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                          Feature
                          <input
                            className="form-control mt-2"
                            value={annotationForm.featureId}
                            onChange={(event) => setAnnotationForm((currentForm) => updateAnnotationForm(currentForm, "featureId", event.target.value))}
                            placeholder="opzionale"
                            disabled={Boolean(editingAnnotationId)}
                          />
                        </label>
                        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                          Titolo
                          <input
                            className="form-control mt-2"
                            value={annotationForm.title}
                            onChange={(event) => setAnnotationForm((currentForm) => updateAnnotationForm(currentForm, "title", event.target.value))}
                            placeholder="Nota campo"
                          />
                        </label>
                        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                          Testo
                          <input
                            className="form-control mt-2"
                            value={annotationForm.body}
                            onChange={(event) => setAnnotationForm((currentForm) => updateAnnotationForm(currentForm, "body", event.target.value))}
                            placeholder="Descrizione annotazione"
                          />
                        </label>
                        <div className="flex gap-2">
                          <button
                            className="btn-primary"
                            type="button"
                            disabled={annotationBusy === `save:${layer.id}`}
                            onClick={() => void saveAnnotation(layer)}
                          >
                            {annotationBusy === `save:${layer.id}`
                              ? "Salvataggio..."
                              : editingAnnotationId
                                ? "Aggiorna nota"
                                : "Crea nota"}
                          </button>
                          {editingAnnotationId ? (
                            <button className="btn-secondary" type="button" onClick={resetAnnotationForm}>
                              Annulla
                            </button>
                          ) : null}
                        </div>
                      </div>
                    ) : null}

                    {annotationError ? <p className="mt-3 text-sm font-medium text-red-700">{annotationError}</p> : null}

                    <div className="mt-4 grid gap-2">
                      {annotationBusy === `load:${layer.id}` ? (
                        <p className="text-sm text-gray-500">Caricamento annotazioni...</p>
                      ) : annotations.length === 0 ? (
                        <p className="text-sm text-gray-500">Nessuna annotazione nel filtro corrente.</p>
                      ) : (
                        annotations.map((annotation) => (
                          <div key={annotation.id} className="rounded-2xl border border-[#edf2ee] bg-[#fbfdfb] p-4">
                            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                              <div>
                                <div className="flex flex-wrap items-center gap-2">
                                  <span className="rounded-full bg-[#EAF3E8] px-2.5 py-1 text-xs font-semibold text-[#1D4E35]">
                                    {annotationStatusLabels[annotation.status]}
                                  </span>
                                  <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-semibold text-gray-500">
                                    {annotation.feature_id || "feature non associata"}
                                  </span>
                                </div>
                                <p className="mt-3 text-sm font-semibold text-gray-950">{annotation.title}</p>
                                <p className="mt-1 text-sm text-gray-600">{annotation.body}</p>
                              </div>
                              <div className="flex flex-wrap gap-2">
                                {layer.can_annotate && annotation.status !== "closed" && annotation.status !== "rejected" ? (
                                  <>
                                    <button className="btn-secondary" type="button" onClick={() => editAnnotation(annotation)}>
                                      Modifica
                                    </button>
                                    <button
                                      className="btn-secondary"
                                      type="button"
                                      disabled={annotationBusy === `status:${annotation.id}:in_review`}
                                      onClick={() => void changeAnnotationStatus(layer, annotation.id, "in_review")}
                                    >
                                      In revisione
                                    </button>
                                  </>
                                ) : null}
                                {layer.can_approve && annotation.status !== "closed" && annotation.status !== "rejected" ? (
                                  <>
                                    <button
                                      className="btn-secondary"
                                      type="button"
                                      disabled={annotationBusy === `status:${annotation.id}:closed`}
                                      onClick={() => void changeAnnotationStatus(layer, annotation.id, "closed")}
                                    >
                                      Chiudi
                                    </button>
                                    <button
                                      className="btn-secondary"
                                      type="button"
                                      disabled={annotationBusy === `status:${annotation.id}:rejected`}
                                      onClick={() => void changeAnnotationStatus(layer, annotation.id, "rejected")}
                                    >
                                      Rigetta
                                    </button>
                                  </>
                                ) : null}
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </section>
                ) : null}

                {changeRequestsLayerId === layer.id ? (
                  <section className="mt-5 rounded-[24px] border border-[#d9dfd6] bg-[#fbfcf8] p-4 shadow-sm">
                    <p className="mb-3 text-sm leading-6 text-gray-600">
                      Qui si propongono correzioni ai dati della mappa. Nessuna modifica viene applicata finche una
                      persona autorizzata non la approva.
                    </p>
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                      <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                        Stato richiesta
                        <select
                          className="form-control mt-2"
                          value={changeRequestFilters.status}
                          onChange={(event) => setChangeRequestFilters({ status: event.target.value as ChangeRequestStatusFilter })}
                        >
                          <option value="all">Tutte</option>
                          {changeRequestStatuses.map((status) => (
                            <option key={status} value={status}>
                              {changeRequestStatusLabels[status]}
                            </option>
                          ))}
                        </select>
                      </label>
                      <button className="btn-secondary" type="button" onClick={() => applyChangeRequestFilters(layer)}>
                        Filtra richieste
                      </button>
                    </div>

                    {layer.can_edit ? (
                      <div className="mt-4 grid gap-3 rounded-2xl border border-[#e3eadf] bg-white p-4 lg:grid-cols-[0.7fr_0.8fr_1.6fr_1fr_auto] lg:items-end">
                        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                          Feature
                          <input
                            className="form-control mt-2"
                            value={changeRequestForm.featureId}
                            onChange={(event) => setChangeRequestForm((currentForm) => updateChangeRequestForm(currentForm, "featureId", event.target.value))}
                            placeholder="parcel-42"
                          />
                        </label>
                        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                          Tipo
                          <select
                            className="form-control mt-2"
                            value={changeRequestForm.changeType}
                            onChange={(event) => setChangeRequestForm((currentForm) => updateChangeRequestForm(currentForm, "changeType", event.target.value))}
                          >
                            {changeRequestTypes.map((changeType) => (
                              <option key={changeType} value={changeType}>
                                {changeRequestTypeLabels[changeType]}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                          Payload JSON
                          <textarea
                            className="form-control mt-2 min-h-28 font-mono text-xs"
                            value={changeRequestForm.payload}
                            onChange={(event) => setChangeRequestForm((currentForm) => updateChangeRequestForm(currentForm, "payload", event.target.value))}
                          />
                        </label>
                        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                          Motivazione
                          <input
                            className="form-control mt-2"
                            value={changeRequestForm.justification}
                            onChange={(event) => setChangeRequestForm((currentForm) => updateChangeRequestForm(currentForm, "justification", event.target.value))}
                            placeholder="Fonte rilievo"
                          />
                        </label>
                        <div className="flex gap-2">
                          <button
                            className="btn-primary"
                            type="button"
                            disabled={changeRequestBusy === `save:${layer.id}`}
                            onClick={() => void saveChangeRequest(layer)}
                          >
                            {changeRequestBusy === `save:${layer.id}`
                              ? "Salvataggio..."
                              : editingChangeRequestId
                                ? "Aggiorna richiesta"
                                : "Crea richiesta"}
                          </button>
                          {editingChangeRequestId ? (
                            <button className="btn-secondary" type="button" onClick={resetChangeRequestForm}>
                              Annulla
                            </button>
                          ) : null}
                        </div>
                      </div>
                    ) : null}

                    {layer.can_approve ? (
                      <label className="mt-4 block text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                        Note revisione
                        <input
                          className="form-control mt-2"
                          value={changeRequestForm.reviewNotes}
                          onChange={(event) => setChangeRequestForm((currentForm) => updateChangeRequestForm(currentForm, "reviewNotes", event.target.value))}
                          placeholder="Esito istruttoria"
                        />
                      </label>
                    ) : null}

                    {changeRequestError ? <p className="mt-3 text-sm font-medium text-red-700">{changeRequestError}</p> : null}

                    <div className="mt-4 grid gap-2">
                      {changeRequestBusy === `load:${layer.id}` ? (
                        <p className="text-sm text-gray-500">Caricamento change request...</p>
                      ) : changeRequests.length === 0 ? (
                        <p className="text-sm text-gray-500">Nessuna change request nel filtro corrente.</p>
                      ) : (
                        changeRequests.map((changeRequest) => {
                          const reviewable = changeRequest.status === "submitted" || changeRequest.status === "needs_changes";
                          return (
                            <div key={changeRequest.id} className="rounded-2xl border border-[#e3eadf] bg-white p-4">
                              <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
                                <div>
                                  <div className="flex flex-wrap items-center gap-2">
                                    <span className="rounded-full bg-[#EAF3E8] px-2.5 py-1 text-xs font-semibold text-[#1D4E35]">
                                      {changeRequestStatusLabels[changeRequest.status]}
                                    </span>
                                    <span className="rounded-full bg-[#eef3f9] px-2.5 py-1 text-xs font-semibold text-[#315d80]">
                                      {changeRequestTypeLabels[changeRequest.change_type]}
                                    </span>
                                    <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-semibold text-gray-500">
                                      {changeRequest.feature_id || "nuova feature"}
                                    </span>
                                  </div>
                                  <p className="mt-3 text-sm font-semibold text-gray-950">
                                    {changeRequest.justification || "Richiesta senza motivazione"}
                                  </p>
                                  <pre className="mt-2 max-h-52 overflow-auto rounded-xl bg-[#17231d] p-3 text-xs text-[#d7eadb]">
                                    {changeRequestPayloadLabel(changeRequest)}
                                  </pre>
                                  {changeRequest.review_notes ? (
                                    <p className="mt-2 text-xs font-medium text-gray-500">Review: {changeRequest.review_notes}</p>
                                  ) : null}
                                </div>
                                <div className="flex flex-wrap gap-2">
                                  {layer.can_edit && reviewable ? (
                                    <button className="btn-secondary" type="button" onClick={() => editChangeRequest(changeRequest)}>
                                      Modifica richiesta
                                    </button>
                                  ) : null}
                                  {layer.can_approve && reviewable ? (
                                    <>
                                      <button
                                        className="btn-secondary"
                                        type="button"
                                        disabled={changeRequestBusy === `status:${changeRequest.id}:needs_changes`}
                                        onClick={() => void changeChangeRequestStatus(changeRequest.id, "needs_changes")}
                                      >
                                        Richiedi modifiche
                                      </button>
                                      <button
                                        className="btn-secondary"
                                        type="button"
                                        disabled={changeRequestBusy === `status:${changeRequest.id}:approved`}
                                        onClick={() => void changeChangeRequestStatus(changeRequest.id, "approved")}
                                      >
                                        Approva
                                      </button>
                                      <button
                                        className="btn-secondary"
                                        type="button"
                                        disabled={changeRequestBusy === `status:${changeRequest.id}:rejected`}
                                        onClick={() => void changeChangeRequestStatus(changeRequest.id, "rejected")}
                                      >
                                        Rigetta richiesta
                                      </button>
                                    </>
                                  ) : null}
                                  {layer.can_approve && changeRequest.status === "approved" ? (
                                    <button
                                      className="btn-secondary"
                                      type="button"
                                      disabled={changeRequestBusy === `status:${changeRequest.id}:applied`}
                                      onClick={() => void changeChangeRequestStatus(changeRequest.id, "applied")}
                                    >
                                      Applica richiesta
                                    </button>
                                  ) : null}
                                </div>
                              </div>
                            </div>
                          );
                        })
                      )}
                    </div>
                  </section>
                ) : null}
              </article>
            );
          })}
        </div>
      )}

      {isLoading ? (
        <div className="flex items-center gap-2 rounded-2xl border border-[#d9dfd6] bg-white px-4 py-3 text-sm text-gray-500">
          <RefreshIcon className="h-4 w-4 animate-spin" />
          Caricamento catalogo GIS...
        </div>
      ) : null}

      <details className="group rounded-[28px] border border-[#d9dfd6] bg-white shadow-sm">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3 p-5 [&::-webkit-details-marker]:hidden">
          <span>
            <span className="block text-xs font-semibold uppercase tracking-[0.22em] text-[#66816d]">Strumenti per utenti esperti</span>
            <span className="mt-1 block text-lg font-semibold text-gray-950">Carica shapefile e lavora con QGIS Desktop</span>
            <span className="mt-1 block text-sm text-gray-500">
              Servono solo a chi importa dati esterni o usa il programma QGIS. Per consultare le mappe non ti servono.
            </span>
          </span>
          <span className="rounded-full bg-[#EAF3E8] px-4 py-2 text-xs font-semibold text-[#1D4E35] group-open:hidden">Apri strumenti</span>
          <span className="hidden rounded-full bg-gray-100 px-4 py-2 text-xs font-semibold text-gray-600 group-open:inline">Chiudi strumenti</span>
        </summary>
        <div className="grid gap-5 px-5 pb-5 xl:grid-cols-2">
        <article className="overflow-hidden rounded-[30px] border border-[#d6dfd2] bg-[#fbfbf2] shadow-sm">
          <div className="border-b border-[#e3eadf] bg-[linear-gradient(135deg,#f6f0c4,#e0ecd7)] p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#6a7340]">Import dati esterni</p>
            <h3 className="mt-2 text-2xl font-semibold text-[#17231d]">Carica shapefile da ZIP</h3>
            <p className="mt-2 text-sm leading-6 text-[#526154]">
              Se hai ricevuto uno shapefile dal campo o da un fornitore, carica qui lo ZIP completo. GAIA lo controlla
              in staging: i layer ufficiali non vengono modificati automaticamente.
            </p>
          </div>
          <div className="p-5">
            <div className="flex flex-wrap gap-2" aria-label="Componenti shapefile richiesti">
              {shapefileRequirements.map((extension) => (
                <span key={extension} className="rounded-full bg-white px-3 py-1.5 font-mono text-xs font-semibold text-[#315d80] shadow-sm">
                  {extension}
                </span>
              ))}
            </div>
            <p className="mt-3 text-xs leading-5 text-[#526154]">
              Lo ZIP deve contenere almeno questi file con lo stesso nome base. Se manca un componente, GAIA blocca
              l&apos;import e spiega cosa correggere.
            </p>
            <ol className="mt-5 space-y-3">
              {shapefilePipeline.map((step, index) => (
                <li key={step} className="flex gap-3 rounded-2xl border border-[#e4eadf] bg-white p-3 text-sm text-gray-600">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#17231d] text-xs font-semibold text-white">
                    {index + 1}
                  </span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
            <div className="mt-5 rounded-[24px] border border-[#e4eadf] bg-white p-4">
              <p className="text-sm font-semibold text-[#17231d]">Carica e controlla il file</p>
              <p className="mt-1 text-xs leading-5 text-gray-500">
                Il file viene letto in una tabella temporanea di controllo: niente viene pubblicato subito. GAIA
                propone automaticamente area, nome layer, titolo e codifica; modifica i campi solo se la proposta non e
                corretta.
              </p>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                  <span>File ZIP dello shapefile</span>
                  <span className="mt-1 block normal-case tracking-normal text-gray-400">Un solo archivio .zip con .shp, .shx, .dbf e .prj.</span>
                  <input
                    className="form-control mt-2"
                    type="file"
                    accept=".zip,application/zip"
                    aria-label="File ZIP dello shapefile"
                    onChange={(event) => handleShapefileFileChange(event.target.files?.[0] ?? null)}
                  />
                </label>
                <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                  <span>Area di lavoro</span>
                  <span className="mt-1 block normal-case tracking-normal text-gray-400">Compilata dal layer riconosciuto o dal nome file.</span>
                  <input
                    className="form-control mt-2"
                    value={shapefileImportForm.workspace}
                    aria-label="Area di lavoro"
                    onChange={(event) => setShapefileImportValue("workspace", event.target.value)}
                    placeholder="rete"
                  />
                </label>
                <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                  <span>Dominio responsabile</span>
                  <span className="mt-1 block normal-case tracking-normal text-gray-400">Derivato dal layer riconosciuto, se presente.</span>
                  <input
                    className="form-control mt-2"
                    value={shapefileImportForm.domainModule}
                    aria-label="Dominio responsabile"
                    onChange={(event) => setShapefileImportValue("domainModule", event.target.value)}
                    placeholder="network"
                  />
                </label>
                <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                  <span>Nome tecnico layer</span>
                  <span className="mt-1 block normal-case tracking-normal text-gray-400">Identificativo stabile senza spazi, usato da API e database.</span>
                  <input
                    className="form-control mt-2"
                    value={shapefileImportForm.targetLayerName}
                    aria-label="Nome tecnico layer"
                    onChange={(event) => setShapefileImportValue("targetLayerName", event.target.value)}
                    placeholder="rete_condotte_upload"
                  />
                </label>
                <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                  <span>Titolo visibile agli utenti</span>
                  <span className="mt-1 block normal-case tracking-normal text-gray-400">Nome leggibile che gli utenti vedranno nel catalogo.</span>
                  <input
                    className="form-control mt-2"
                    value={shapefileImportForm.targetLayerTitle}
                    aria-label="Titolo visibile agli utenti"
                    onChange={(event) => setShapefileImportValue("targetLayerTitle", event.target.value)}
                    placeholder="Rete condotte upload"
                  />
                </label>
                <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                  <span>Sistema coordinate</span>
                  <span className="mt-1 block normal-case tracking-normal text-gray-400">Automatico dal .prj se contiene EPSG; compila solo se GAIA non lo riconosce.</span>
                  <input
                    className="form-control mt-2"
                    type="number"
                    min="1"
                    value={shapefileImportForm.sourceSrid}
                    aria-label="Sistema coordinate"
                    onChange={(event) => setShapefileImportValue("sourceSrid", event.target.value)}
                    placeholder="automatico da .prj"
                  />
                </label>
                <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                  <span>Fonte dei dati</span>
                  <span className="mt-1 block normal-case tracking-normal text-gray-400">Origine del file, ad esempio rilievo campo, fornitore o survey.</span>
                  <input
                    className="form-control mt-2"
                    value={shapefileImportForm.officialSource}
                    aria-label="Fonte dei dati"
                    onChange={(event) => setShapefileImportValue("officialSource", event.target.value)}
                    placeholder="survey"
                  />
                </label>
                <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                  <span>Codifica testo</span>
                  <span className="mt-1 block normal-case tracking-normal text-gray-400">Vuoto = usa il .cpg dello ZIP, altrimenti utf-8.</span>
                  <input
                    className="form-control mt-2"
                    value={shapefileImportForm.encoding}
                    aria-label="Codifica testo"
                    onChange={(event) => setShapefileImportValue("encoding", event.target.value)}
                    placeholder="automatico"
                  />
                </label>
              </div>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <button
                  className="btn-primary"
                  type="button"
                  disabled={shapefileImportBusy === "upload"}
                  onClick={() => void submitShapefileImport()}
                >
                  {shapefileImportBusy === "upload" ? "Controllo file..." : "Carica e controlla file"}
                </button>
                <span className="text-xs font-medium text-gray-500">
                  Nessun dato ufficiale viene sovrascritto durante questo passaggio.
                </span>
              </div>
              {shapefileImportError ? <p className="mt-3 text-sm font-medium text-red-700">{shapefileImportError}</p> : null}
              {shapefileImportResult ? (
                <div className="mt-4 rounded-2xl border border-[#dce8ed] bg-[#f5fbfc] p-4">
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div>
                      <p className="text-sm font-semibold text-[#17231d]">Import validato</p>
                      <p className="mt-1 text-xs text-gray-500">
                        Stato {shapefileImportStatusLabels[shapefileImportResult.status]} - {shapefileImportResult.feature_count} feature -{" "}
                        {formatValue(shapefileImportResult.geometry_type)}
                      </p>
                      <p className="mt-2 font-mono text-xs text-gray-500">
                        Staging PostGIS: {formatValue(shapefileImportResult.staging_schema)}.
                        {shapefileImportResult.staging_table}
                      </p>
                      <p className="mt-1 font-mono text-xs text-gray-400">{shapefileImportResult.checksum_sha256}</p>
                      {shapefileImportResult.published_layer_id ? (
                        <p className="mt-2 text-xs font-semibold text-[#315d80]">
                          Layer catalogo creato: {shapefileImportResult.published_layer_id}
                        </p>
                      ) : null}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {shapefileImportResult.status === "validated" ? (
                        <button
                          className="btn-primary"
                          type="button"
                          disabled={shapefileImportBusy === "publish"}
                          onClick={() => void publishShapefileImportResult(shapefileImportResult.id)}
                        >
                          {shapefileImportBusy === "publish" ? "Pubblicazione..." : "Pubblica nel catalogo"}
                        </button>
                      ) : null}
                      {shapefileImportResult.status === "validated" || shapefileImportResult.status === "published" ? (
                        <button
                          className="btn-secondary"
                          type="button"
                          disabled={shapefileImportBusy === "preview"}
                          onClick={() => void loadShapefileImportPreview(shapefileImportResult.id)}
                        >
                          Vedi anteprima staging
                        </button>
                      ) : null}
                      {shapefileImportResult.status !== "rejected" && shapefileImportResult.status !== "published" ? (
                        <button
                          className="btn-secondary"
                          type="button"
                          disabled={shapefileImportBusy === "reject"}
                          onClick={() => void rejectShapefileImportResult(shapefileImportResult.id)}
                        >
                          {shapefileImportBusy === "reject" ? "Reject..." : "Rigetta import"}
                        </button>
                      ) : null}
                    </div>
                  </div>
                  {shapefileImportPreviewError ? (
                    <p className="mt-3 text-sm font-medium text-red-700">{shapefileImportPreviewError}</p>
                  ) : null}
                  {shapefileImportPreview ? (
                    <div className="mt-4 flex flex-col gap-3 rounded-2xl border border-[#c6dfe8] bg-white p-4 md:flex-row md:items-center md:justify-between">
                      <div>
                        <p className="text-sm font-semibold text-[#17231d]">Anteprima GIS pronta</p>
                        <p className="mt-1 text-xs text-gray-500">
                          {shapefileImportPreview.returned_count} feature mostrate su {shapefileImportPreview.feature_count}. Apri la modal per controllare attributi e geometria prima di pubblicare.
                        </p>
                      </div>
                      <button className="btn-secondary" type="button" onClick={() => setShapefileImportPreviewOpen(true)}>
                        Apri anteprima GIS
                      </button>
                    </div>
                  ) : null}
                  {shapefileImportResult.status === "validated" || shapefileImportResult.status === "published" ? (
                    <div className="mt-4 rounded-2xl border border-[#d8dec8] bg-[#fffdf2] p-4">
                      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                        <div>
                          <p className="text-sm font-semibold text-[#17231d]">Impatta un layer ufficiale?</p>
                          <p className="mt-1 text-xs leading-5 text-gray-600">
                            Non sovrascrivere il dato vivo: scegli il layer ufficiale e GAIA crea change request
                            `feature_create` dalle feature dello staging. Un approvatore decide cosa applicare.
                          </p>
                        </div>
                        {importChangeRequestResult ? (
                          <span className="rounded-full bg-[#e8f1df] px-3 py-1.5 text-xs font-semibold text-[#1d4e35]">
                            {importChangeRequestResult.created_count} nuove / {importChangeRequestResult.existing_count} gia presenti
                          </span>
                        ) : null}
                      </div>
                      {importChangeRequestTargetLayers.length > 0 ? (
                        <>
                          <div className="mt-4 grid gap-3 md:grid-cols-[1.4fr_0.5fr_0.5fr]">
                            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                              Layer ufficiale target
                              <select
                                className="form-control mt-2"
                                value={importChangeRequestForm.targetLayerId}
                                onChange={(event) => setImportChangeRequestValue("targetLayerId", event.target.value)}
                              >
                                <option value="">Seleziona layer editabile</option>
                                {importChangeRequestTargetLayers.map((layer) => (
                                  <option key={layer.id} value={layer.id}>
                                    {layer.workspace} / {layer.title}
                                  </option>
                                ))}
                              </select>
                            </label>
                            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                              Feature per batch
                              <input
                                className="form-control mt-2"
                                type="number"
                                min="1"
                                max="100"
                                value={importChangeRequestForm.limit}
                                onChange={(event) => setImportChangeRequestValue("limit", event.target.value)}
                              />
                            </label>
                            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                              Offset
                              <input
                                className="form-control mt-2"
                                type="number"
                                min="0"
                                value={importChangeRequestForm.offset}
                                onChange={(event) => setImportChangeRequestValue("offset", event.target.value)}
                              />
                            </label>
                          </div>
                          <label className="mt-3 block text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                            Motivazione change request da import
                            <textarea
                              className="form-control mt-2 min-h-20"
                              value={importChangeRequestForm.justification}
                              onChange={(event) => setImportChangeRequestValue("justification", event.target.value)}
                              placeholder="Esempio: rilievo campo del 15/07/2026 da validare sul layer ufficiale"
                            />
                          </label>
                          <div className="mt-4 flex flex-wrap items-center gap-3">
                            <button
                              className="btn-primary"
                              type="button"
                              disabled={importChangeRequestBusy}
                              onClick={() => void createChangeRequestsFromImport(shapefileImportResult.id)}
                            >
                              {importChangeRequestBusy ? "Creazione richieste..." : "Crea change request da import"}
                            </button>
                            <span className="text-xs font-medium text-gray-500">
                              Batch corrente: max {importChangeRequestForm.limit} feature dallo staging.
                            </span>
                          </div>
                        </>
                      ) : (
                        <p className="mt-4 rounded-xl bg-white px-3 py-2 text-sm text-[#76560c]">
                          Nessun layer ufficiale editabile visibile. Chiedi a un admin GIS di assegnare un permesso editor
                          sul layer target.
                        </p>
                      )}
                      {importChangeRequestError ? (
                        <p className="mt-3 text-sm font-medium text-red-700">{importChangeRequestError}</p>
                      ) : null}
                      {importChangeRequestResult ? (
                        <p className="mt-3 text-xs leading-5 text-gray-600">
                          Create {importChangeRequestResult.created_count}, gia esistenti{" "}
                          {importChangeRequestResult.existing_count}, saltate {importChangeRequestResult.skipped_count}.
                          {importChangeRequestResult.has_more ? " Aumenta l'offset per il batch successivo." : " Batch completato."}
                        </p>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          </div>
        </article>

        <article className="overflow-hidden rounded-[30px] border border-[#cbd9df] bg-[#f5fbfc] shadow-sm">
          <div className="border-b border-[#dce8ed] bg-[linear-gradient(135deg,#d7edf0,#eef5d1)] p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#315d80]">Per chi usa QGIS</p>
            <h3 className="mt-2 text-2xl font-semibold text-[#17231d]">QGIS Desktop in un colpo</h3>
            <p className="mt-2 text-sm leading-6 text-[#526154]">
              Scarichi un unico progetto gia pronto: dentro trovi le mappe a cui hai accesso, con stili e connessione
              gia impostati. Non devi configurare nulla a mano.
            </p>
          </div>
          <div className="p-5">
            <div className="grid gap-3">
              {qgisDesktopModes.map((mode) => (
                <div key={mode} className="rounded-2xl border border-[#dce8ed] bg-white p-4 text-sm leading-6 text-gray-600">
                  {mode}
                </div>
              ))}
            </div>
            <div className="mt-5 flex flex-wrap gap-3">
              <button
                className="btn-primary"
                type="button"
                disabled={qgisProjectBusy || dashboard?.qgis_publishable_layers === 0}
                onClick={() => void downloadQgisProject()}
              >
                {qgisProjectBusy ? "Preparazione progetto..." : "Scarica progetto QGIS"}
              </button>
            </div>
            {dashboard?.qgis_publishable_layers === 0 ? (
              <p className="mt-3 text-sm font-medium text-[#76560C]">
                Non ci sono layer QGIS pubblicabili per la tua utenza: controlla permessi o metadata del catalogo.
              </p>
            ) : null}
            {qgisProjectError ? <p className="mt-3 text-sm font-medium text-red-700">{qgisProjectError}</p> : null}
            <div className="mt-5 rounded-2xl border border-[#cbd9df] bg-white p-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div>
                  <p className="text-sm font-semibold text-[#17231d]">POC OGC read-only</p>
                  <p className="mt-1 text-xs leading-5 text-gray-600">
                    Verifica cosa pubblicheremmo con QGIS Server: WMS/WFS in sola lettura, niente WFS-T e proxy protetto.
                  </p>
                </div>
                <button className="btn-secondary" type="button" disabled={ogcPocBusy} onClick={() => void loadOgcPoc()}>
                  {ogcPocBusy ? "Verifica..." : "Verifica POC OGC"}
                </button>
              </div>
              {ogcPocError ? <p className="mt-3 text-sm font-medium text-red-700">{ogcPocError}</p> : null}
              {ogcPoc ? (
                <div className="mt-4 space-y-3">
                  <div className="grid gap-2 md:grid-cols-3">
                    <CatalogFact label="Server" value={ogcPoc.recommended_server} />
                    <CatalogFact label="Proxy" value={ogcPoc.proxy_path} />
                    <CatalogFact label="Layer OGC" value={String(ogcPoc.publishable_layer_count)} />
                  </div>
                  {ogcPoc.warnings.map((warning) => (
                    <p key={warning} className="rounded-xl bg-[#fff6d8] px-3 py-2 text-xs font-medium text-[#76560c]">
                      {warning}
                    </p>
                  ))}
                  <div className="grid gap-2">
                    {ogcPoc.layers.slice(0, 4).map((layer) => (
                      <div key={layer.layer_id} className="rounded-xl border border-[#e2edf1] bg-[#f8fbfc] p-3 text-xs text-gray-600">
                        <p className="font-semibold text-[#17231d]">
                          {layer.workspace} / {layer.title}
                        </p>
                        <p className="mt-1 font-mono">{layer.service_layer_name} - {layer.source_table}</p>
                        <p className="mt-1">WMS/WFS read-only, WFS-T disabilitato.</p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </article>
        </div>
      </details>

      {dashboard ? (
        <section className="rounded-[28px] border border-[#d9dfd6] bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#66816d]">Health catalogo GIS</p>
              <h3 className="mt-2 text-xl font-semibold text-gray-950">Controlli automatici sulle mappe</h3>
              <p className="mt-2 text-sm text-gray-500">
                GAIA verifica da solo che le mappe siano configurate bene. Se qui e tutto verde non devi fare nulla.
              </p>
            </div>
            <span className={`rounded-full px-4 py-2 text-sm font-semibold ${healthStatusClasses[dashboard.health_status]}`}>
              {healthStatusLabels[dashboard.health_status]}
            </span>
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-4">
            <CatalogFact label="Mappe attive" value={String(dashboard.active_layers)} />
            <CatalogFact label="Usabili in QGIS" value={String(dashboard.qgis_publishable_layers)} />
            <CatalogFact label="Esportabili" value={String(dashboard.exportable_layers)} />
            <CatalogFact label="Problemi rilevati" value={String(dashboard.issues.length)} />
          </div>
          <div className="mt-5 grid gap-4 xl:grid-cols-[1.2fr_1fr_1fr]">
            <div className="rounded-[22px] border border-[#e2e9e0] bg-[#f8fbf8] p-4">
              <p className="text-sm font-semibold text-gray-900">Problemi principali</p>
              {dashboard.issues.length === 0 ? (
                <p className="mt-3 text-sm text-gray-500">Nessuna criticita rilevata sui layer visibili.</p>
              ) : (
                <div className="mt-3 space-y-2">
                  {dashboard.issues.slice(0, 4).map((issue) => (
                    <div key={`${issue.layer_id}:${issue.code}`} className="rounded-2xl border border-[#d9dfd6] bg-white p-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`rounded-full px-2 py-1 text-xs font-semibold ${healthStatusClasses[issue.severity]}`}>
                          {issue.severity}
                        </span>
                        <span className="font-mono text-xs text-gray-500">{issue.code}</span>
                      </div>
                      <p className="mt-2 text-sm font-semibold text-gray-900">{issue.layer_name}</p>
                      <p className="text-sm text-gray-500">{issue.message}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="rounded-[22px] border border-[#e2e9e0] bg-[#f8fbf8] p-4">
              <p className="text-sm font-semibold text-gray-900">Workspace</p>
              <div className="mt-3 space-y-2">
                {dashboard.workspaces.map((workspace) => (
                  <div key={workspace.workspace} className="flex items-center justify-between rounded-2xl bg-white px-3 py-2 text-sm">
                    <span className="font-semibold text-gray-900">{workspace.workspace}</span>
                    <span className={`rounded-full px-2 py-1 text-xs font-semibold ${healthStatusClasses[workspace.health_status]}`}>
                      {workspace.total_layers} layer / {workspace.issue_count} issue
                    </span>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-[22px] border border-[#e2e9e0] bg-[#f8fbf8] p-4">
              <p className="text-sm font-semibold text-gray-900">Ultimi export</p>
              {dashboard.latest_exports.length === 0 ? (
                <p className="mt-3 text-sm text-gray-500">Nessun export registrato sui layer visibili.</p>
              ) : (
                <div className="mt-3 space-y-2">
                  {dashboard.latest_exports.slice(0, 4).map((item) => (
                    <div key={`${item.layer_id}:${item.version_label}`} className="rounded-2xl bg-white px-3 py-2 text-sm">
                      <div className="flex items-center justify-between gap-3">
                        <span className="font-semibold text-gray-900">{item.layer_name}</span>
                        <span className="rounded-full bg-[#eef3f9] px-2 py-1 text-xs font-semibold text-[#315d80]">
                          {item.status}
                        </span>
                      </div>
                      <p className="mt-1 font-mono text-xs text-gray-500">{item.version_label}</p>
                      <p className="text-xs text-gray-500">{item.trigger ?? "manual"}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </section>
      ) : null}
      {shapefileImportPreview && shapefileImportPreviewOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#17231d]/70 p-4">
          <section
            aria-modal="true"
            aria-labelledby="shapefile-preview-title"
            className="max-h-[88vh] w-full max-w-5xl overflow-hidden rounded-[30px] border border-[#c6dfe8] bg-white shadow-2xl"
            role="dialog"
          >
            <div className="flex flex-col gap-4 border-b border-[#e2edf1] bg-[#f5fbfc] p-5 md:flex-row md:items-start md:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#315d80]">Preview GIS</p>
                <h3 id="shapefile-preview-title" className="mt-2 text-2xl font-semibold text-[#17231d]">
                  Anteprima staging
                </h3>
                <p className="mt-2 text-sm leading-6 text-gray-600">
                  Controlla un campione dei dati appena caricati. Questa vista legge solo l&apos;area di prova e non modifica dati ufficiali.
                </p>
              </div>
              <button className="btn-secondary" type="button" onClick={() => setShapefileImportPreviewOpen(false)}>
                Chiudi anteprima
              </button>
            </div>
            <div className="max-h-[65vh] overflow-auto p-5">
              <div className="grid gap-3 md:grid-cols-3">
                <CatalogFact label="Feature mostrate" value={`${shapefileImportPreview.returned_count} / ${shapefileImportPreview.feature_count}`} />
                <CatalogFact
                  label="Staging"
                  value={`${formatValue(shapefileImportPreview.staging_schema)}.${shapefileImportPreview.staging_table}`}
                />
                <CatalogFact label="Campione" value={`Limite ${shapefileImportPreview.limit}, offset ${shapefileImportPreview.offset}`} />
              </div>
              <div className="mt-4 grid gap-3">
                {shapefileImportPreview.features.map((feature) => (
                  <div key={feature.feature_seq} className="rounded-2xl border border-[#e2edf1] bg-[#f8fbfc] p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#315d80]">
                      Feature #{feature.feature_seq} - {formatValue(feature.geometry_type)} - SRID {feature.source_srid}
                    </p>
                    <div className="mt-3 grid gap-3 md:grid-cols-2">
                      <div>
                        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-gray-400">Attributi</p>
                        <pre className="max-h-72 overflow-auto rounded-xl bg-white p-3 text-xs text-gray-700">
                          {JSON.stringify(feature.attributes, null, 2)}
                        </pre>
                      </div>
                      <div>
                        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-gray-400">Geometria</p>
                        <pre className="max-h-72 overflow-auto rounded-xl bg-white p-3 text-xs text-gray-700">
                          {JSON.stringify(feature.geometry, null, 2)}
                        </pre>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}

function MetricTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-[#e0dcc0] bg-white/70 p-4">
      <p className="text-3xl font-semibold tracking-tight">{value}</p>
      <p className="mt-1 text-xs font-semibold uppercase tracking-[0.14em] text-[#6a7340]">{label}</p>
    </div>
  );
}

function GuideCard({ eyebrow, title, body }: { eyebrow: string; title: string; body: string }) {
  return (
    <article className="rounded-[26px] border border-[#d9dfd6] bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#8a9560]">{eyebrow}</p>
      <h3 className="mt-3 text-lg font-semibold text-gray-950">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-gray-600">{body}</p>
    </article>
  );
}

function CatalogFact({ label, value, description }: { label: string; value: string; description?: string }) {
  return (
    <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-400">{label}</p>
      <p className="mt-2 break-words text-sm font-semibold text-gray-800">{value}</p>
      {description ? <p className="mt-2 text-xs leading-5 text-gray-500">{description}</p> : null}
    </div>
  );
}

export default function GisCatalogPage() {
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  return (
    <ProtectedPage
      title="GIS Platform"
      description="Tutte le mappe disponibili in GAIA: cosa contengono, chi le cura e cosa puoi farci."
      breadcrumb="GIS Platform / Catalogo"
      requiredModule="gis"
      hideContentHeader
    >
      <GisCatalogWorkspace token={token} />
    </ProtectedPage>
  );
}
