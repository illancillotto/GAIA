import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

const api = vi.hoisted(() => ({ create: vi.fn(), get: vi.fn(), download: vi.fn() }));
vi.mock("@/lib/api/territorio", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/territorio")>()),
  createGisSchedaTerritoriale: api.create,
  getGisSchedaTerritoriale: api.get,
  downloadGisSchedaTerritoriale: api.download,
}));

import InterrogazionePanel from "@/components/catasto/gis/InterrogazionePanel";
import { useSchedaTerritoriale, type SchedaTerritorialeState } from "@/components/catasto/gis/use-scheda-territoriale";
import type { InterrogazioneState } from "@/components/catasto/gis/use-interrogazione";
import type { GisSchedaTerritoriale } from "@/lib/api/territorio";

function sheet(status: GisSchedaTerritoriale["status"]): GisSchedaTerritoriale {
  return { id: "sheet-1", particella_id: "parcel-1", status, artifact_path: null, checksum_sha256: null, source_snapshot: {}, error_message: null };
}

function Harness({ onState, token = "token", parcelId = "parcel-1" }: { onState: (value: SchedaTerritorialeState) => void; token?: string | null; parcelId?: unknown }) {
  const value = useSchedaTerritoriale(token, [{ source_id: "particella", data: [{ id: parcelId }] }]);
  useEffect(() => onState(value), [onState, value]);
  return <button onClick={value.generate}>generate</button>;
}

describe("scheda territoriale", () => {
  beforeEach(() => {
    vi.useRealTimers();
    api.create.mockReset(); api.get.mockReset(); api.download.mockReset();
    vi.stubGlobal("URL", { createObjectURL: vi.fn(() => "blob:sheet"), revokeObjectURL: vi.fn() });
  });

  test("creates, polls, downloads and revokes the completed PDF", async () => {
    vi.useFakeTimers();
    let current: SchedaTerritorialeState | null = null;
    api.create.mockResolvedValue(sheet("queued"));
    api.get.mockResolvedValue(sheet("completed"));
    api.download.mockResolvedValue(new Blob(["pdf"]));
    const { rerender, unmount } = render(<Harness onState={(value) => { current = value; }} />);
    fireEvent.click(screen.getByText("generate"));
    await act(async () => { await Promise.resolve(); });
    expect(api.create).toHaveBeenCalledWith("token", "parcel-1");
    await act(async () => { await vi.advanceTimersByTimeAsync(1000); });
    await act(async () => { await Promise.resolve(); await Promise.resolve(); });
    expect(current?.downloadUrl).toBe("blob:sheet");
    expect(api.get).toHaveBeenCalledWith("token", "sheet-1");
    expect(api.download).toHaveBeenCalledWith("token", "sheet-1");
    rerender(<Harness parcelId="parcel-2" onState={(value) => { current = value; }} />);
    await act(async () => { await Promise.resolve(); });
    expect(current?.sheet).toBeNull();
    expect(current?.downloadUrl).toBeNull();
    unmount();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:sheet");
  });

  test("reports create, polling and download errors and ignores missing context", async () => {
    let current: SchedaTerritorialeState | null = null;
    api.create.mockRejectedValueOnce(new Error("create down"));
    const { rerender } = render(<Harness onState={(value) => { current = value; }} />);
    fireEvent.click(screen.getByText("generate"));
    await waitFor(() => expect(current?.error).toBe("create down"));
    rerender(<Harness token={null} onState={(value) => { current = value; }} />);
    fireEvent.click(screen.getByText("generate"));
    expect(api.create).toHaveBeenCalledTimes(1);

    rerender(<Harness token="token" parcelId={7} onState={(value) => { current = value; }} />);
    expect(current?.parcelId).toBeNull();
  });

  test("reports polling and download failures", async () => {
    vi.useFakeTimers();
    let current: SchedaTerritorialeState | null = null;
    api.create.mockResolvedValueOnce(sheet("processing"));
    api.get.mockRejectedValueOnce("poll down");
    const { unmount } = render(<Harness onState={(value) => { current = value; }} />);
    fireEvent.click(screen.getByText("generate"));
    await act(async () => { await Promise.resolve(); });
    await act(async () => { await vi.advanceTimersByTimeAsync(1000); await Promise.resolve(); });
    expect(current?.error).toBe("poll down");
    unmount();

    vi.useRealTimers();
    api.create.mockResolvedValueOnce(sheet("completed"));
    api.download.mockRejectedValueOnce(new Error("download down"));
    render(<Harness onState={(value) => { current = value; }} />);
    fireEvent.click(screen.getByText("generate"));
    await waitFor(() => expect(current?.error).toBe("download down"));
  });

  test("normalizes alternate API rejection values", async () => {
    let current: SchedaTerritorialeState | null = null;
    api.create.mockRejectedValueOnce("create string");
    const first = render(<Harness onState={(value) => { current = value; }} />);
    fireEvent.click(screen.getByText("generate"));
    await waitFor(() => expect(current?.error).toBe("create string"));
    first.unmount();

    vi.useFakeTimers();
    api.create.mockResolvedValueOnce(sheet("queued"));
    api.get.mockRejectedValueOnce(new Error("poll error"));
    const second = render(<Harness onState={(value) => { current = value; }} />);
    fireEvent.click(screen.getByText("generate"));
    await act(async () => { await Promise.resolve(); });
    await act(async () => { await vi.advanceTimersByTimeAsync(1000); await Promise.resolve(); });
    expect(current?.error).toBe("poll error");
    second.unmount();

    vi.useRealTimers();
    api.create.mockResolvedValueOnce(sheet("completed"));
    api.download.mockRejectedValueOnce("download string");
    render(<Harness onState={(value) => { current = value; }} />);
    fireEvent.click(screen.getByText("generate"));
    await waitFor(() => expect(current?.error).toBe("download string"));
  });

  test("panel enables generation, shows progress, errors and download", () => {
    const base: InterrogazioneState = { open: true, armed: false, point: null, gaia: [], catastoUfficiale: [], territorio: [], arm: vi.fn(), close: vi.fn() };
    const generate = vi.fn();
    const { rerender } = render(<InterrogazionePanel {...base} scheda={{ parcelId: "parcel-1", sheet: null, error: null, downloadUrl: null, generate }} />);
    fireEvent.click(screen.getByRole("button", { name: "Genera scheda territoriale" }));
    expect(generate).toHaveBeenCalled();
    rerender(<InterrogazionePanel {...base} scheda={{ parcelId: "parcel-1", sheet: sheet("queued"), error: null, downloadUrl: null, generate }} />);
    expect(screen.getByRole("button", { name: "Scheda in coda..." })).toBeDisabled();
    rerender(<InterrogazionePanel {...base} scheda={{ parcelId: "parcel-1", sheet: sheet("processing"), error: "failed", downloadUrl: null, generate }} />);
    expect(screen.getByText("Generazione scheda...")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("failed");
    rerender(<InterrogazionePanel {...base} scheda={{ parcelId: "parcel-1", sheet: sheet("completed"), error: null, downloadUrl: "blob:sheet", generate }} />);
    expect(screen.getByRole("link", { name: /Scarica scheda/ })).toHaveAttribute("href", "blob:sheet");
  });
});
