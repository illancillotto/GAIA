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
    point: { lon: 9, lat: 40 },
    gaia: [source()],
    catastoUfficiale: [source({ source_id: "ade", title: "Catasto AdE", status: "empty", data: [], message: "Nessun elemento trovato.", attribution: "Dati AdE" })],
    territorio: [
      source({ source_id: "ras-loading", title: "Vincolo", status: "loading", data: [], theme: "vincoli", themeLabel: "Vincoli e tutele", attribution: "Dati RAS" }),
      source({ source_id: "ras-failed", title: "Reticolo", status: "failed", data: [], message: "timeout", theme: "idrografia", themeLabel: "Acque e reticolo" }),
      source({ source_id: "ras-skipped", title: "Ortofoto", status: "skipped", data: [], message: "Solo visualizzazione", theme: "ortofoto", themeLabel: "Ortofoto storiche" }),
      source({ source_id: "other", title: "Altro", status: "empty", data: [] }),
    ],
    interrogate: vi.fn(),
    clear: vi.fn(),
    ...overrides,
  };
}

const scheda = {
  token: "token",
  particellaId: null,
  currentUser: { enabled_modules: ["gis"], role: "viewer" },
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
    expect(screen.queryByRole("button", { name: /Genera scheda territoriale/ })).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Vincoli e tutele" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "altro" })).toBeInTheDocument();
  });

  test("keeps GAIA open and lets official and territory sections collapse", () => {
    render(<InterrogazionePanel {...state()} scheda={scheda} />);
    expect(screen.getByRole("region", { name: "GAIA" })).toBeInTheDocument();
    const container = screen.getByText("Dati territoriali sul punto").closest("details");
    const official = screen.getByText("Catasto ufficiale").closest("details");
    const territory = screen.getByText("Territorio").closest("details");
    expect(container).not.toHaveAttribute("open");
    expect(official).not.toHaveAttribute("open");
    expect(territory).not.toHaveAttribute("open");
    fireEvent.click(screen.getByText("Dati territoriali sul punto"));
    fireEvent.click(screen.getByText("Catasto ufficiale"));
    fireEvent.click(screen.getByText("Territorio"));
    expect(container).toHaveAttribute("open");
    expect(official).toHaveAttribute("open");
    expect(territory).toHaveAttribute("open");
  });

  test("renders only when a parcel click has supplied a point", () => {
    const { container } = render(<InterrogazionePanel {...state({ point: null })} scheda={scheda} />);
    expect(container).toBeEmptyDOMElement();
    expect(screen.queryByRole("button", { name: "Interroga punto" })).not.toBeInTheDocument();
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

function Harness({ token = "token", onState }: { token?: string | null; onState: (value: InterrogazioneState) => void }) {
  const value = useInterrogazione(token, groups);
  useEffect(() => onState(value), [onState, value]);
  return <><button onClick={() => value.interrogate({ lon: 9, lat: 40 })}>interrogate</button><button onClick={value.clear}>clear</button></>;
}

describe("useInterrogazione", () => {
  beforeEach(() => api.interroga.mockReset());

  test("publishes local and remote responses progressively for the parcel click", async () => {
    let current: InterrogazioneState | null = null;
    api.interroga.mockImplementation((...args: unknown[]) => {
      const body = args.find((item): item is { layer_ids: string[] } => typeof item === "object" && item !== null && "layer_ids" in item);
      return Promise.resolve(response(body?.layer_ids[0]));
    });
    render(<Harness onState={(value) => { current = value; }} />);
    fireEvent.click(screen.getByText("interrogate"));
    expect(current?.point).toEqual({ lon: 9, lat: 40 });
    expect(current?.territorio.map((item) => item.status)).toEqual(["loading", "skipped"]);
    await waitFor(() => expect(current?.gaia[0]?.status).toBe("ok"));
    await waitFor(() => expect(current?.territorio[0]?.status).toBe("ok"));
    await waitFor(() => expect(current?.catastoUfficiale[0]?.status).toBe("ok"));
    expect(api.interroga).toHaveBeenCalledTimes(3);
    expect(api.interroga).not.toHaveBeenCalledWith("token", expect.objectContaining({ layer_ids: ["visual"] }));
    fireEvent.click(screen.getByText("clear"));
    expect(current?.point).toBeNull();
    expect(current?.gaia).toEqual([]);
  });

  test("maps local and remote failures without aborting remaining sources", async () => {
    let current: InterrogazioneState | null = null;
    api.interroga.mockRejectedValueOnce(new Error("GAIA down"))
      .mockRejectedValueOnce(new Error("RAS down"))
      .mockResolvedValueOnce({ ...response(), catasto_ufficiale: { key: "catasto_ufficiale", sources: [] } });
    render(<Harness onState={(value) => { current = value; }} />);
    fireEvent.click(screen.getByText("interrogate"));
    await waitFor(() => expect(current?.gaia.every((item) => item.status === "failed")).toBe(true));
    await waitFor(() => expect(current?.territorio[0]?.message).toBe("RAS down"));
    await waitFor(() => expect(current?.catastoUfficiale[0]?.status).toBe("failed"));
  });

  test("does not query without a token and ignores stale parcel responses", async () => {
    let anonymous: InterrogazioneState | null = null;
    const anonymousView = render(<Harness token={null} onState={(value) => { anonymous = value; }} />);
    fireEvent.click(screen.getByText("interrogate"));
    expect(anonymous?.point).toBeNull();
    expect(api.interroga).not.toHaveBeenCalled();
    anonymousView.unmount();

    let resolveFirst: ((value: GisInterrogazioneResponse) => void) | null = null;
    api.interroga
      .mockImplementationOnce(() => new Promise((resolve) => { resolveFirst = resolve; }))
      .mockResolvedValue(response())
      .mockResolvedValue(response())
      .mockResolvedValue(response());
    let current: InterrogazioneState | null = null;
    render(<Harness onState={(value) => { current = value; }} />);
    fireEvent.click(screen.getByText("interrogate"));
    fireEvent.click(screen.getByText("clear"));
    act(() => resolveFirst?.(response()));
    await act(async () => { await Promise.resolve(); });
    expect(current?.point).toBeNull();
    expect(current?.gaia).toEqual([]);

    let rejectNext: ((reason: Error) => void) | null = null;
    api.interroga.mockReset();
    api.interroga
      .mockImplementationOnce(() => new Promise((_, reject) => { rejectNext = reject; }))
      .mockResolvedValue(response())
      .mockResolvedValue(response());
    fireEvent.click(screen.getByText("interrogate"));
    fireEvent.click(screen.getByText("clear"));
    act(() => rejectNext?.(new Error("stale")));
    await act(async () => { await Promise.resolve(); });
    expect(current?.point).toBeNull();
    expect(current?.gaia).toEqual([]);
  });
});
