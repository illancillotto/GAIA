import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { GisRuntimeHealthPanel } from "@/app/gis/catalogo/runtime-health-panel";

const mocks = vi.hoisted(() => ({ getGisRuntimeHealth: vi.fn() }));

vi.mock("@/lib/api/gis", () => ({
  getGisRuntimeHealth: (...args: unknown[]) => mocks.getGisRuntimeHealth(...args),
}));

const health = {
  generated_at: "2026-08-25T10:00:00Z",
  status: "warning" as const,
  export_scheduler_enabled: false,
  components: [
    { key: "postgis" as const, label: "PostGIS", status: "ok" as const, message: "Disponibile", latency_ms: 4.2, checked_at: "2026-08-25T10:00:00Z", details: {} },
    { key: "martin" as const, label: "Martin", status: "warning" as const, message: "Lento", latency_ms: null, checked_at: "2026-08-25T10:00:00Z", details: {} },
    { key: "qgis" as const, label: "QGIS", status: "not_configured" as const, message: "Non configurato", checked_at: "2026-08-25T10:00:00Z", details: {} },
    { key: "nas" as const, label: "NAS", status: "critical" as const, message: "Non raggiungibile", checked_at: "2026-08-25T10:00:00Z", details: {} },
  ],
};

describe("GisRuntimeHealthPanel", () => {
  beforeEach(() => mocks.getGisRuntimeHealth.mockReset());

  test("renders honest runtime states and refreshes them", async () => {
    mocks.getGisRuntimeHealth.mockResolvedValue(health);
    render(<GisRuntimeHealthPanel token="token" />);

    expect(await screen.findByText("PostGIS")).toBeInTheDocument();
    expect(screen.getByText("Disponibile", { selector: "span" })).toBeInTheDocument();
    expect(screen.getByText("Da verificare")).toBeInTheDocument();
    expect(screen.getByText("Non configurato", { selector: "span" })).toBeInTheDocument();
    expect(screen.getByText("Non disponibile")).toBeInTheDocument();
    expect(screen.getByText("Risposta in 4.2 ms")).toBeInTheDocument();
    expect(screen.getByText("Scheduler export: disabilitato.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Verifica di nuovo" }));
    await waitFor(() => expect(mocks.getGisRuntimeHealth).toHaveBeenCalledTimes(2));
  });

  test("renders enabled scheduler and both error fallbacks", async () => {
    mocks.getGisRuntimeHealth.mockResolvedValueOnce({ ...health, export_scheduler_enabled: true });
    const success = render(<GisRuntimeHealthPanel token="token" />);
    expect(await screen.findByText("Scheduler export: attivo.")).toBeInTheDocument();
    success.unmount();

    mocks.getGisRuntimeHealth.mockRejectedValueOnce(new Error("health offline"));
    const failed = render(<GisRuntimeHealthPanel token="token" />);
    expect(await screen.findByText("health offline")).toBeInTheDocument();
    failed.unmount();

    mocks.getGisRuntimeHealth.mockRejectedValueOnce("offline");
    render(<GisRuntimeHealthPanel token="token" />);
    expect(await screen.findByText("Controllo servizi GIS non disponibile")).toBeInTheDocument();
  });

  test("ignores late responses after unmount", async () => {
    let resolveHealth: (value: typeof health) => void = () => undefined;
    mocks.getGisRuntimeHealth.mockReturnValue(new Promise((resolve) => { resolveHealth = resolve; }));
    const { unmount } = render(<GisRuntimeHealthPanel token="token" />);
    unmount();
    resolveHealth(health);
    await waitFor(() => expect(mocks.getGisRuntimeHealth).toHaveBeenCalledWith("token"));

    let rejectHealth: (reason: unknown) => void = () => undefined;
    mocks.getGisRuntimeHealth.mockReturnValueOnce(new Promise((_, reject) => { rejectHealth = reject; }));
    const rejected = render(<GisRuntimeHealthPanel token="token" />);
    rejected.unmount();
    rejectHealth(new Error("late"));
    await waitFor(() => expect(mocks.getGisRuntimeHealth).toHaveBeenCalledTimes(2));
  });
});
