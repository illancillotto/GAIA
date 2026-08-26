import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { GisQgisTools } from "@/app/gis/strumenti/qgis-tools";

const mocks = vi.hoisted(() => ({
  downloadGisQgisProject: vi.fn(),
  getGisOgcPoc: vi.fn(),
}));

vi.mock("@/lib/api/gis", () => ({
  downloadGisQgisProject: (...args: unknown[]) =>
    mocks.downloadGisQgisProject(...args),
  getGisOgcPoc: (...args: unknown[]) => mocks.getGisOgcPoc(...args),
}));

describe("GisQgisTools", () => {
  beforeEach(() => {
    Object.values(mocks).forEach((mock) => mock.mockReset());
  });

  test("downloads the QGIS project and renders the read-only OGC plan", async () => {
    const createObjectURL = vi.fn(() => "blob:qgis");
    const revokeObjectURL = vi.fn();
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
    const blob = new Blob(["qgz"]);
    mocks.downloadGisQgisProject.mockResolvedValue(blob);
    mocks.getGisOgcPoc.mockResolvedValue({
      recommended_server: "QGIS Server LTR",
      proxy_path: "/api/v1/gis/ogc",
      publishable_layer_count: 3,
      warnings: [],
      layers: [],
    });

    render(<GisQgisTools token="token" />);
    fireEvent.click(screen.getByRole("button", { name: "Scarica progetto QGIS" }));

    expect(await screen.findByText("Progetto QGIS scaricato.")).toBeInTheDocument();
    expect(mocks.downloadGisQgisProject).toHaveBeenCalledWith("token");
    expect(createObjectURL).toHaveBeenCalledWith(blob);
    expect(click).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:qgis");

    fireEvent.click(screen.getByRole("button", { name: "Verifica piano OGC" }));
    expect(await screen.findByText("QGIS Server LTR")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("Sola lettura")).toBeInTheDocument();

    click.mockRestore();
    vi.unstubAllGlobals();
  });

  test("shows explicit and fallback errors for QGIS and OGC", async () => {
    mocks.downloadGisQgisProject
      .mockRejectedValueOnce(new Error("download offline"))
      .mockRejectedValueOnce("offline");
    mocks.getGisOgcPoc
      .mockRejectedValueOnce(new Error("ogc offline"))
      .mockRejectedValueOnce("offline");

    const first = render(<GisQgisTools token="token" />);
    fireEvent.click(screen.getByRole("button", { name: "Scarica progetto QGIS" }));
    expect(await screen.findByText("download offline")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Verifica piano OGC" }));
    expect(await screen.findByText("ogc offline")).toBeInTheDocument();
    first.unmount();

    render(<GisQgisTools token="token" />);
    fireEvent.click(screen.getByRole("button", { name: "Scarica progetto QGIS" }));
    expect(await screen.findByText("Download QGIS non riuscito")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Verifica piano OGC" }));
    await waitFor(() =>
      expect(screen.getByText("Piano OGC non disponibile")).toBeInTheDocument(),
    );
  });
});
