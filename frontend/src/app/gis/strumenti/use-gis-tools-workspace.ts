import { type Dispatch, type SetStateAction, useEffect, useState } from "react";

import {
  createGisShapefileImport,
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

import {
  buildShapefileUpload,
  createAllGuidedChangeRequests,
  firstEditableLayerId,
  guidedChangesNotice,
  inferLayerName,
  isEditablePostgisLayer,
  readableError,
  type PendingImportAction,
} from "./tools-workspace-helpers";

type FeedbackSetters = {
  setBusy: Dispatch<SetStateAction<string | null>>;
  setError: Dispatch<SetStateAction<string | null>>;
  setNotice: Dispatch<SetStateAction<string | null>>;
  setHistoryVersion: Dispatch<SetStateAction<number>>;
  setPreview: Dispatch<SetStateAction<GisShapefileImportPreview | null>>;
  setSelectedImport: Dispatch<SetStateAction<GisShapefileImport | null>>;
};

function useGisToolsCatalog(
  token: string | null,
  setError: Dispatch<SetStateAction<string | null>>,
) {
  const [layers, setLayers] = useState<GisCatalogLayer[]>([]);
  const [targetLayerId, setTargetLayerId] = useState("");

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    void listGisCatalogLayers(token)
      .then((response) => {
        if (cancelled) return;
        setLayers(response.items);
        setTargetLayerId(firstEditableLayerId(response.items));
      })
      .catch((loadError: unknown) => {
        if (!cancelled) setError(readableError(loadError, "Catalogo GIS non disponibile"));
      });
    return () => {
      cancelled = true;
    };
  }, [setError, token]);

  return { layers, targetLayerId, setTargetLayerId };
}

function selectWorkspaceFile(
  nextFile: File | null,
  setFile: Dispatch<SetStateAction<File | null>>,
  setters: Pick<FeedbackSetters, "setPreview"> & {
    setLayerName: Dispatch<SetStateAction<string>>;
    setTitle: Dispatch<SetStateAction<string>>;
  },
) {
  setFile(nextFile);
  setters.setPreview(null);
  if (!nextFile) return;
  const inferredName = inferLayerName(nextFile.name);
  setters.setLayerName(inferredName);
  setters.setTitle((current) => current || inferredName.replace(/_/g, " "));
}

async function loadImportPreview(
  token: string | null,
  item: GisShapefileImport,
  setters: FeedbackSetters,
) {
  const currentToken = token as string;
  setters.setSelectedImport(item);
  if (item.status !== "validated" && item.status !== "published") {
    setters.setPreview(null);
    return;
  }
  setters.setBusy("preview");
  setters.setError(null);
  try {
    setters.setPreview(await previewGisShapefileImport(currentToken, item.id, 10, 0));
  } catch (previewError) {
    setters.setError(readableError(previewError, "Anteprima non disponibile"));
  } finally {
    setters.setBusy(null);
  }
}

async function uploadShapefile(
  input: {
    token: string | null;
    file: File | null;
    workspace: string;
    title: string;
    layerName: string;
    sourceSrid: string;
    encoding: string;
  },
  setters: FeedbackSetters,
) {
  const built = buildShapefileUpload(input);
  if (!built.ok) {
    setters.setError(built.error);
    return;
  }
  setters.setBusy("upload");
  setters.setError(null);
  try {
    const result = await createGisShapefileImport(built.token, built.payload);
    setters.setSelectedImport(result);
    setters.setNotice(`${result.target_layer_title} è stato controllato e salvato nell'area di prova.`);
    setters.setHistoryVersion((value) => value + 1);
    await loadImportPreview(built.token, result, setters);
  } catch (uploadError) {
    setters.setError(readableError(uploadError, "Import non riuscito"));
  } finally {
    setters.setBusy(null);
  }
}

async function runPendingImportAction(
  session: {
    token: string | null;
    selectedImport: GisShapefileImport | null;
    preview: GisShapefileImportPreview | null;
    pendingAction: PendingImportAction | null;
  },
  setters: FeedbackSetters & { setPendingAction: Dispatch<SetStateAction<PendingImportAction | null>> },
) {
  const currentToken = session.token as string;
  const currentImport = session.selectedImport as GisShapefileImport;
  const action = session.pendingAction as PendingImportAction;
  setters.setBusy(action);
  setters.setError(null);
  try {
    const updated = action === "publish"
      ? await publishGisShapefileImport(currentToken, currentImport.id)
      : await rejectGisShapefileImport(currentToken, currentImport.id);
    setters.setSelectedImport(updated);
    setters.setPreview(action === "reject" ? null : session.preview);
    setters.setPendingAction(null);
    setters.setNotice(action === "publish" ? "Import pubblicato nel catalogo." : "Import rigettato e area di prova rimossa.");
    setters.setHistoryVersion((value) => value + 1);
  } catch (actionError) {
    setters.setError(readableError(actionError, "Operazione import non riuscita"));
  } finally {
    setters.setBusy(null);
  }
}

async function submitGuidedChanges(
  session: {
    token: string | null;
    selectedImport: GisShapefileImport | null;
    targetLayerId: string;
    justification: string;
  },
  setters: FeedbackSetters,
) {
  if (!session.token || !session.selectedImport || !session.targetLayerId || !session.justification.trim()) {
    setters.setError("Scegli la mappa da correggere e descrivi il motivo della proposta.");
    return;
  }
  setters.setBusy("changes");
  setters.setError(null);
  try {
    const result = await createAllGuidedChangeRequests(
      session.token,
      session.selectedImport.id,
      session.targetLayerId,
      session.justification.trim(),
    );
    setters.setNotice(guidedChangesNotice(result.created, result.existing));
    setters.setHistoryVersion((value) => value + 1);
  } catch (changeError) {
    setters.setError(readableError(changeError, "Creazione proposte non riuscita"));
  } finally {
    setters.setBusy(null);
  }
}

export type GisToolsWorkspaceView = {
  busy: string | null;
  editableLayers: GisCatalogLayer[];
  encoding: string;
  error: string | null;
  historyVersion: number;
  justification: string;
  layerName: string;
  layers: GisCatalogLayer[];
  notice: string | null;
  pendingAction: PendingImportAction | null;
  preview: GisShapefileImportPreview | null;
  selectedImport: GisShapefileImport | null;
  sourceSrid: string;
  targetLayerId: string;
  title: string;
  workspace: string;
  cancelPendingAction: () => void;
  confirmImportAction: () => void;
  createGuidedChanges: () => void;
  loadPreview: (item: GisShapefileImport) => void;
  selectFile: (nextFile: File | null) => void;
  setEncoding: Dispatch<SetStateAction<string>>;
  setJustification: Dispatch<SetStateAction<string>>;
  setLayerName: Dispatch<SetStateAction<string>>;
  setPendingAction: Dispatch<SetStateAction<PendingImportAction | null>>;
  setSourceSrid: Dispatch<SetStateAction<string>>;
  setTargetLayerId: Dispatch<SetStateAction<string>>;
  setTitle: Dispatch<SetStateAction<string>>;
  setWorkspace: Dispatch<SetStateAction<string>>;
  uploadImport: () => void;
};

export function useGisToolsWorkspace(token: string | null): GisToolsWorkspaceView {
  const [file, setFile] = useState<File | null>(null);
  const [workspace, setWorkspace] = useState("rete");
  const [title, setTitle] = useState("");
  const [layerName, setLayerName] = useState("");
  const [sourceSrid, setSourceSrid] = useState("");
  const [encoding, setEncoding] = useState("");
  const [selectedImport, setSelectedImport] = useState<GisShapefileImport | null>(null);
  const [preview, setPreview] = useState<GisShapefileImportPreview | null>(null);
  const [justification, setJustification] = useState("");
  const [pendingAction, setPendingAction] = useState<PendingImportAction | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [historyVersion, setHistoryVersion] = useState(0);
  const catalog = useGisToolsCatalog(token, setError);
  const setters: FeedbackSetters = {
    setBusy, setError, setNotice, setHistoryVersion, setPreview, setSelectedImport,
  };

  return {
    busy,
    editableLayers: catalog.layers.filter(isEditablePostgisLayer),
    encoding,
    error,
    historyVersion,
    justification,
    layerName,
    layers: catalog.layers,
    notice,
    pendingAction,
    preview,
    selectedImport,
    sourceSrid,
    targetLayerId: catalog.targetLayerId,
    title,
    workspace,
    cancelPendingAction: () => setPendingAction(null),
    confirmImportAction: () => {
      void runPendingImportAction(
        { token, selectedImport, preview, pendingAction },
        { ...setters, setPendingAction },
      );
    },
    createGuidedChanges: () => {
      void submitGuidedChanges(
        { token, selectedImport, targetLayerId: catalog.targetLayerId, justification },
        setters,
      );
    },
    loadPreview: (item) => {
      void loadImportPreview(token, item, setters);
    },
    selectFile: (nextFile) => {
      selectWorkspaceFile(nextFile, setFile, { setPreview, setLayerName, setTitle });
    },
    setEncoding,
    setJustification,
    setLayerName,
    setPendingAction,
    setSourceSrid,
    setTargetLayerId: catalog.setTargetLayerId,
    setTitle,
    setWorkspace,
    uploadImport: () => {
      void uploadShapefile({ token, file, workspace, title, layerName, sourceSrid, encoding }, setters);
    },
  };
}
