import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { usePathname } from "next/navigation";
import { HomeSyncAlerts } from "@/components/elaborazioni/home-sync-alerts";
import { ApiError, request } from "@/lib/api/core";
import { useSessionBootstrap } from "@/lib/use-session-bootstrap";

vi.mock("next/navigation", () => ({ usePathname: vi.fn() }));
vi.mock("@/lib/use-session-bootstrap", () => ({ useSessionBootstrap: vi.fn() }));
vi.mock("@/lib/api/core", async () => ({
  ...await vi.importActual<typeof import("@/lib/api/core")>("@/lib/api/core"), request: vi.fn(),
}));

const inaz = { id: "presenze:credential:1:1", service: "Presenze INAZ", message: "Credenziale disabilitata." };
const sister = { id: "autosync:job:123:failed", service: "SISTER autosync", message: "Esecuzione interrotta." };
type Session = ReturnType<typeof useSessionBootstrap>;

function session(overrides: Partial<Session> = {}) {
  vi.mocked(useSessionBootstrap).mockReturnValue({
    token: "admin-token", status: "ready", error: null, grantedSectionKeys: [], logout: vi.fn(),
    currentUser: { role: "admin" } as NonNullable<Session["currentUser"]>, ...overrides,
  });
}

async function flush() { await act(async () => {}); }
async function poll() { await act(async () => { await vi.advanceTimersByTimeAsync(30000); }); }
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.useFakeTimers();
  vi.mocked(usePathname).mockReturnValue("/");
  session();
  vi.mocked(request).mockResolvedValue([]);
});
afterEach(() => { vi.useRealTimers(); });

describe("notifiche home riservate agli amministratori", () => {
  it.each(["/login", "/elaborazioni", "/presenze"])("non controlla sessione o servizi fuori dalla home: %s", (path) => {
    vi.mocked(usePathname).mockReturnValue(path);
    render(<HomeSyncAlerts />);
    expect(useSessionBootstrap).not.toHaveBeenCalled();
    expect(request).not.toHaveBeenCalled();
  });

  it.each(["operator", "viewer", "user"])("non legge né mostra allarmi al ruolo %s", async (role) => {
    session({ currentUser: { role } as NonNullable<Session["currentUser"]> });
    render(<HomeSyncAlerts />);
    await flush();
    await poll();
    expect(request).not.toHaveBeenCalled();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it.each([
    { status: "checking" as const }, { status: "anonymous" as const }, { status: "error" as const },
    { token: null }, { currentUser: null },
  ])("attende una sessione admin completa: %j", async (state) => {
    session(state);
    render(<HomeSyncAlerts />);
    await flush();
    expect(request).not.toHaveBeenCalled();
  });

  it.each(["admin", "super_admin"])("mostra più servizi al ruolo %s, con autenticazione e timeout", async (role) => {
    session({ currentUser: { role } as NonNullable<Session["currentUser"]> });
    vi.mocked(request).mockResolvedValue([inaz, sister]);
    render(<HomeSyncAlerts />);
    await flush();
    expect(screen.getByRole("alert", { name: "Avvisi sincronizzazioni" })).toBeInTheDocument();
    expect(screen.getByText("Presenze INAZ")).toBeInTheDocument();
    expect(screen.getByText("SISTER autosync")).toBeInTheDocument();
    expect(request).toHaveBeenCalledWith("/elaborazioni/sync-alerts", {
      headers: { Authorization: "Bearer admin-token" }, timeoutMs: 15000,
    });
  });

  it("resta silenzioso senza problemi e rileva un'interruzione al controllo successivo", async () => {
    render(<HomeSyncAlerts />);
    await flush();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    vi.mocked(request).mockResolvedValue([sister]);
    await poll();
    expect(screen.getByText("SISTER autosync")).toBeInTheDocument();
  });

  it("chiude lo stesso incidente senza ripeterlo; avvisa per nuovi problemi e dopo un recupero", async () => {
    vi.mocked(request).mockResolvedValue([inaz]);
    render(<HomeSyncAlerts />);
    await flush();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi avvisi sincronizzazioni" }));
    await poll();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    vi.mocked(request).mockResolvedValue([inaz, sister]);
    await poll();
    expect(screen.getByText("SISTER autosync")).toBeInTheDocument();
    expect(screen.queryByText("Presenze INAZ")).not.toBeInTheDocument();
    vi.mocked(request).mockResolvedValue([]);
    await poll();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    vi.mocked(request).mockResolvedValue([inaz]);
    await poll();
    expect(screen.getByText("Presenze INAZ")).toBeInTheDocument();
  });

  it("se il monitor è irraggiungibile conserva i problemi noti e distingue l'errore di lettura", async () => {
    vi.mocked(request).mockResolvedValue([inaz]);
    render(<HomeSyncAlerts />);
    await flush();
    vi.mocked(request).mockRejectedValue(new ApiError("backend down", null, 503));
    await poll();
    await poll();
    expect(screen.getByText("Presenze INAZ")).toBeInTheDocument();
    expect(screen.getAllByText("Monitor sincronizzazioni")).toHaveLength(1);
    vi.mocked(request).mockResolvedValue([]);
    await poll();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it.each([401, 403])("rimuove gli allarmi se la sessione perde accesso (%s)", async (status) => {
    vi.mocked(request).mockResolvedValue([inaz]);
    render(<HomeSyncAlerts />);
    await flush();
    vi.mocked(request).mockRejectedValue(new ApiError("denied", null, status));
    await poll();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("segnala anche errori di rete senza un codice HTTP", async () => {
    vi.mocked(request).mockRejectedValue(new TypeError("Network error"));
    render(<HomeSyncAlerts />);
    await flush();
    expect(screen.getByText("Monitor sincronizzazioni")).toBeInTheDocument();
  });

  it("non sovrappone richieste lente e ignora la risposta dopo l'uscita dalla home", async () => {
    const pending = deferred<typeof inaz[]>();
    vi.mocked(request).mockReturnValue(pending.promise);
    const view = render(<HomeSyncAlerts />);
    await poll();
    expect(request).toHaveBeenCalledTimes(1);
    view.unmount();
    await act(async () => { pending.resolve([inaz]); });
    await poll();
    expect(request).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("ignora anche errori arrivati dopo l'uscita dalla home", async () => {
    const pending = deferred<never>();
    vi.mocked(request).mockReturnValue(pending.promise);
    const view = render(<HomeSyncAlerts />);
    view.unmount();
    await act(async () => { pending.reject(new Error("late failure")); });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("isola il monitor quando cambia il token e lo smonta al cambio di ruolo", async () => {
    const pending = deferred<typeof inaz[]>();
    vi.mocked(request).mockReturnValueOnce(pending.promise).mockResolvedValue([sister]);
    const view = render(<HomeSyncAlerts />);
    session({ token: "other-admin" });
    view.rerender(<HomeSyncAlerts />);
    await flush();
    await act(async () => { pending.resolve([inaz]); });
    expect(screen.getByText("SISTER autosync")).toBeInTheDocument();
    expect(screen.queryByText("Presenze INAZ")).not.toBeInTheDocument();
    session({ currentUser: { role: "operator" } as NonNullable<Session["currentUser"]> });
    view.rerender(<HomeSyncAlerts />);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
