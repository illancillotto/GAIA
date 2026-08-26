import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import {
  GuidedAnnotationComposer,
  GuidedChangeRequestComposer,
} from "@/app/gis/catalogo/guided-workflow-components";
import type {
  GisCatalogAnnotation,
  GisCatalogChangeRequest,
  GisCatalogLayer,
  GisCatalogLayerFeature,
  GisCatalogLayerFeatureListResponse,
} from "@/types/gis";

const mocks = vi.hoisted(() => ({ listGisLayerFeatures: vi.fn() }));

vi.mock("@/lib/api/gis", () => ({
  listGisLayerFeatures: (...args: unknown[]) =>
    mocks.listGisLayerFeatures(...args),
}));

const layer = {
  id: "layer-1",
  workspace: "rete",
  name: "condotte",
  title: "Condotte",
  domain_module: "network",
  source_type: "postgis",
  official_source: "network",
  geometry_type: "LINESTRING",
  feature_id_column: "id",
  metadata: {},
  is_active: true,
  effective_access_level: "editor",
  can_view: true,
  can_annotate: true,
  can_edit: true,
  can_approve: false,
  can_manage: false,
  created_at: "2026-08-25T08:00:00Z",
  updated_at: "2026-08-25T08:00:00Z",
} satisfies GisCatalogLayer;

const feature: GisCatalogLayerFeature = {
  feature_id: "pipe-1",
  label: "pipe-1 - Condotta principale",
  attributes: { id: "pipe-1", diameter: 120, active: true },
  geometry: {
    type: "LineString",
    coordinates: [
      [8.4, 39.9],
      [8.5, 40],
    ],
  },
};

const otherFeature: GisCatalogLayerFeature = {
  feature_id: "pipe-2",
  label: "pipe-2 - Condotta secondaria",
  attributes: { id: "pipe-2", diameter: 90 },
  geometry: null,
};

function featureResponse(
  items: GisCatalogLayerFeature[] = [feature],
  overrides: Partial<GisCatalogLayerFeatureListResponse> = {},
): GisCatalogLayerFeatureListResponse {
  return {
    items,
    total: items.length,
    limit: 20,
    offset: 0,
    has_more: false,
    ...overrides,
  };
}

const annotation: GisCatalogAnnotation = {
  id: "annotation-1",
  layer_id: layer.id,
  feature_id: feature.feature_id,
  title: "Nota esistente",
  body: "Testo esistente",
  geometry: null,
  attachment_refs: [],
  status: "open",
  created_by_user_id: 1,
  created_at: "2026-08-25T08:00:00Z",
  updated_at: "2026-08-25T08:00:00Z",
};

const changeRequest: GisCatalogChangeRequest = {
  id: "change-1",
  layer_id: layer.id,
  feature_id: feature.feature_id,
  change_type: "attribute_update",
  status: "submitted",
  payload: { before: { diameter: 120 }, after: { diameter: 160 } },
  justification: "Rilievo",
  requested_by_user_id: 1,
  reviewed_by_user_id: null,
  review_notes: null,
  reviewed_at: null,
  created_at: "2026-08-25T08:00:00Z",
  updated_at: "2026-08-25T08:00:00Z",
};

describe("guided GIS workflow components", () => {
  beforeEach(() => {
    mocks.listGisLayerFeatures.mockReset();
    mocks.listGisLayerFeatures.mockResolvedValue(featureResponse());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  test("searches and pages selectable features and reports both error shapes", async () => {
    mocks.listGisLayerFeatures
      .mockResolvedValueOnce(
        featureResponse([feature], { total: 45, has_more: true }),
      )
      .mockResolvedValueOnce(
        featureResponse([feature], { total: 45, has_more: true }),
      )
      .mockResolvedValueOnce(
        featureResponse([otherFeature], {
          total: 45,
          offset: 20,
          has_more: true,
        }),
      )
      .mockResolvedValueOnce(
        featureResponse([feature], { total: 45, has_more: true }),
      )
      .mockRejectedValueOnce(new Error("Ricerca non disponibile"))
      .mockRejectedValueOnce("offline");
    render(
      <GuidedAnnotationComposer
        token="token"
        layer={layer}
        busy={false}
        onSubmit={vi.fn()}
      />,
    );

    expect(await screen.findByText("45 elementi trovati")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Cerca per codice o descrizione"), {
      target: { value: " principale " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Cerca" }));
    await waitFor(() =>
      expect(mocks.listGisLayerFeatures).toHaveBeenLastCalledWith(
        "token",
        layer.id,
        " principale ",
        20,
        0,
      ),
    );

    fireEvent.click(screen.getByRole("button", { name: "Successivi" }));
    expect(
      await screen.findByRole("option", { name: otherFeature.label }),
    ).toBeInTheDocument();
    expect(screen.getByText("Da 21 a 40")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Precedenti" }));
    expect(
      await screen.findByRole("option", { name: feature.label }),
    ).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Elemento della mappa"), {
      target: { value: "missing" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Cerca" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Ricerca non disponibile",
    );
    fireEvent.click(screen.getByRole("button", { name: "Cerca" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Elementi della mappa non disponibili",
    );
  });

  test("reports both initial feature loading error shapes", async () => {
    mocks.listGisLayerFeatures.mockRejectedValueOnce(
      new Error("Caricamento iniziale non disponibile"),
    );
    const firstRender = render(
      <GuidedAnnotationComposer
        token="token"
        layer={layer}
        busy={false}
        onSubmit={vi.fn()}
      />,
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Caricamento iniziale non disponibile",
    );
    firstRender.unmount();

    mocks.listGisLayerFeatures.mockRejectedValueOnce("offline");
    render(
      <GuidedAnnotationComposer
        token="token"
        layer={layer}
        busy={false}
        onSubmit={vi.fn()}
      />,
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Elementi della mappa non disponibili",
    );
  });

  test("creates a note through validation, correction, retry and reset", async () => {
    const onSubmit = vi
      .fn()
      .mockResolvedValueOnce(false)
      .mockResolvedValueOnce(true);
    render(
      <GuidedAnnotationComposer
        token="token"
        layer={layer}
        busy={false}
        onSubmit={onSubmit}
      />,
    );
    await screen.findByRole("option", { name: feature.label });
    fireEvent.change(screen.getByLabelText("Elemento della mappa"), {
      target: { value: feature.feature_id },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continua" }));
    expect(screen.getByRole("heading", { name: "Descrivi quello che hai osservato" })).toHaveFocus();
    fireEvent.click(screen.getByRole("button", { name: "Indietro" }));
    expect(screen.getByRole("heading", { name: "Dove vuoi lasciare la nota?" })).toHaveFocus();
    fireEvent.click(screen.getByRole("button", { name: "Continua" }));
    fireEvent.click(screen.getByRole("button", { name: "Rivedi nota" }));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Inserisci un titolo breve",
    );
    fireEvent.change(screen.getByLabelText("Titolo breve"), {
      target: { value: " Nota " },
    });
    fireEvent.change(screen.getByLabelText("Descrizione"), {
      target: { value: " Testo " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Rivedi nota" }));
    expect(screen.getByRole("heading", { name: "Controlla prima di inviare" })).toHaveFocus();
    expect(screen.getByText(feature.label)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Correggi" }));
    expect(screen.getByRole("heading", { name: "Descrivi quello che hai osservato" })).toHaveFocus();
    fireEvent.click(screen.getByRole("button", { name: "Rivedi nota" }));
    fireEvent.click(
      screen.getByRole("button", { name: "Conferma e crea nota" }),
    );
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    fireEvent.click(
      screen.getByRole("button", { name: "Conferma e crea nota" }),
    );
    await waitFor(() =>
      expect(
        screen.getByText("Dove vuoi lasciare la nota?"),
      ).toBeInTheDocument(),
    );
    expect(onSubmit).toHaveBeenLastCalledWith({
      featureId: "pipe-1",
      title: "Nota",
      body: "Testo",
      attachmentRefs: [],
    });
  });

  test("reviews a note for the whole map without selecting a feature", async () => {
    render(
      <GuidedAnnotationComposer
        token="token"
        layer={layer}
        busy={false}
        onSubmit={vi.fn()}
      />,
    );
    await screen.findByText("1 elementi trovati");
    fireEvent.click(screen.getByRole("button", { name: "Continua" }));
    fireEvent.change(screen.getByLabelText("Titolo breve"), {
      target: { value: "Nota generale" },
    });
    fireEvent.change(screen.getByLabelText("Descrizione"), {
      target: { value: "Verifica complessiva" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Rivedi nota" }));

    expect(screen.getByText("Intera mappa")).toBeInTheDocument();
  });

  test("edits and cancels annotations while exposing busy feedback", async () => {
    const onCancel = vi.fn();
    const onSubmit = vi.fn().mockResolvedValue(true);
    const { unmount } = render(
      <GuidedAnnotationComposer
        token="token"
        layer={layer}
        annotation={annotation}
        busy={false}
        onSubmit={onSubmit}
        onCancel={onCancel}
      />,
    );
    await screen.findByRole("option", { name: feature.label });
    expect(screen.getByLabelText("Elemento della mappa")).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Annulla modifica" }));
    expect(onCancel).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Continua" }));
    expect(screen.getByRole("heading", { name: "Descrivi quello che hai osservato" })).toHaveFocus();
    fireEvent.click(screen.getByRole("button", { name: "Annulla modifica" }));
    fireEvent.click(screen.getByRole("button", { name: "Rivedi nota" }));
    fireEvent.click(
      screen.getByRole("button", { name: "Conferma aggiornamento" }),
    );
    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(screen.getByText("Controlla prima di inviare")).toBeInTheDocument();
    unmount();

    render(
      <GuidedAnnotationComposer
        token="token"
        layer={layer}
        annotation={annotation}
        busy
        onSubmit={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Continua" }));
    fireEvent.click(screen.getByRole("button", { name: "Rivedi nota" }));
    expect(
      screen.getByRole("button", { name: "Salvataggio..." }),
    ).toBeDisabled();
    expect(screen.getByRole("button", { name: "Correggi" })).toBeDisabled();
  });

  test("creates, retries and resets an attribute correction", async () => {
    const onSubmit = vi
      .fn()
      .mockResolvedValueOnce(false)
      .mockResolvedValueOnce(true);
    render(
      <GuidedChangeRequestComposer
        token="token"
        layer={layer}
        busy={false}
        onSubmit={onSubmit}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Continua" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Seleziona l'elemento");
    await screen.findByRole("option", { name: feature.label });
    fireEvent.change(screen.getByLabelText("Elemento della mappa"), {
      target: { value: feature.feature_id },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continua" }));
    expect(screen.getByRole("heading", { name: "Descrivi la correzione" })).toHaveFocus();
    fireEvent.click(screen.getByRole("button", { name: "Indietro" }));
    fireEvent.click(screen.getByRole("button", { name: "Continua" }));
    fireEvent.change(screen.getByLabelText("Dato da correggere"), {
      target: { value: "diameter" },
    });
    fireEvent.change(screen.getByLabelText("Nuovo valore"), {
      target: { value: "160" },
    });
    fireEvent.change(screen.getByLabelText("Motivazione"), {
      target: { value: " Rilievo " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Rivedi richiesta" }));
    expect(screen.getByRole("heading", { name: "Controlla le conseguenze" })).toHaveFocus();
    fireEvent.click(screen.getByRole("button", { name: "Correggi" }));
    expect(screen.getByRole("heading", { name: "Descrivi la correzione" })).toHaveFocus();
    fireEvent.click(screen.getByRole("button", { name: "Rivedi richiesta" }));
    fireEvent.click(screen.getByRole("button", { name: "Conferma e invia" }));
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    fireEvent.click(screen.getByRole("button", { name: "Conferma e invia" }));
    await waitFor(() =>
      expect(
        screen.getByText("Che tipo di correzione vuoi proporre?"),
      ).toBeInTheDocument(),
    );
  });

  test("guides feature creation through property and coordinate validation", async () => {
    const onSubmit = vi.fn().mockResolvedValue(true);
    render(
      <GuidedChangeRequestComposer
        token="token"
        layer={{ ...layer, geometry_type: "POINT" }}
        busy={false}
        onSubmit={onSubmit}
      />,
    );
    fireEvent.change(screen.getByLabelText("Tipo di correzione"), {
      target: { value: "feature_create" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continua" }));
    fireEvent.click(screen.getByRole("button", { name: "Rivedi richiesta" }));
    expect(screen.getByRole("alert")).toHaveTextContent("motivo");
    fireEvent.change(screen.getByLabelText("Motivazione"), {
      target: { value: "Nuovo rilievo" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Rivedi richiesta" }));
    expect(screen.getByRole("alert")).toHaveTextContent("dato descrittivo");
    fireEvent.change(screen.getByLabelText("Nome del dato"), {
      target: { value: "name" },
    });
    fireEvent.change(screen.getByLabelText("Valore"), {
      target: { value: "Nuovo punto" },
    });
    fireEvent.change(screen.getByPlaceholderText(/8\.4001/), {
      target: { value: "errate" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Rivedi richiesta" }));
    expect(screen.getByRole("alert")).toHaveTextContent("coordinate valide");
    fireEvent.change(screen.getByPlaceholderText(/8\.4001/), {
      target: { value: "8.4, 39.9" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Rivedi richiesta" }));
    expect(screen.getByText("Nuovo elemento")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Conferma e invia" }));
    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith({
        featureId: undefined,
        changeType: "feature_create",
        payload: {
          properties: { name: "Nuovo punto" },
          geometry: { type: "Point", coordinates: [8.4, 39.9] },
        },
        justification: "Nuovo rilievo",
      }),
    );
  });

  test("guides geometry and deletion requests and preserves edit mode", async () => {
    const geometrySubmit = vi.fn().mockResolvedValue(true);
    const { unmount } = render(
      <GuidedChangeRequestComposer
        token="token"
        layer={layer}
        busy={false}
        onSubmit={geometrySubmit}
      />,
    );
    await screen.findByRole("option", { name: feature.label });
    fireEvent.change(screen.getByLabelText("Elemento della mappa"), {
      target: { value: "" },
    });
    fireEvent.change(screen.getByLabelText("Elemento della mappa"), {
      target: { value: feature.feature_id },
    });
    fireEvent.change(screen.getByLabelText("Tipo di correzione"), {
      target: { value: "geometry_update" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continua" }));
    fireEvent.change(screen.getByLabelText("Motivazione"), {
      target: { value: "Nuovo tracciato" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Rivedi richiesta" }));
    fireEvent.click(screen.getByRole("button", { name: "Conferma e invia" }));
    await waitFor(() => expect(geometrySubmit).toHaveBeenCalled());
    unmount();

    const deleteSubmit = vi.fn().mockResolvedValue(true);
    render(
      <GuidedChangeRequestComposer
        token="token"
        layer={layer}
        busy={false}
        onSubmit={deleteSubmit}
      />,
    );
    await screen.findByRole("option", { name: feature.label });
    fireEvent.change(screen.getByLabelText("Elemento della mappa"), {
      target: { value: feature.feature_id },
    });
    fireEvent.change(screen.getByLabelText("Tipo di correzione"), {
      target: { value: "feature_delete" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continua" }));
    expect(screen.getByText(/proponendo l'eliminazione/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Motivazione"), {
      target: { value: "Doppione" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Rivedi richiesta" }));
    fireEvent.click(screen.getByRole("button", { name: "Conferma e invia" }));
    await waitFor(() => expect(deleteSubmit).toHaveBeenCalled());
  });

  test("cancels and submits existing corrections and renders busy state", async () => {
    const onCancel = vi.fn();
    const onSubmit = vi.fn().mockResolvedValue(true);
    const { unmount } = render(
      <GuidedChangeRequestComposer
        token="token"
        layer={layer}
        changeRequest={changeRequest}
        busy={false}
        onSubmit={onSubmit}
        onCancel={onCancel}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Annulla modifica" }));
    expect(onCancel).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Continua" }));
    fireEvent.click(screen.getByRole("button", { name: "Annulla modifica" }));
    fireEvent.click(screen.getByRole("button", { name: "Rivedi richiesta" }));
    fireEvent.click(
      screen.getByRole("button", { name: "Conferma aggiornamento" }),
    );
    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(screen.getByText("Controlla le conseguenze")).toBeInTheDocument();
    unmount();

    render(
      <GuidedChangeRequestComposer
        token="token"
        layer={layer}
        changeRequest={changeRequest}
        busy
        onSubmit={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Continua" }));
    fireEvent.click(screen.getByRole("button", { name: "Rivedi richiesta" }));
    expect(screen.getByRole("button", { name: "Invio..." })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Correggi" })).toBeDisabled();
  });

  test("ignores feature responses after unmount for resolve and reject", async () => {
    let resolveRequest:
      ((value: GisCatalogLayerFeatureListResponse) => void) | undefined;
    mocks.listGisLayerFeatures.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveRequest = resolve;
      }),
    );
    const first = render(
      <GuidedAnnotationComposer
        token="token"
        layer={layer}
        busy={false}
        onSubmit={vi.fn()}
      />,
    );
    first.unmount();
    resolveRequest?.(featureResponse());
    await Promise.resolve();

    let rejectRequest: ((reason: unknown) => void) | undefined;
    mocks.listGisLayerFeatures.mockReturnValueOnce(
      new Promise((_resolve, reject) => {
        rejectRequest = reject;
      }),
    );
    const second = render(
      <GuidedAnnotationComposer
        token="token"
        layer={layer}
        busy={false}
        onSubmit={vi.fn()}
      />,
    );
    second.unmount();
    rejectRequest?.(new Error("late"));
    await Promise.resolve();
  });
});
