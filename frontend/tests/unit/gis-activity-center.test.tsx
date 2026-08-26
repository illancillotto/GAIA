import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { GisActivityCenter } from "@/app/gis/strumenti/activity-center";
import type { GisCatalogLayer } from "@/types/gis";

const mocks = vi.hoisted(() => ({
  listGisAuditLogs: vi.fn(),
  listGisCatalogLayerExports: vi.fn(),
  listGisShapefileImports: vi.fn(),
}));

vi.mock("@/lib/api/gis", () => ({
  listGisAuditLogs: (...args: unknown[]) => mocks.listGisAuditLogs(...args),
  listGisCatalogLayerExports: (...args: unknown[]) => mocks.listGisCatalogLayerExports(...args),
  listGisShapefileImports: (...args: unknown[]) => mocks.listGisShapefileImports(...args),
}));

const layer = {
  id: "layer-1",
  workspace: "rete",
  name: "rete",
  title: "Condotte",
  source_type: "postgis",
  official_source: "postgis",
  metadata: {},
  is_active: true,
  effective_access_level: "viewer",
  can_view: true,
  can_annotate: false,
  can_edit: false,
  can_approve: false,
  can_manage: false,
  created_at: "2026-08-25T08:00:00Z",
  updated_at: "2026-08-25T08:00:00Z",
} satisfies GisCatalogLayer;

const importItem = {
  id: "import-1",
  status: "validated" as const,
  original_filename: "rete.zip",
  workspace: "rete",
  target_layer_name: "rete_import",
  target_layer_title: "Rete importata",
  official_source: "shapefile_upload",
  source_srid: 4326,
  encoding: "utf-8",
  staging_table: "import_1",
  feature_count: 3,
  fields: [],
  validation_report: {},
  metadata: {},
  checksum_sha256: "a".repeat(64),
  created_at: "2026-08-25T08:00:00Z",
  updated_at: "2026-08-25T09:00:00Z",
};

describe("GisActivityCenter", () => {
  beforeEach(() => {
    Object.values(mocks).forEach((mock) => mock.mockReset());
    mocks.listGisShapefileImports.mockResolvedValue({ items: [importItem], total: 1, limit: 25, offset: 0, has_more: false });
    mocks.listGisCatalogLayerExports.mockResolvedValue({ items: [{ id: "export-1", layer_id: "layer-1", version_label: "v1", status: "completed", nas_path: "/nas/v1.zip", metadata: {}, created_at: "2026-08-25T09:30:00Z" }], total: 1, limit: 25, offset: 0, has_more: false });
    mocks.listGisAuditLogs.mockResolvedValue({ items: [{ id: "audit-1", event_type: "export.completed", target_type: "export", payload: {}, created_at: "2026-08-25T09:30:00Z" }], total: 1, limit: 25, offset: 0, has_more: false });
  });

  test("renders persistent histories, resumes imports and optionally shows audit", async () => {
    const onResume = vi.fn();
    render(<GisActivityCenter token="token" layers={[layer]} showAudit onResumeImport={onResume} />);

    expect(await screen.findByText("Rete importata")).toBeInTheDocument();
    expect(screen.getByText("Condotte")).toBeInTheDocument();
    expect(screen.getByText("Consulta audit amministrativo (1)")).toBeInTheDocument();
    expect(mocks.listGisAuditLogs).toHaveBeenCalledWith("token", { limit: 25 });
    fireEvent.click(screen.getByRole("button", { name: "Riprendi" }));
    expect(onResume).toHaveBeenCalledWith(importItem);
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna storico" }));
    await waitFor(() => expect(mocks.listGisShapefileImports).toHaveBeenCalledTimes(2));
  });

  test("hides audit for operators and renders empty histories", async () => {
    mocks.listGisShapefileImports.mockResolvedValueOnce({ items: [], total: 0, limit: 25, offset: 0, has_more: false });
    mocks.listGisCatalogLayerExports.mockResolvedValueOnce({ items: [], total: 0, limit: 25, offset: 0, has_more: false });
    render(<GisActivityCenter token="token" layers={[]} />);

    expect(await screen.findByText("Nessun import registrato.")).toBeInTheDocument();
    expect(screen.getByText("Nessun export registrato.")).toBeInTheDocument();
    expect(screen.queryByText(/audit amministrativo/)).not.toBeInTheDocument();
    expect(mocks.listGisAuditLogs).not.toHaveBeenCalled();
  });

  test("uses fallback labels and reports both error forms", async () => {
    mocks.listGisCatalogLayerExports.mockResolvedValueOnce({ items: [{ id: "export-2", layer_id: "missing", version_label: "v2", status: "failed", nas_path: "/nas/v2.zip", metadata: {}, created_at: "2026-08-25T09:30:00Z" }], total: 1, limit: 25, offset: 0, has_more: false });
    const fallback = render(<GisActivityCenter token="token" layers={[]} />);
    expect(await screen.findByText("Mappa non disponibile")).toBeInTheDocument();
    fallback.unmount();

    mocks.listGisShapefileImports.mockRejectedValueOnce(new Error("history offline"));
    const failed = render(<GisActivityCenter token="token" layers={[]} />);
    expect(await screen.findByText("history offline")).toBeInTheDocument();
    failed.unmount();

    mocks.listGisShapefileImports.mockRejectedValueOnce("offline");
    render(<GisActivityCenter token="token" layers={[]} />);
    expect(await screen.findByText("Storico GIS non disponibile")).toBeInTheDocument();
  });

  test("ignores history responses after unmount", async () => {
    let resolveImports: (value: unknown) => void = () => undefined;
    mocks.listGisShapefileImports.mockReturnValue(new Promise((resolve) => { resolveImports = resolve; }));
    const { unmount } = render(<GisActivityCenter token="token" layers={[]} />);
    unmount();
    resolveImports({ items: [], total: 0, limit: 25, offset: 0, has_more: false });
    await waitFor(() => expect(mocks.listGisShapefileImports).toHaveBeenCalled());

    mocks.listGisShapefileImports.mockRejectedValueOnce(new Error("late"));
    const rejected = render(<GisActivityCenter token="token" layers={[]} />);
    rejected.unmount();
    await waitFor(() => expect(mocks.listGisShapefileImports).toHaveBeenCalled());
  });

  test("falls back to raw import status and generic audit target labels", async () => {
    mocks.listGisShapefileImports.mockResolvedValueOnce({ items: [{ ...importItem, status: "custom_status" }], total: 1, limit: 25, offset: 0, has_more: false });
    mocks.listGisAuditLogs.mockResolvedValueOnce({ items: [{ id: "audit-2", event_type: "custom", target_type: null, payload: {}, created_at: "2026-08-25T09:30:00Z" }], total: 1, limit: 25, offset: 0, has_more: false });
    render(<GisActivityCenter token="token" layers={[]} showAudit />);
    expect(await screen.findByText(/custom_status/)).toBeInTheDocument();
    expect(screen.getByText(/GIS ·/)).toBeInTheDocument();
  });
});
