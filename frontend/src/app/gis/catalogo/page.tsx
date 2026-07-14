"use client";

import Link from "next/link";
import { startTransition, useEffect, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { RefreshIcon } from "@/components/ui/icons";
import { getStoredAccessToken } from "@/lib/auth";
import {
  createGisLayerChangeRequest,
  createGisLayerAnnotation,
  getGisCatalogDashboard,
  listGisCatalogLayers,
  listGisChangeRequests,
  listGisLayerAnnotations,
  listGisLayerPermissions,
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

const gisAccessLevels: GisCatalogAccessLevel[] = ["viewer", "annotator", "editor", "approver", "admin"];
const annotationStatuses: GisCatalogAnnotationStatus[] = ["open", "in_review", "closed", "rejected"];
const changeRequestStatuses: GisCatalogChangeRequestStatus[] = ["submitted", "needs_changes", "approved", "rejected", "applied"];
const changeRequestTypes: GisCatalogChangeRequestType[] = ["attribute_update", "geometry_update", "feature_create", "feature_delete"];
const applicationRoleOptions = ["viewer", "operator", "reviewer", "hr_manager", "admin", "super_admin"];

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

export function GisCatalogWorkspace({ token }: { token: string | null }) {
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
      <section className="overflow-hidden rounded-[32px] border border-[#c9d8cd] bg-[#10251d] text-white shadow-[0_22px_60px_rgba(16,37,29,0.22)]">
        <div className="grid gap-6 p-6 lg:grid-cols-[1.5fr_0.8fr] lg:p-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[#9fc5ad]">GAIA GIS Platform</p>
            <h2 className="mt-4 text-3xl font-semibold tracking-tight lg:text-4xl">Catalogo operativo GIS</h2>
            <p className="mt-4 max-w-2xl text-sm leading-6 text-[#d9e6dd]">
              Vista centrale read-only dei layer pubblicati: PostGIS resta sorgente ufficiale, Martin e QGIS sono
              esposti come metadati governati, Catasto resta nel proprio workspace operativo.
            </p>
          </div>
          <div className="rounded-[28px] border border-white/15 bg-white/10 p-5 backdrop-blur">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#bcd8c6]">Contratto dati</p>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-3xl font-semibold">{dashboard?.total_layers ?? layers.length}</p>
                <p className="text-[#cbdccf]">Layer visibili</p>
              </div>
              <div>
                <p className="text-3xl font-semibold">{dashboard?.workspace_count ?? fallbackWorkspaces.size}</p>
                <p className="text-[#cbdccf]">Workspace</p>
              </div>
              <div>
                <p className="text-3xl font-semibold">
                  {dashboard?.official_source_counts.postgis ?? fallbackOfficialPostgisCount}
                </p>
                <p className="text-[#cbdccf]">PostGIS ufficiali</p>
              </div>
              <div>
                <p className="text-3xl font-semibold">{dashboard?.inactive_layers ?? fallbackInactiveCount}</p>
                <p className="text-[#cbdccf]">Inattivi</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {dashboard ? (
        <section className="rounded-[28px] border border-[#d9dfd6] bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#66816d]">Health catalogo GIS</p>
              <h3 className="mt-2 text-xl font-semibold text-gray-950">Stato pubblicazione e policy layer</h3>
              <p className="mt-2 text-sm text-gray-500">
                Controllo deterministico su metadata catalogo, permessi visibili, policy QGIS ed export shapefile.
              </p>
            </div>
            <span className={`rounded-full px-4 py-2 text-sm font-semibold ${healthStatusClasses[dashboard.health_status]}`}>
              {healthStatusLabels[dashboard.health_status]}
            </span>
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-4">
            <CatalogFact label="Layer attivi" value={String(dashboard.active_layers)} />
            <CatalogFact label="QGIS publishable" value={String(dashboard.qgis_publishable_layers)} />
            <CatalogFact label="Export shapefile" value={String(dashboard.exportable_layers)} />
            <CatalogFact label="Issue health" value={String(dashboard.issues.length)} />
          </div>
          <div className="mt-5 grid gap-4 xl:grid-cols-[1.2fr_1fr_1fr]">
            <div className="rounded-[22px] border border-[#e2e9e0] bg-[#f8fbf8] p-4">
              <p className="text-sm font-semibold text-gray-900">Issue principali</p>
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

      <section className="rounded-[28px] border border-[#d9dfd6] bg-white p-5 shadow-sm">
        <div className="grid gap-3 md:grid-cols-5">
          <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
            Workspace
            <input
              className="form-control mt-2"
              value={filters.workspace}
              onChange={(event) => setFilter("workspace", event.target.value)}
              placeholder="catasto"
            />
          </label>
          <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
            Dominio
            <input
              className="form-control mt-2"
              value={filters.domainModule}
              onChange={(event) => setFilter("domainModule", event.target.value)}
              placeholder="catasto"
            />
          </label>
          <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
            Source
            <input
              className="form-control mt-2"
              value={filters.sourceType}
              onChange={(event) => setFilter("sourceType", event.target.value)}
              placeholder="postgis"
            />
          </label>
          <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
            Ufficiale
            <input
              className="form-control mt-2"
              value={filters.officialSource}
              onChange={(event) => setFilter("officialSource", event.target.value)}
              placeholder="postgis"
            />
          </label>
          <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
            Stato
            <select
              className="form-control mt-2"
              value={filters.active}
              onChange={(event) => setFilter("active", event.target.value)}
            >
              <option value="all">Tutti</option>
              <option value="active">Solo attivi</option>
              <option value="inactive">Solo inattivi</option>
            </select>
          </label>
        </div>
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
          <p className="text-lg font-semibold text-gray-900">Nessun layer nel filtro corrente</p>
          <p className="mt-2 text-sm text-gray-500">Modifica i filtri o verifica i permessi GIS del tuo account.</p>
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
                        {layer.workspace}
                      </span>
                      <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-600">
                        {layer.is_active ? "attivo" : "inattivo"}
                      </span>
                      <span className="rounded-full bg-[#eef3f9] px-3 py-1 text-xs font-semibold text-[#315d80]">
                        {layer.effective_access_level}
                      </span>
                    </div>
                    <h3 className="mt-3 text-xl font-semibold text-gray-950">{layer.title}</h3>
                    <p className="mt-1 text-sm text-gray-500">{formatValue(layer.description)}</p>
                    <p className="mt-2 font-mono text-xs text-gray-400">{layer.name}</p>
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
                    ) : (
                      <button className="btn-secondary cursor-default" type="button" disabled>
                        Permessi read-only
                      </button>
                    )}
                    {layer.can_view ? (
                      <button className="btn-secondary" type="button" onClick={() => toggleAnnotationPanel(layer)}>
                        {annotationsLayerId === layer.id ? "Chiudi annotazioni" : "Annotazioni"}
                      </button>
                    ) : null}
                    {layer.can_view ? (
                      <button className="btn-secondary" type="button" onClick={() => toggleChangeRequestPanel(layer)}>
                        {changeRequestsLayerId === layer.id ? "Chiudi change request" : "Change request"}
                      </button>
                    ) : null}
                  </div>
                </div>

                <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  <CatalogFact label="PostGIS" value={`${formatValue(layer.postgis_schema)}.${formatValue(layer.postgis_table)}`} />
                  <CatalogFact label="Geometry" value={`${formatValue(layer.geometry_type)} - SRID ${formatValue(layer.srid)}`} />
                  <CatalogFact label="Martin layer" value={formatValue(layer.martin_layer_id)} />
                  <CatalogFact label="Feature id" value={formatValue(layer.feature_id_column)} />
                  <CatalogFact label="Source type" value={layer.source_type} />
                  <CatalogFact label="Official source" value={layer.official_source} />
                  <CatalogFact label="QGIS mode" value={qgisMode(layer)} />
                  <CatalogFact label="Tile provider" value={tileProvider(layer)} />
                </div>

                {permissionsLayerId === layer.id && layer.can_manage ? (
                  <section className="mt-5 rounded-[24px] border border-[#d9dfd6] bg-[#f7faf7] p-4">
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
                              {level}
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
                                {permission.access_level} - view {metadataLabel(permission.can_view)} / annotate {metadataLabel(permission.can_annotate)} / edit {metadataLabel(permission.can_edit)} / approve {metadataLabel(permission.can_approve)} / manage {metadataLabel(permission.can_manage)}
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
                              {status}
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
                                    {annotation.status}
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
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                      <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                        Stato change request
                        <select
                          className="form-control mt-2"
                          value={changeRequestFilters.status}
                          onChange={(event) => setChangeRequestFilters({ status: event.target.value as ChangeRequestStatusFilter })}
                        >
                          <option value="all">Tutte</option>
                          {changeRequestStatuses.map((status) => (
                            <option key={status} value={status}>
                              {status}
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
                                {changeType}
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
                                      {changeRequest.status}
                                    </span>
                                    <span className="rounded-full bg-[#eef3f9] px-2.5 py-1 text-xs font-semibold text-[#315d80]">
                                      {changeRequest.change_type}
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
                                      Applica no-op
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
    </div>
  );
}

function CatalogFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-400">{label}</p>
      <p className="mt-2 break-words text-sm font-semibold text-gray-800">{value}</p>
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
      description="Catalogo centrale read-only dei layer GIS governati da GAIA."
      breadcrumb="GIS Platform / Catalogo"
      requiredModule="gis"
      hideContentHeader
    >
      <GisCatalogWorkspace token={token} />
    </ProtectedPage>
  );
}
