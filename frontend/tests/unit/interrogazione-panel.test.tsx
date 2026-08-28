import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

const api = vi.hoisted(() => ({ interroga: vi.fn() }));

vi.mock("@/lib/api/territorio", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/api/territorio")>();
  return { ...original, interrogaGisTerritorio: api.interroga };
});

import InterrogazionePanel from "@/components/catasto/gis/InterrogazionePanel";
import {
  useInterrogazione,
  type InterrogazioneMap,
  type InterrogazioneState,
  type InterrogazioneViewSource,
} from "@/components/catasto/gis/use-interrogazione";
import type { GisInterrogazioneResponse, GisTerritorioLayerGroup } from "@/lib/api/territorio";

function source(overrides: Partial<InterrogazioneViewSource> = {}): InterrogazioneViewSource {
  return {
    source_id: "source-1",
    title: "Particella GAIA",
    status: "ok",
    duration_ms: 12,
    data: [{ foglio: "12", particella: "34", vuoto: null }],
    message: null,
    ...overrides,
  };
}

function state(overrides: Partial<InterrogazioneState> = {}): InterrogazioneState {
  return {
    open: true,
    armed: false,
    point: { lon: 9, lat: 40 },
    gaia: [source()],
    catastoUfficiale: [source({ source_id: "ade", title: "Catasto AdE", status: "empty", data: [], message: "Nessun elemento trovato.", attribution: "Dati AdE" })],
    territorio: [
      source({ source_id: "ras-loading", title: "Vincolo", status: "loading", data: [], theme: "vincoli", themeLabel: "Vincoli e tutele", attribution: "Dati RAS" }),
      source({ source_id: "ras-failed", title: "Reticolo", status: "failed", data: [], message: "timeout", theme: "idrografia", themeLabel: "Acque e reticolo" }),
      source({ source_id: "ras-skipped", title: "Ortofoto", status: "skipped", data: [], message: "Solo visualizzazione", theme: "ortofoto", themeLabel: "Ortofoto storiche" }),
      source({ source_id: "other", title: "Altro", status: "empty", data: [] }),
    ],
    arm: vi.fn(),
    close: vi.fn(),
    ...overrides,
  };
}

const scheda = {
  parcelId: null,
  sheet: null,
  error: null,
  downloadUrl: null,
  generate: vi.fn(),
};

describe("InterrogazionePanel", () => {
  test("renders every source state, data, attribution and disabled M24 action", () => {
    render(<InterrogazionePanel {...state()} scheda={scheda} />);
    expect(screen.getByText("Risultato disponibile")).toBeInTheDocument();
    expect(screen.getAllByText("Nessun risultato")).toHaveLength(2);
    expect(screen.getByText("In caricamento")).toBeInTheDocument();
    expect(screen.getByText("Sorgente non raggiungibile")).toBeInTheDocument();
    expect(screen.getByText("Non interrogabile")).toBeInTheDocument();
    expect(screen.getByText("34")).toBeInTheDocument();
    expect(screen.getByText("-")).toBeInTheDocument();
    expect(screen.getByText("Dati AdE")).toBeInTheDocument();
    expect(screen.getByText("Dati RAS")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Genera scheda territoriale/ })).toBeDisabled();
    expect(screen.getByRole("region", { name: "Vincoli e tutele" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "altro" })).toBeInTheDocument();
  });

  test("keeps GAIA open and lets official and territory sections collapse", () => {
    render(<InterrogazionePanel {...state()} scheda={scheda} />);
    expect(screen.getByRole("region", { name: "GAIA" })).toBeInTheDocument();
    const official = screen.getByText("Catasto ufficiale").closest("details");
    const territory = screen.getByText("Territorio").closest("details");
    expect(official).toHaveAttribute("open");
    expect(territory).toHaveAttribute("open");
    fireEvent.click(screen.getByText("Catasto ufficiale"));
    fireEvent.click(screen.getByText("Territorio"));
    expect(official).not.toHaveAttribute("open");
    expect(territory).not.toHaveAttribute("open");
  });

  test("arms from the closed control, shows instructions and closes", () => {
    const closed = state({ open: false });
    const { rerender } = render(<InterrogazionePanel {...closed} scheda={scheda} />);
    fireEvent.click(screen.getByRole("button", { name: "Interroga punto" }));
    expect(closed.arm).toHaveBeenCalledOnce();
    const armed = state({ armed: true, point: null, gaia: [], catastoUfficiale: [], territorio: [] });
    rerender(<InterrogazionePanel {...armed} scheda={scheda} />);
    expect(screen.getByText(/Clicca un punto/)).toBeInTheDocument();
    expect(screen.getAllByText("Nessuna sorgente disponibile.")).toHaveLength(3);
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    expect(armed.close).toHaveBeenCalledOnce();
  });
});

const groups: GisTerritorioLayerGroup[] = [{
  theme: "vincoli",
  label: "Vincoli e tutele",
  layers: [
    { id: "ras-1", name: "ras", title: "RAS", description: null, theme: "vincoli", source: "ras_sitr", proxy_wms_url: "", legend_url: "", default_opacity: 0.6, render_order: 1, queryable: "wfs_queryable", attribution: "RAS attribution" },
    { id: "visual", name: "visual", title: "Ortofoto", description: null, theme: "vincoli", source: "ras_sitr", proxy_wms_url: "", legend_url: "", default_opacity: 1, render_order: 2, queryable: "wms_visual_only", attribution: "RAS attribution" },
  ],
}, {
  theme: "catasto_ufficiale",
  label: "Cartografia catastale ufficiale",
  layers: [{ id: "ade-1", name: "ade", title: "AdE", description: null, theme: "catasto_ufficiale", source: "agenzia_entrate", proxy_wms_url: "", legend_url: "", default_opacity: 0.6, render_order: 3, queryable: "wms_infoable", attribution: "AdE attribution" }],
}];

function response(layerId?: string): GisInterrogazioneResponse {
  const remote = layerId ? { source_id: layerId, title: layerId, status: "ok" as const, duration_ms: 5, data: [{ id: layerId }], message: null } : null;
  return {
    lon: 9,
    lat: 40,
    srid: 4326,
    radius_m: 150,
    gaia: { key: "gaia", sources: [source({ source_id: "particella" })] },
    catasto_ufficiale: { key: "catasto_ufficiale", sources: layerId === "ade-1" && remote ? [remote] : [] },
    territorio: { key: "territorio", sources: layerId === "ras-1" && remote ? [remote] : [] },
  };
}

class FakeMap implements InterrogazioneMap {
  listener: ((event: { lngLat: { lng: number; lat: number } }) => void) | null = null;
  on = vi.fn((event: "click", listener: NonNullable<FakeMap["listener"]>) => { this.listener = listener; });
  off = vi.fn((event: "click", listener: NonNullable<FakeMap["listener"]>) => { if (this.listener === listener) this.listener = null; });
}

function Harness({ map, onState }: { map: FakeMap; onState: (value: InterrogazioneState) => void }) {
  const value = useInterrogazione(map, "token", groups);
  useEffect(() => onState(value), [onState, value]);
  return <button onClick={value.arm}>arm</button>;
}

describe("useInterrogazione", () => {
  beforeEach(() => api.interroga.mockReset());

  test("arms one map click and publishes local and remote responses progressively", async () => {
    const map = new FakeMap();
    let current: InterrogazioneState | null = null;
    api.interroga.mockImplementation((...args: unknown[]) => {
      const body = args.find((item): item is { layer_ids: string[] } => typeof item === "object" && item !== null && "layer_ids" in item);
      return Promise.resolve(response(body?.layer_ids[0]));
    });
    const { unmount } = render(<Harness map={map} onState={(value) => { current = value; }} />);
    fireEvent.click(screen.getByText("arm"));
    expect(current?.armed).toBe(true);
    act(() => map.listener?.({ lngLat: { lng: 9, lat: 40 } }));
    expect(current?.point).toEqual({ lon: 9, lat: 40 });
    expect(current?.territorio.map((item) => item.status)).toEqual(["loading", "skipped"]);
    await waitFor(() => expect(current?.gaia[0]?.status).toBe("ok"));
    await waitFor(() => expect(current?.territorio[0]?.status).toBe("ok"));
    await waitFor(() => expect(current?.catastoUfficiale[0]?.status).toBe("ok"));
    expect(api.interroga).toHaveBeenCalledTimes(3);
    expect(api.interroga).not.toHaveBeenCalledWith("token", expect.objectContaining({ layer_ids: ["visual"] }));
    act(() => current?.close());
    expect(current?.open).toBe(false);
    unmount();
    expect(map.off).toHaveBeenCalled();
  });

  test("maps local and remote failures without aborting remaining sources", async () => {
    const map = new FakeMap();
    let current: InterrogazioneState | null = null;
    api.interroga.mockRejectedValueOnce(new Error("GAIA down"))
      .mockRejectedValueOnce(new Error("RAS down"))
      .mockResolvedValueOnce({ ...response(), catasto_ufficiale: { key: "catasto_ufficiale", sources: [] } });
    render(<Harness map={map} onState={(value) => { current = value; }} />);
    fireEvent.click(screen.getByText("arm"));
    act(() => map.listener?.({ lngLat: { lng: 9, lat: 40 } }));
    await waitFor(() => expect(current?.gaia.every((item) => item.status === "failed")).toBe(true));
    await waitFor(() => expect(current?.territorio[0]?.message).toBe("RAS down"));
    await waitFor(() => expect(current?.catastoUfficiale[0]?.status).toBe("failed"));
  });
});
