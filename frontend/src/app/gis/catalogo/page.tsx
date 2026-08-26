"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

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
  setGisChangeRequestStatus,
  setGisLayerAnnotationStatus,
  updateGisChangeRequest,
  updateGisLayerAnnotation,
} from "@/lib/api/gis";
import type {
  GisCatalogAccessLevel,
  GisCatalogAnnotation,
  GisCatalogAnnotationSaveInput,
  GisCatalogAnnotationStatus,
  GisCatalogChangeRequest,
  GisCatalogChangeRequestSaveInput,
  GisCatalogChangeRequestStatus,
  GisCatalogChangeRequestType,
  GisCatalogDashboardResponse,
  GisCatalogHealthStatus,
  GisCatalogLayer,
  GisCatalogLayerFilters,
} from "@/types/gis";

import {
  CatalogLayerSummary,
  CatalogSearchControls,
  catalogLayerDestination,
  layerMatchesCatalogFilters,
} from "./catalog-essential";
import { ConfirmationDialog } from "./catalog-dialog";
import {
  GuidedAnnotationComposer,
  GuidedChangeRequestComposer,
} from "./guided-workflow-components";

type ActiveFilter = "all" | "active" | "inactive";

type FilterState = {
  query: string;
  workspace: string;
  domainModule: string;
  sourceType: string;
  officialSource: string;
  active: ActiveFilter;
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
  reviewNotes: string;
};

type PendingConfirmation = {
  title: string;
  description: string;
  consequences: string[];
  confirmLabel: string;
  successMessage: string;
  tone: "primary" | "destructive";
  action: () => Promise<boolean>;
};

const initialFilters: FilterState = {
  query: "",
  workspace: "",
  domainModule: "",
  sourceType: "",
  officialSource: "",
  active: "all",
};

const initialAnnotationFilters: AnnotationFilterState = {
  status: "all",
  featureId: "",
};

const initialChangeRequestFilters: ChangeRequestFilterState = {
  status: "all",
};

const initialChangeRequestForm: ChangeRequestFormState = {
  reviewNotes: "",
};

const annotationStatuses: GisCatalogAnnotationStatus[] = [
  "open",
  "in_review",
  "closed",
  "rejected",
];
const changeRequestStatuses: GisCatalogChangeRequestStatus[] = [
  "submitted",
  "needs_changes",
  "approved",
  "rejected",
  "applied",
];
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

const changeRequestStatusLabels: Record<GisCatalogChangeRequestStatus, string> =
  {
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

function toApiFilters(filters: FilterState): GisCatalogLayerFilters {
  const apiFilters: GisCatalogLayerFilters = {};
  if (filters.workspace.trim()) apiFilters.workspace = filters.workspace.trim();
  if (filters.domainModule.trim())
    apiFilters.domainModule = filters.domainModule.trim();
  if (filters.sourceType.trim())
    apiFilters.sourceType = filters.sourceType.trim();
  if (filters.officialSource.trim())
    apiFilters.officialSource = filters.officialSource.trim();
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

function updateFilterValue(
  filters: FilterState,
  key: keyof FilterState,
  value: string,
): FilterState {
  return { ...filters, [key]: value } as FilterState;
}

function toAnnotationApiFilters(filters: AnnotationFilterState) {
  return {
    status: filters.status === "all" ? undefined : filters.status,
    featureId: filters.featureId,
  };
}

function toChangeRequestApiFilters(
  layer: GisCatalogLayer,
  filters: ChangeRequestFilterState,
) {
  return {
    layerId: layer.id,
    status: filters.status === "all" ? undefined : filters.status,
  };
}

function prettyJson(value: Record<string, unknown>): string {
  return JSON.stringify(value, null, 2);
}

function changeRequestPayloadLabel(
  changeRequest: GisCatalogChangeRequest,
): string {
  const labels: Record<GisCatalogChangeRequestType, string> = {
    attribute_update: "Diff attributi",
    geometry_update: "Diff geometria",
    feature_create: "Nuova feature",
    feature_delete: "Feature da eliminare",
  };
  return `${labels[changeRequest.change_type]}\n${prettyJson(changeRequest.payload)}`;
}

function layerActionLabels(layer: GisCatalogLayer): string[] {
  const labels: string[] = [];
  if (layer.can_view) labels.push("consultazione");
  if (layer.can_annotate) labels.push("note");
  if (layer.can_edit) labels.push("richieste di modifica");
  if (layer.can_approve) labels.push("approvazione");
  return labels.length > 0 ? labels : ["nessuna azione disponibile"];
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

const catalogTaskCards = [
  {
    eyebrow: "Per tutti",
    title: "Trova la mappa giusta",
    body: "Scrivi una parola comune oppure scegli Catasto, Rete o Riordino. La ricerca e solo consultazione e non modifica dati.",
  },
  {
    eyebrow: "Operatori",
    title: "Segnala o proponi correzioni",
    body: "Dalle schede layer puoi aprire note e richieste di modifica. Le note non cambiano i dati; le correzioni passano da approvazione.",
  },
  {
    eyebrow: "Tecnici GIS",
    title: "Import e QGIS restano separati",
    body: "Shapefile, staging, progetto QGIS e POC OGC sono raccolti negli strumenti avanzati per non confondere la consultazione ordinaria.",
  },
];

const layerFactDescriptions = {
  postgis: "Tabella o vista usata dal layer quando la sorgente e PostGIS.",
  geometry:
    "Tipo geometrico e sistema di riferimento: servono per mappa, export e QGIS.",
  martin:
    "Identificativo del tile server Martin, se il layer e pubblicato come tile.",
  featureId:
    "Campo stabile usato per collegare note e change request a una feature.",
  sourceType: "Tecnologia o registro da cui arriva il layer nel catalogo.",
  officialSource:
    "Sistema autorevole da cui il dato deve essere considerato valido.",
  qgisMode:
    "Modalita prevista per QGIS Desktop: read-only, controlled edit o non pubblicato.",
  tileProvider: "Motore che serve le tile al viewer quando configurato.",
} as const;

function GisCatalogWorkspace({ token }: { token: string | null }) {
  const [filters, setFilters] = useState<FilterState>(initialFilters);
  const [catalogLayers, setLayers] = useState<GisCatalogLayer[]>([]);
  const [dashboard, setDashboard] =
    useState<GisCatalogDashboardResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [annotationsLayerId, setAnnotationsLayerId] = useState<string | null>(
    null,
  );
  const [annotations, setAnnotations] = useState<GisCatalogAnnotation[]>([]);
  const [annotationFilters, setAnnotationFilters] =
    useState<AnnotationFilterState>(initialAnnotationFilters);
  const [editingAnnotationId, setEditingAnnotationId] = useState<string | null>(
    null,
  );
  const [annotationError, setAnnotationError] = useState<string | null>(null);
  const [annotationBusy, setAnnotationBusy] = useState<string | null>(null);
  const [changeRequestsLayerId, setChangeRequestsLayerId] = useState<
    string | null
  >(null);
  const [changeRequests, setChangeRequests] = useState<
    GisCatalogChangeRequest[]
  >([]);
  const [changeRequestFilters, setChangeRequestFilters] =
    useState<ChangeRequestFilterState>(initialChangeRequestFilters);
  const [changeRequestForm, setChangeRequestForm] =
    useState<ChangeRequestFormState>(initialChangeRequestForm);
  const [editingChangeRequestId, setEditingChangeRequestId] = useState<
    string | null
  >(null);
  const [changeRequestError, setChangeRequestError] = useState<string | null>(
    null,
  );
  const [changeRequestBusy, setChangeRequestBusy] = useState<string | null>(
    null,
  );
  const [pendingConfirmation, setPendingConfirmation] =
    useState<PendingConfirmation | null>(null);
  const [confirmationBusy, setConfirmationBusy] = useState(false);
  const [confirmationError, setConfirmationError] = useState<string | null>(
    null,
  );
  const [actionNotice, setActionNotice] = useState<string | null>(null);

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
        setLoadError(
          error instanceof Error
            ? error.message
            : "Errore caricamento catalogo GIS",
        );
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

  function openConfirmation(confirmation: PendingConfirmation) {
    setConfirmationError(null);
    setPendingConfirmation(() => confirmation);
  }

  async function confirmPendingAction() {
    const confirmation = pendingConfirmation as PendingConfirmation;
    setConfirmationBusy(true);
    setConfirmationError(null);
    try {
      const succeeded = await confirmation.action();
      if (!succeeded) {
        setConfirmationError(
          "Operazione non completata. Controlla il messaggio di errore e riprova.",
        );
        return;
      }
      setActionNotice(confirmation.successMessage);
      setPendingConfirmation(null);
    } finally {
      setConfirmationBusy(false);
    }
  }

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
      setLoadError(
        error instanceof Error
          ? error.message
          : "Errore caricamento catalogo GIS",
      );
    } finally {
      setIsLoading(false);
    }
  }

  function setFilter(key: keyof FilterState, value: string) {
    setFilters((currentFilters) =>
      updateFilterValue(currentFilters, key, value),
    );
  }

  function resetFilters() {
    setFilters(initialFilters);
    void loadCatalog(initialFilters);
  }

  async function loadAnnotations(
    layer: GisCatalogLayer,
    filters: AnnotationFilterState = annotationFilters,
  ) {
    const currentToken = token as string;
    setAnnotationsLayerId(layer.id);
    setAnnotationBusy(`load:${layer.id}`);
    setAnnotationError(null);
    try {
      const response = await listGisLayerAnnotations(
        currentToken,
        layer.id,
        toAnnotationApiFilters(filters),
      );
      setAnnotations(response);
    } catch (error) {
      setAnnotations([]);
      setAnnotationError(
        error instanceof Error
          ? error.message
          : "Errore caricamento annotazioni GIS",
      );
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
    setEditingAnnotationId(null);
    void loadAnnotations(layer, initialAnnotationFilters);
  }

  function editAnnotation(annotation: GisCatalogAnnotation) {
    setEditingAnnotationId(annotation.id);
  }

  function resetAnnotationForm() {
    setEditingAnnotationId(null);
  }

  async function saveAnnotation(
    layer: GisCatalogLayer,
    input: GisCatalogAnnotationSaveInput,
  ): Promise<boolean> {
    const currentToken = token as string;
    const isEditing = Boolean(editingAnnotationId);
    setAnnotationBusy(`save:${layer.id}`);
    setAnnotationError(null);
    try {
      if (editingAnnotationId) {
        await updateGisLayerAnnotation(
          currentToken,
          layer.id,
          editingAnnotationId,
          { title: input.title, body: input.body },
        );
      } else {
        await createGisLayerAnnotation(currentToken, layer.id, input);
      }
      resetAnnotationForm();
      const response = await listGisLayerAnnotations(
        currentToken,
        layer.id,
        toAnnotationApiFilters(annotationFilters),
      );
      setAnnotations(response);
      setActionNotice(
        isEditing
          ? `Nota aggiornata sulla mappa ${layer.title}.`
          : `Nota creata sulla mappa ${layer.title}.`,
      );
      return true;
    } catch (error) {
      setAnnotationError(
        error instanceof Error
          ? error.message
          : "Errore salvataggio annotazione GIS",
      );
      return false;
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
      const updated = await setGisLayerAnnotationStatus(
        currentToken,
        layer.id,
        annotationId,
        nextStatus,
      );
      setAnnotations((currentItems) =>
        currentItems.map((item) => (item.id === updated.id ? updated : item)),
      );
      setActionNotice(
        `Nota aggiornata: ${annotationStatusLabels[nextStatus]}.`,
      );
    } catch (error) {
      setAnnotationError(
        error instanceof Error ? error.message : "Errore stato annotazione GIS",
      );
    } finally {
      setAnnotationBusy(null);
    }
  }

  async function loadChangeRequests(
    layer: GisCatalogLayer,
    filters: ChangeRequestFilterState,
  ) {
    const currentToken = token as string;
    setChangeRequestsLayerId(layer.id);
    setChangeRequestBusy(`load:${layer.id}`);
    setChangeRequestError(null);
    try {
      const response = await listGisChangeRequests(
        currentToken,
        toChangeRequestApiFilters(layer, filters),
      );
      setChangeRequests(response);
    } catch (error) {
      setChangeRequests([]);
      setChangeRequestError(
        error instanceof Error
          ? error.message
          : "Errore caricamento change request GIS",
      );
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
  }

  function resetChangeRequestForm() {
    setEditingChangeRequestId(null);
    setChangeRequestForm(initialChangeRequestForm);
  }

  async function saveChangeRequest(
    layer: GisCatalogLayer,
    input: GisCatalogChangeRequestSaveInput,
  ): Promise<boolean> {
    const currentToken = token as string;
    const isEditing = Boolean(editingChangeRequestId);
    setChangeRequestBusy(`save:${layer.id}`);
    setChangeRequestError(null);
    try {
      if (editingChangeRequestId) {
        await updateGisChangeRequest(
          currentToken,
          editingChangeRequestId,
          input,
        );
      } else {
        await createGisLayerChangeRequest(currentToken, layer.id, input);
      }
      resetChangeRequestForm();
      const response = await listGisChangeRequests(
        currentToken,
        toChangeRequestApiFilters(layer, changeRequestFilters),
      );
      setChangeRequests(response);
      setActionNotice(
        isEditing
          ? `Richiesta aggiornata sulla mappa ${layer.title}.`
          : `Richiesta inviata per la mappa ${layer.title}.`,
      );
      return true;
    } catch (error) {
      setChangeRequestError(
        error instanceof Error
          ? error.message
          : "Errore salvataggio change request GIS",
      );
      return false;
    } finally {
      setChangeRequestBusy(null);
    }
  }

  async function changeChangeRequestStatus(
    changeRequestId: string,
    nextStatus: Exclude<GisCatalogChangeRequestStatus, "submitted">,
  ): Promise<boolean> {
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
      setChangeRequests((currentItems) =>
        currentItems.map((item) => (item.id === updated.id ? updated : item)),
      );
      setChangeRequestForm((currentForm) => ({
        ...currentForm,
        reviewNotes: "",
      }));
      setActionNotice(
        `Richiesta aggiornata: ${changeRequestStatusLabels[nextStatus]}.`,
      );
      return true;
    } catch (error) {
      setChangeRequestError(
        error instanceof Error
          ? error.message
          : "Errore stato change request GIS",
      );
      return false;
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
  for (const layer of catalogLayers) {
    fallbackWorkspaces.add(layer.workspace);
    if (!layer.is_active) fallbackInactiveCount += 1;
    if (layer.official_source === "postgis") fallbackOfficialPostgisCount += 1;
  }
  const layers = catalogLayers.filter((layer) =>
    layerMatchesCatalogFilters(layer, filters),
  );

  if (!token) {
    return (
      <article className="rounded-[28px] border border-[#d8e4db] bg-white p-6 shadow-sm">
        <p className="text-sm font-semibold text-[#1D4E35]">
          Sessione catalogo in caricamento.
        </p>
        <p className="mt-2 text-sm text-gray-500">
          Il catalogo GIS viene caricato dopo la verifica della sessione GAIA.
        </p>
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
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[#d6e8bd]">
              GAIA GIS Platform
            </p>
            <h2 className="mt-5 text-4xl font-semibold tracking-tight lg:text-5xl">
              Catalogo delle mappe
            </h2>
            <p className="mt-5 max-w-2xl text-base leading-7 text-[#edf4e7]">
              Qui trovi tutte le mappe (layer) disponibili in GAIA. Per ogni
              mappa vedi subito di cosa si tratta, se e aggiornata e cosa puoi
              farci: consultarla, lasciare una nota o proporre una correzione.
            </p>
            <div className="mt-6 flex flex-wrap gap-2 text-xs font-semibold uppercase tracking-[0.16em]">
              <span className="rounded-full border border-white/15 bg-white/10 px-3 py-2 text-[#eef7e8]">
                Layer = una mappa tematica
              </span>
              <span className="rounded-full border border-white/15 bg-white/10 px-3 py-2 text-[#eef7e8]">
                Workspace = gruppo di mappe
              </span>
              <span className="rounded-full border border-white/15 bg-white/10 px-3 py-2 text-[#eef7e8]">
                Permesso = cosa puoi fare
              </span>
            </div>
            <Link
              className="mt-6 inline-flex rounded-full border border-white/20 bg-white/10 px-4 py-2 text-sm font-semibold text-white hover:bg-white/15"
              href="/gis/strumenti"
            >
              Strumenti per import e QGIS
            </Link>
          </div>
          <div className="rounded-[30px] border border-white/15 bg-[#f8f5dc]/95 p-5 text-[#17231d] shadow-[0_18px_44px_rgba(0,0,0,0.18)]">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#6a7340]">
              In sintesi
            </p>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <MetricTile
                label="Mappe disponibili"
                value={String(dashboard?.total_layers ?? catalogLayers.length)}
              />
              <MetricTile
                label="Gruppi di mappe"
                value={String(
                  dashboard?.workspace_count ?? fallbackWorkspaces.size,
                )}
              />
              <MetricTile
                label="Fonti ufficiali"
                value={String(
                  dashboard?.official_source_counts.postgis ??
                    fallbackOfficialPostgisCount,
                )}
              />
              <MetricTile
                label="Non attive"
                value={String(
                  dashboard?.inactive_layers ?? fallbackInactiveCount,
                )}
              />
            </div>
            <p className="mt-4 rounded-2xl bg-[#17231d] px-4 py-3 text-xs leading-5 text-[#dcebd0]">
              Non serve conoscere i termini tecnici: ogni scheda spiega in
              chiaro cosa contiene la mappa e cosa puoi fare. I dettagli tecnici
              restano disponibili, ma nascosti di default.
            </p>
          </div>
        </div>
      </section>

      {actionNotice ? (
        <section
          className="flex flex-col gap-3 rounded-2xl border border-[#bcd6c2] bg-[#edf8ef] px-4 py-3 text-sm text-[#1D4E35] sm:flex-row sm:items-center sm:justify-between"
          role="status"
          aria-live="polite"
        >
          <p className="font-semibold">{actionNotice}</p>
          <button
            className="btn-secondary"
            type="button"
            onClick={() => setActionNotice(null)}
          >
            Chiudi messaggio
          </button>
        </section>
      ) : null}

      <details className="group rounded-[28px] border border-[#d9dfd6] bg-white shadow-sm">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3 p-5 [&::-webkit-details-marker]:hidden">
          <span>
            <span className="block text-xs font-semibold uppercase tracking-[0.22em] text-[#526a59]">
              Guida rapida
            </span>
            <span className="mt-1 block text-lg font-semibold text-gray-950">
              Come funziona il catalogo, in parole semplici
            </span>
          </span>
          <span className="rounded-full bg-[#EAF3E8] px-4 py-2 text-xs font-semibold text-[#1D4E35] group-open:hidden">
            Apri la guida
          </span>
          <span className="hidden rounded-full bg-gray-100 px-4 py-2 text-xs font-semibold text-gray-600 group-open:inline">
            Chiudi la guida
          </span>
        </summary>
        <div className="grid gap-3 px-5 pb-5 md:grid-cols-2 xl:grid-cols-4">
          {catalogGuides.map((guide) => (
            <GuideCard
              key={guide.title}
              eyebrow={guide.eyebrow}
              title={guide.title}
              body={guide.body}
            />
          ))}
        </div>
      </details>

      <section className="grid gap-3 md:grid-cols-3">
        {catalogTaskCards.map((card) => (
          <GuideCard
            key={card.title}
            eyebrow={card.eyebrow}
            title={card.title}
            body={card.body}
          />
        ))}
      </section>

      <section className="rounded-[28px] border border-[#d9dfd6] bg-white p-5 shadow-sm">
        <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#526a59]">
              Cerca una mappa
            </p>
            <h3 className="mt-2 text-xl font-semibold text-gray-950">
              Che cosa stai cercando?
            </h3>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-500">
              Scrivi un nome o un argomento, per esempio particelle, condotte o
              pratiche. Puoi anche scegliere direttamente un&apos;area qui
              sotto.
            </p>
          </div>
          <span className="rounded-full bg-[#f4f0d0] px-4 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-[#59642f]">
            Solo consultazione
          </span>
        </div>
        <CatalogSearchControls
          filters={filters}
          visibleLayerCount={layers.length}
          onFilterChange={setFilter}
        />
        <details className="mt-4 rounded-2xl border border-gray-100 bg-gray-50 p-4">
          <summary className="cursor-pointer text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
            Filtri avanzati per operatori GIS
          </summary>
          <p className="mt-2 text-sm text-gray-500">
            Usali solo se conosci la provenienza tecnica dei dati.
          </p>
          <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
              Dominio
              <input
                className="form-control mt-2"
                value={filters.domainModule}
                aria-label="Dominio"
                onChange={(event) =>
                  setFilter("domainModule", event.target.value)
                }
                placeholder="catasto"
              />
            </label>
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
              Stato
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
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
              Source
              <span className="mt-1 block normal-case tracking-normal text-gray-600">
                Tecnologia che alimenta il layer, per esempio postgis.
              </span>
              <input
                className="form-control mt-2"
                value={filters.sourceType}
                aria-label="Source"
                onChange={(event) =>
                  setFilter("sourceType", event.target.value)
                }
                placeholder="postgis"
              />
            </label>
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
              Ufficiale
              <span className="mt-1 block normal-case tracking-normal text-gray-600">
                Sistema autorevole da cui arriva il dato valido.
              </span>
              <input
                className="form-control mt-2"
                value={filters.officialSource}
                aria-label="Ufficiale"
                onChange={(event) =>
                  setFilter("officialSource", event.target.value)
                }
                placeholder="postgis"
              />
            </label>
          </div>
        </details>
        <div className="mt-4 flex flex-wrap gap-3">
          <button
            className="btn-primary"
            type="button"
            disabled={isLoading}
            onClick={() => void loadCatalog(filters)}
          >
            {isLoading ? "Caricamento..." : "Applica filtri avanzati"}
          </button>
          <button
            className="btn-secondary"
            type="button"
            disabled={isLoading}
            onClick={resetFilters}
          >
            Azzera tutto
          </button>
        </div>
      </section>

      {loadError ? (
        <article
          className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-700"
          role="alert"
        >
          {loadError}
        </article>
      ) : null}

      {layers.length === 0 && !isLoading ? (
        <article className="rounded-[28px] border border-dashed border-[#b8cabb] bg-[#f7faf7] p-8 text-center">
          <p className="text-lg font-semibold text-gray-900">
            Nessuna mappa trovata con questi filtri
          </p>
          <p className="mt-2 text-sm text-gray-500">
            Prova ad azzerare ricerca e filtri. Se ti aspettavi di vedere una
            mappa, chiedi a chi amministra il GIS di verificare i permessi del
            tuo account.
          </p>
        </article>
      ) : (
        <div className="grid gap-4">
          {layers.map((layer) => {
            const destination = catalogLayerDestination(layer);
            const actionLabels = layerActionLabels(layer);
            const editingAnnotation = annotations.find(
              (item) => item.id === editingAnnotationId,
            );
            const editingChangeRequest = changeRequests.find(
              (item) => item.id === editingChangeRequestId,
            );
            return (
              <article
                key={layer.id}
                className="rounded-[24px] border border-[#d9dfd6] bg-white p-4 shadow-sm sm:p-5"
              >
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-[#EAF3E8] px-3 py-1 text-xs font-semibold text-[#1D4E35]">
                        Workspace: {layer.workspace}
                      </span>
                      <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-600">
                        Stato: {layer.is_active ? "in uso" : "non attiva"}
                      </span>
                      <span className="rounded-full bg-[#eef3f9] px-3 py-1 text-xs font-semibold text-[#315d80]">
                        Permesso effettivo: puoi{" "}
                        {accessLevelDescriptions[layer.effective_access_level]}
                      </span>
                    </div>
                    <h3 className="mt-3 text-xl font-semibold text-gray-950">
                      {layer.title}
                    </h3>
                    <p className="mt-1 text-sm text-gray-500">
                      {formatValue(layer.description)}
                    </p>
                    <p className="mt-2 text-xs leading-5 text-gray-500">
                      Curata dal modulo {layer.domain_module}. Fonte dei dati:{" "}
                      {layer.official_source}.
                    </p>
                    <CatalogLayerSummary
                      layer={layer}
                      actionLabels={actionLabels}
                    />
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {destination ? (
                      <Link
                        aria-label={`${destination.label} ${layer.title}`}
                        className="btn-primary"
                        href={destination.href}
                      >
                        {destination.label}
                      </Link>
                    ) : null}
                    {layer.can_view ? (
                      <button
                        className="btn-secondary"
                        type="button"
                        onClick={() => toggleAnnotationPanel(layer)}
                      >
                        {annotationsLayerId === layer.id
                          ? "Chiudi note"
                          : "Apri note"}
                      </button>
                    ) : null}
                    {layer.can_view ? (
                      <button
                        className="btn-secondary"
                        type="button"
                        onClick={() => toggleChangeRequestPanel(layer)}
                      >
                        {changeRequestsLayerId === layer.id
                          ? "Chiudi modifiche"
                          : "Proponi/vedi modifiche"}
                      </button>
                    ) : null}
                  </div>
                </div>

                <details className="mt-5 rounded-2xl border border-gray-100 bg-gray-50 p-4">
                  <summary className="cursor-pointer text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                    Dettagli tecnici (per operatori GIS)
                  </summary>
                  <p className="mt-3 font-mono text-xs text-gray-600">
                    {layer.name}
                  </p>
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
                    <CatalogFact
                      label="Source type"
                      value={layer.source_type}
                      description={layerFactDescriptions.sourceType}
                    />
                    <CatalogFact
                      label="Official source"
                      value={layer.official_source}
                      description={layerFactDescriptions.officialSource}
                    />
                    <CatalogFact
                      label="QGIS mode"
                      value={qgisMode(layer)}
                      description={layerFactDescriptions.qgisMode}
                    />
                    <CatalogFact
                      label="Tile provider"
                      value={tileProvider(layer)}
                      description={layerFactDescriptions.tileProvider}
                    />
                  </div>
                </details>

                {annotationsLayerId === layer.id ? (
                  <section className="mt-5 rounded-[24px] border border-[#d9dfd6] bg-white p-4 shadow-sm">
                    <p className="mb-3 text-sm leading-6 text-gray-600">
                      Le note servono a segnalare qualcosa su questa mappa, ad
                      esempio un dato da verificare sul campo. Non modificano i
                      dati.
                    </p>
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-end">
                      <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                        Stato note
                        <select
                          className="form-control mt-2"
                          value={annotationFilters.status}
                          onChange={(event) =>
                            setAnnotationFilters((currentFilters) => ({
                              ...currentFilters,
                              status: event.target
                                .value as AnnotationStatusFilter,
                            }))
                          }
                        >
                          <option value="all">Tutte</option>
                          {annotationStatuses.map((status) => (
                            <option key={status} value={status}>
                              {annotationStatusLabels[status]}
                            </option>
                          ))}
                        </select>
                      </label>
                      <button
                        className="btn-secondary"
                        type="button"
                        onClick={() => applyAnnotationFilters(layer)}
                      >
                        Filtra note
                      </button>
                    </div>

                    {layer.can_annotate ? (
                      <GuidedAnnotationComposer
                        key={editingAnnotationId ?? "new-annotation"}
                        token={token as string}
                        layer={layer}
                        annotation={editingAnnotation}
                        busy={annotationBusy === `save:${layer.id}`}
                        onSubmit={(input) => saveAnnotation(layer, input)}
                        onCancel={resetAnnotationForm}
                      />
                    ) : null}

                    {annotationError ? (
                      <p
                        className="mt-3 text-sm font-medium text-red-700"
                        role="alert"
                      >
                        {annotationError}
                      </p>
                    ) : null}

                    <div className="mt-4 grid gap-2">
                      {annotationBusy === `load:${layer.id}` ? (
                        <p className="text-sm text-gray-500">
                          Caricamento annotazioni...
                        </p>
                      ) : annotations.length === 0 ? (
                        <p className="text-sm text-gray-500">
                          Nessuna annotazione nel filtro corrente.
                        </p>
                      ) : (
                        annotations.map((annotation) => (
                          <div
                            key={annotation.id}
                            className="rounded-2xl border border-[#edf2ee] bg-[#fbfdfb] p-4"
                          >
                            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                              <div>
                                <div className="flex flex-wrap items-center gap-2">
                                  <span className="rounded-full bg-[#EAF3E8] px-2.5 py-1 text-xs font-semibold text-[#1D4E35]">
                                    {annotationStatusLabels[annotation.status]}
                                  </span>
                                  <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-semibold text-gray-500">
                                    {annotation.feature_id ||
                                      "feature non associata"}
                                  </span>
                                </div>
                                <p className="mt-3 text-sm font-semibold text-gray-950">
                                  {annotation.title}
                                </p>
                                <p className="mt-1 text-sm text-gray-600">
                                  {annotation.body}
                                </p>
                              </div>
                              <div className="flex flex-wrap gap-2">
                                {layer.can_annotate &&
                                annotation.status !== "closed" &&
                                annotation.status !== "rejected" ? (
                                  <>
                                    <button
                                      className="btn-secondary"
                                      type="button"
                                      onClick={() => editAnnotation(annotation)}
                                    >
                                      Modifica
                                    </button>
                                    <button
                                      className="btn-secondary"
                                      type="button"
                                      disabled={
                                        annotationBusy ===
                                        `status:${annotation.id}:in_review`
                                      }
                                      onClick={() =>
                                        void changeAnnotationStatus(
                                          layer,
                                          annotation.id,
                                          "in_review",
                                        )
                                      }
                                    >
                                      In revisione
                                    </button>
                                  </>
                                ) : null}
                                {layer.can_approve &&
                                annotation.status !== "closed" &&
                                annotation.status !== "rejected" ? (
                                  <>
                                    <button
                                      className="btn-secondary"
                                      type="button"
                                      disabled={
                                        annotationBusy ===
                                        `status:${annotation.id}:closed`
                                      }
                                      onClick={() =>
                                        void changeAnnotationStatus(
                                          layer,
                                          annotation.id,
                                          "closed",
                                        )
                                      }
                                    >
                                      Chiudi
                                    </button>
                                    <button
                                      className="btn-secondary"
                                      type="button"
                                      disabled={
                                        annotationBusy ===
                                        `status:${annotation.id}:rejected`
                                      }
                                      onClick={() =>
                                        void changeAnnotationStatus(
                                          layer,
                                          annotation.id,
                                          "rejected",
                                        )
                                      }
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
                      Qui si propongono correzioni ai dati della mappa. Nessuna
                      modifica viene applicata finche una persona autorizzata
                      non la approva.
                    </p>
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                      <label className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                        Stato richiesta
                        <select
                          className="form-control mt-2"
                          value={changeRequestFilters.status}
                          onChange={(event) =>
                            setChangeRequestFilters({
                              status: event.target
                                .value as ChangeRequestStatusFilter,
                            })
                          }
                        >
                          <option value="all">Tutte</option>
                          {changeRequestStatuses.map((status) => (
                            <option key={status} value={status}>
                              {changeRequestStatusLabels[status]}
                            </option>
                          ))}
                        </select>
                      </label>
                      <button
                        className="btn-secondary"
                        type="button"
                        onClick={() => applyChangeRequestFilters(layer)}
                      >
                        Filtra richieste
                      </button>
                    </div>

                    {layer.can_edit ? (
                      <GuidedChangeRequestComposer
                        key={editingChangeRequestId ?? "new-change-request"}
                        token={token as string}
                        layer={layer}
                        changeRequest={editingChangeRequest}
                        busy={changeRequestBusy === `save:${layer.id}`}
                        onSubmit={(input) => saveChangeRequest(layer, input)}
                        onCancel={resetChangeRequestForm}
                      />
                    ) : null}

                    {layer.can_approve ? (
                      <label className="mt-4 block text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                        Note revisione
                        <input
                          className="form-control mt-2"
                          value={changeRequestForm.reviewNotes}
                          onChange={(event) =>
                            setChangeRequestForm({
                              reviewNotes: event.target.value,
                            })
                          }
                          placeholder="Esito istruttoria"
                        />
                      </label>
                    ) : null}

                    {changeRequestError ? (
                      <p
                        className="mt-3 text-sm font-medium text-red-700"
                        role="alert"
                      >
                        {changeRequestError}
                      </p>
                    ) : null}

                    <div className="mt-4 grid gap-2">
                      {changeRequestBusy === `load:${layer.id}` ? (
                        <p className="text-sm text-gray-500">
                          Caricamento change request...
                        </p>
                      ) : changeRequests.length === 0 ? (
                        <p className="text-sm text-gray-500">
                          Nessuna change request nel filtro corrente.
                        </p>
                      ) : (
                        changeRequests.map((changeRequest) => {
                          const reviewable =
                            changeRequest.status === "submitted" ||
                            changeRequest.status === "needs_changes";
                          return (
                            <div
                              key={changeRequest.id}
                              className="rounded-2xl border border-[#e3eadf] bg-white p-4"
                            >
                              <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
                                <div>
                                  <div className="flex flex-wrap items-center gap-2">
                                    <span className="rounded-full bg-[#EAF3E8] px-2.5 py-1 text-xs font-semibold text-[#1D4E35]">
                                      {
                                        changeRequestStatusLabels[
                                          changeRequest.status
                                        ]
                                      }
                                    </span>
                                    <span className="rounded-full bg-[#eef3f9] px-2.5 py-1 text-xs font-semibold text-[#315d80]">
                                      {
                                        changeRequestTypeLabels[
                                          changeRequest.change_type
                                        ]
                                      }
                                    </span>
                                    <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-semibold text-gray-500">
                                      {changeRequest.feature_id ||
                                        "nuova feature"}
                                    </span>
                                  </div>
                                  <p className="mt-3 text-sm font-semibold text-gray-950">
                                    {changeRequest.justification ||
                                      "Richiesta senza motivazione"}
                                  </p>
                                  <pre className="mt-2 max-h-52 overflow-auto rounded-xl bg-[#17231d] p-3 text-xs text-[#d7eadb]">
                                    {changeRequestPayloadLabel(changeRequest)}
                                  </pre>
                                  {changeRequest.review_notes ? (
                                    <p className="mt-2 text-xs font-medium text-gray-500">
                                      Review: {changeRequest.review_notes}
                                    </p>
                                  ) : null}
                                </div>
                                <div className="flex flex-wrap gap-2">
                                  {layer.can_edit && reviewable ? (
                                    <button
                                      className="btn-secondary"
                                      type="button"
                                      onClick={() =>
                                        editChangeRequest(changeRequest)
                                      }
                                    >
                                      Modifica richiesta
                                    </button>
                                  ) : null}
                                  {layer.can_approve && reviewable ? (
                                    <>
                                      <button
                                        className="btn-secondary"
                                        type="button"
                                        disabled={
                                          changeRequestBusy ===
                                          `status:${changeRequest.id}:needs_changes`
                                        }
                                        onClick={() =>
                                          void changeChangeRequestStatus(
                                            changeRequest.id,
                                            "needs_changes",
                                          )
                                        }
                                      >
                                        Richiedi modifiche
                                      </button>
                                      <button
                                        className="btn-secondary"
                                        type="button"
                                        disabled={
                                          changeRequestBusy ===
                                          `status:${changeRequest.id}:approved`
                                        }
                                        onClick={() =>
                                          void changeChangeRequestStatus(
                                            changeRequest.id,
                                            "approved",
                                          )
                                        }
                                      >
                                        Approva
                                      </button>
                                      <button
                                        className="btn-secondary"
                                        type="button"
                                        disabled={
                                          changeRequestBusy ===
                                          `status:${changeRequest.id}:rejected`
                                        }
                                        onClick={() =>
                                          void changeChangeRequestStatus(
                                            changeRequest.id,
                                            "rejected",
                                          )
                                        }
                                      >
                                        Rigetta richiesta
                                      </button>
                                    </>
                                  ) : null}
                                  {layer.can_approve &&
                                  changeRequest.status === "approved" ? (
                                    <button
                                      className="btn-secondary"
                                      type="button"
                                      disabled={
                                        changeRequestBusy ===
                                        `status:${changeRequest.id}:applied`
                                      }
                                      onClick={() =>
                                        openConfirmation({
                                          title: "Applicare questa modifica?",
                                          description: `${changeRequestTypeLabels[changeRequest.change_type]} sulla mappa ${layer.title}.`,
                                          consequences: [
                                            "La richiesta passerà allo stato Applicata e l'operazione sarà auditata.",
                                            "Sui layer con modifica controllata i dati PostGIS possono cambiare; sul Catasto l'apply resta senza scrittura.",
                                          ],
                                          confirmLabel: "Conferma applicazione",
                                          successMessage: `Modifica applicata sulla mappa ${layer.title}.`,
                                          tone: "destructive",
                                          action: () =>
                                            changeChangeRequestStatus(
                                              changeRequest.id,
                                              "applied",
                                            ),
                                        })
                                      }
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

      {dashboard ? (
        <section className="rounded-[28px] border border-[#d9dfd6] bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#526a59]">
                Health catalogo GIS
              </p>
              <h3 className="mt-2 text-xl font-semibold text-gray-950">
                Controlli automatici sulle mappe
              </h3>
              <p className="mt-2 text-sm text-gray-500">
                Questi controlli verificano configurazione e metadati del
                catalogo. Non misurano in tempo reale la disponibilita o
                l&apos;aggiornamento di PostGIS, Martin, QGIS e NAS.
              </p>
            </div>
            <span
              className={`rounded-full px-4 py-2 text-sm font-semibold ${healthStatusClasses[dashboard.health_status]}`}
            >
              {healthStatusLabels[dashboard.health_status]}
            </span>
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-4">
            <CatalogFact
              label="Mappe attive"
              value={String(dashboard.active_layers)}
            />
            <CatalogFact
              label="Usabili in QGIS"
              value={String(dashboard.qgis_publishable_layers)}
            />
            <CatalogFact
              label="Esportabili"
              value={String(dashboard.exportable_layers)}
            />
            <CatalogFact
              label="Problemi rilevati"
              value={String(dashboard.issues.length)}
            />
          </div>
          <div className="mt-5 grid gap-4 xl:grid-cols-[1.2fr_1fr_1fr]">
            <div className="rounded-[22px] border border-[#e2e9e0] bg-[#f8fbf8] p-4">
              <p className="text-sm font-semibold text-gray-900">
                Problemi principali
              </p>
              {dashboard.issues.length === 0 ? (
                <p className="mt-3 text-sm text-gray-500">
                  Nessuna criticita rilevata sui layer visibili.
                </p>
              ) : (
                <div className="mt-3 space-y-2">
                  {dashboard.issues.slice(0, 4).map((issue) => (
                    <div
                      key={`${issue.layer_id}:${issue.code}`}
                      className="rounded-2xl border border-[#d9dfd6] bg-white p-3"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`rounded-full px-2 py-1 text-xs font-semibold ${healthStatusClasses[issue.severity]}`}
                        >
                          {issue.severity}
                        </span>
                        <span className="font-mono text-xs text-gray-500">
                          {issue.code}
                        </span>
                      </div>
                      <p className="mt-2 text-sm font-semibold text-gray-900">
                        {issue.layer_name}
                      </p>
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
                  <div
                    key={workspace.workspace}
                    className="flex items-center justify-between rounded-2xl bg-white px-3 py-2 text-sm"
                  >
                    <span className="font-semibold text-gray-900">
                      {workspace.workspace}
                    </span>
                    <span
                      className={`rounded-full px-2 py-1 text-xs font-semibold ${healthStatusClasses[workspace.health_status]}`}
                    >
                      {workspace.total_layers} layer / {workspace.issue_count}{" "}
                      issue
                    </span>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-[22px] border border-[#e2e9e0] bg-[#f8fbf8] p-4">
              <p className="text-sm font-semibold text-gray-900">
                Ultimi export
              </p>
              {dashboard.latest_exports.length === 0 ? (
                <p className="mt-3 text-sm text-gray-500">
                  Nessun export registrato sui layer visibili.
                </p>
              ) : (
                <div className="mt-3 space-y-2">
                  {dashboard.latest_exports.slice(0, 4).map((item) => (
                    <div
                      key={`${item.layer_id}:${item.version_label}`}
                      className="rounded-2xl bg-white px-3 py-2 text-sm"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span className="font-semibold text-gray-900">
                          {item.layer_name}
                        </span>
                        <span className="rounded-full bg-[#eef3f9] px-2 py-1 text-xs font-semibold text-[#315d80]">
                          {item.status}
                        </span>
                      </div>
                      <p className="mt-1 font-mono text-xs text-gray-500">
                        {item.version_label}
                      </p>
                      <p className="text-xs text-gray-500">
                        {item.trigger ?? "manual"}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </section>
      ) : null}
      {pendingConfirmation ? (
        <ConfirmationDialog
          title={pendingConfirmation.title}
          description={pendingConfirmation.description}
          consequences={pendingConfirmation.consequences}
          confirmLabel={pendingConfirmation.confirmLabel}
          busy={confirmationBusy}
          error={confirmationError}
          tone={pendingConfirmation.tone}
          onCancel={() => setPendingConfirmation(null)}
          onConfirm={() => void confirmPendingAction()}
        />
      ) : null}
    </div>
  );
}

function MetricTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-[#e0dcc0] bg-white/70 p-4">
      <p className="text-3xl font-semibold tracking-tight">{value}</p>
      <p className="mt-1 text-xs font-semibold uppercase tracking-[0.14em] text-[#6a7340]">
        {label}
      </p>
    </div>
  );
}

function GuideCard({
  eyebrow,
  title,
  body,
}: {
  eyebrow: string;
  title: string;
  body: string;
}) {
  return (
    <article className="rounded-[26px] border border-[#d9dfd6] bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#59642f]">
        {eyebrow}
      </p>
      <h3 className="mt-3 text-lg font-semibold text-gray-950">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-gray-600">{body}</p>
    </article>
  );
}

function CatalogFact({
  label,
  value,
  description,
}: {
  label: string;
  value: string;
  description?: string;
}) {
  return (
    <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-600">
        {label}
      </p>
      <p className="mt-2 break-words text-sm font-semibold text-gray-800">
        {value}
      </p>
      {description ? (
        <p className="mt-2 text-xs leading-5 text-gray-500">{description}</p>
      ) : null}
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
      <div className="gis-touch-targets">
        <GisCatalogWorkspace token={token} />
      </div>
    </ProtectedPage>
  );
}
