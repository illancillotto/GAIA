import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { ProtectedPage } from "@/components/app/protected-page";

const replaceMock = vi.fn();
const routerMock = { replace: replaceMock };
const mockGetCurrentUser = vi.fn();
const mockGetMyPermissions = vi.fn();
const mockGetDashboardSummary = vi.fn();
const mockGetStoredAccessToken = vi.fn();
const mockClearStoredAccessToken = vi.fn();
const mockHasSectionAccess = vi.fn();
const mockIsAuthError = vi.fn();

vi.mock("next/link", () => ({
  default: ({ href, children, className }: { href: string; children: ReactNode; className?: string }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => routerMock,
}));

vi.mock("@/components/layout/app-shell", () => ({
  AppShell: ({ children, onLogout }: { children: ReactNode; onLogout: () => void }) => (
    <div data-testid="app-shell">
      <button type="button" onClick={onLogout}>
        logout
      </button>
      {children}
    </div>
  ),
}));

vi.mock("@/components/layout/topbar", () => ({
  Topbar: ({ pageTitle }: { pageTitle: string }) => <div data-testid="topbar">{pageTitle}</div>,
}));

vi.mock("@/lib/api", () => ({
  getCurrentUser: (...args: unknown[]) => mockGetCurrentUser(...args),
  getDashboardSummary: (...args: unknown[]) => mockGetDashboardSummary(...args),
  getMyPermissions: (...args: unknown[]) => mockGetMyPermissions(...args),
  isAuthError: (...args: unknown[]) => mockIsAuthError(...args),
}));

vi.mock("@/lib/auth", () => ({
  clearStoredAccessToken: () => mockClearStoredAccessToken(),
  getStoredAccessToken: () => mockGetStoredAccessToken(),
}));

vi.mock("@/lib/section-access", () => ({
  hasSectionAccess: (...args: unknown[]) => mockHasSectionAccess(...args),
}));

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });

  return { promise, resolve, reject };
}

function buildUser(overrides: Record<string, unknown> = {}) {
  return {
    id: "user-1",
    username: "mrossi",
    email: "mrossi@example.test",
    full_name: "Mario Rossi",
    role: "admin",
    enabled: true,
    enabled_modules: ["catasto"],
    created_at: "2026-06-22T10:00:00Z",
    updated_at: "2026-06-22T10:00:00Z",
    ...overrides,
  };
}

describe("ProtectedPage", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/catasto");
    replaceMock.mockReset();
    mockGetCurrentUser.mockReset();
    mockGetMyPermissions.mockReset();
    mockGetDashboardSummary.mockReset();
    mockGetStoredAccessToken.mockReset();
    mockClearStoredAccessToken.mockReset();
    mockHasSectionAccess.mockReset();
    mockIsAuthError.mockReset();
    mockHasSectionAccess.mockReturnValue(true);
    mockIsAuthError.mockReturnValue(false);
    mockGetDashboardSummary.mockResolvedValue({
      nas_users: 0,
      nas_groups: 0,
      shares: 0,
      reviews: 0,
      snapshots: 0,
      sync_runs: 0,
    });
  });

  test("shows a loading spinner while the session check is still in progress", () => {
    const deferredUser = createDeferred<ReturnType<typeof buildUser>>();
    const deferredPermissions = createDeferred<{ granted_keys: string[] }>();

    mockGetStoredAccessToken.mockReturnValue("token");
    mockGetCurrentUser.mockReturnValue(deferredUser.promise);
    mockGetMyPermissions.mockReturnValue(deferredPermissions.promise);

    render(
      <ProtectedPage title="GAIA Catasto" description="Dashboard operativa">
        <div>contenuto</div>
      </ProtectedPage>,
    );

    expect(screen.getByText("Verifica sessione")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Sto caricando la sessione e i permessi della pagina.");
    expect(screen.queryByText("Vai al login")).not.toBeInTheDocument();

    deferredUser.resolve(buildUser());
    deferredPermissions.resolve({ granted_keys: [] });
  });

  test("redirects to login and exits the loading state when there is no stored token", async () => {
    mockGetStoredAccessToken.mockReturnValue(null);

    render(
      <ProtectedPage title="GAIA Catasto" description="Dashboard operativa">
        <div>contenuto</div>
      </ProtectedPage>,
    );

    await act(async () => {});

    expect(screen.getByText("Accesso richiesto")).toBeInTheDocument();
    expect(screen.getByText("Accesso richiesto. Effettua il login.")).toBeInTheDocument();
    expect(screen.queryByText("Verifica sessione")).not.toBeInTheDocument();
    expect(screen.getByText("Vai al login")).toHaveAttribute("href", "/login");
    expect(replaceMock).toHaveBeenCalledWith("/login");
  });

  test("renders the shell and page content after a successful session load", async () => {
    mockGetStoredAccessToken.mockReturnValue("token");
    mockGetCurrentUser.mockResolvedValue(buildUser());
    mockGetMyPermissions.mockResolvedValue({ granted_keys: ["catasto.dashboard"] });

    render(
      <ProtectedPage title="GAIA Catasto" description="Dashboard operativa" requiredSection="catasto.dashboard">
        <div>contenuto</div>
      </ProtectedPage>,
    );

    expect(await screen.findByTestId("app-shell")).toBeInTheDocument();
    expect(screen.getByTestId("topbar")).toHaveTextContent("GAIA Catasto");
    expect(screen.getByText("contenuto")).toBeInTheDocument();
    expect(mockGetDashboardSummary).toHaveBeenCalledWith("token");
    expect(mockHasSectionAccess).toHaveBeenCalledWith(["catasto.dashboard"], "catasto.dashboard");
  });

  test("keeps rendering when the optional dashboard summary request fails", async () => {
    mockGetStoredAccessToken.mockReturnValue("token");
    mockGetCurrentUser.mockResolvedValue(buildUser());
    mockGetMyPermissions.mockResolvedValue({ granted_keys: [] });
    mockGetDashboardSummary.mockRejectedValue(new Error("summary failed"));

    render(
      <ProtectedPage title="GAIA Catasto" description="Dashboard operativa">
        <div>contenuto</div>
      </ProtectedPage>,
    );

    expect(await screen.findByText("contenuto")).toBeInTheDocument();
  });

  test("shows the login card after an authentication error clears the session", async () => {
    const error = new Error("401");

    mockGetStoredAccessToken.mockReturnValue("token");
    mockGetCurrentUser.mockRejectedValue(error);
    mockGetMyPermissions.mockRejectedValue(error);
    mockIsAuthError.mockReturnValue(true);

    render(
      <ProtectedPage title="GAIA Catasto" description="Dashboard operativa">
        <div>contenuto</div>
      </ProtectedPage>,
    );

    expect(await screen.findByText("Accesso richiesto")).toBeInTheDocument();
    expect(screen.getByText("401")).toBeInTheDocument();
    expect(screen.getByText("Vai al login")).toHaveAttribute("href", "/login");
    expect(mockClearStoredAccessToken).toHaveBeenCalled();
    expect(replaceMock).toHaveBeenCalledWith("/login");
  });

  test("shows a generic unexpected error when the auth rejection is not an Error instance", async () => {
    mockGetStoredAccessToken.mockReturnValue("token");
    mockGetCurrentUser.mockRejectedValue("fatal");
    mockGetMyPermissions.mockRejectedValue("fatal");
    mockIsAuthError.mockReturnValue(true);

    render(
      <ProtectedPage title="GAIA Catasto" description="Dashboard operativa">
        <div>contenuto</div>
      </ProtectedPage>,
    );

    expect(await screen.findByText("Errore imprevisto")).toBeInTheDocument();
  });

  test("shows the unauthorized state inside the shell when module access is missing", async () => {
    mockGetStoredAccessToken.mockReturnValue("token");
    mockGetCurrentUser.mockResolvedValue(buildUser({ role: "user", enabled_modules: [] }));
    mockGetMyPermissions.mockResolvedValue({ granted_keys: [] });

    render(
      <ProtectedPage title="GAIA Catasto" description="Dashboard operativa" requiredModule="catasto">
        <div>contenuto</div>
      </ProtectedPage>,
    );

    expect(await screen.findByTestId("app-shell")).toBeInTheDocument();
    expect(screen.getByText("Accesso non autorizzato")).toBeInTheDocument();
    expect(
      screen.getByText("Questa sezione e disponibile solo per gli utenti abilitati al modulo richiesto."),
    ).toBeInTheDocument();
  });

  test("allows GIS-enabled users to open GIS module pages", async () => {
    mockGetStoredAccessToken.mockReturnValue("token");
    mockGetCurrentUser.mockResolvedValue(buildUser({ role: "user", enabled_modules: ["gis"] }));
    mockGetMyPermissions.mockResolvedValue({ granted_keys: [] });

    render(
      <ProtectedPage title="GIS Platform" description="Catalogo layer" requiredModule="gis">
        <div>catalogo gis</div>
      </ProtectedPage>,
    );

    expect(await screen.findByText("catalogo gis")).toBeInTheDocument();
    expect(screen.queryByText("Accesso non autorizzato")).not.toBeInTheDocument();
  });

  test("shows the login card with a backend availability message when session load fails without auth error", async () => {
    mockGetStoredAccessToken.mockReturnValue("token");
    mockGetCurrentUser.mockRejectedValue(new Error("timeout"));
    mockGetMyPermissions.mockRejectedValue(new Error("timeout"));

    render(
      <ProtectedPage title="GAIA Catasto" description="Dashboard operativa">
        <div>contenuto</div>
      </ProtectedPage>,
    );

    expect(await screen.findByText("Accesso richiesto")).toBeInTheDocument();
    expect(screen.getByText("timeout")).toBeInTheDocument();
    expect(mockClearStoredAccessToken).not.toHaveBeenCalled();
  });

  test("renders the embedded unauthorized state when a required role is missing", async () => {
    window.history.replaceState({}, "", "/catasto?embedded=1");
    mockGetStoredAccessToken.mockReturnValue("token");
    mockGetCurrentUser.mockResolvedValue(buildUser({ role: "user" }));
    mockGetMyPermissions.mockResolvedValue({ granted_keys: [] });

    render(
      <ProtectedPage title="GAIA Catasto" description="Dashboard operativa" requiredRoles={["admin"]}>
        <div>contenuto</div>
      </ProtectedPage>,
    );

    expect(await screen.findByText("Accesso non autorizzato")).toBeInTheDocument();
    expect(screen.queryByTestId("app-shell")).not.toBeInTheDocument();
    expect(screen.getByText("Questa sezione e disponibile solo per i ruoli autorizzati.")).toBeInTheDocument();
  });

  test("renders the embedded unauthorized module copy when module access is missing", async () => {
    window.history.replaceState({}, "", "/catasto?embedded=1");
    mockGetStoredAccessToken.mockReturnValue("token");
    mockGetCurrentUser.mockResolvedValue(buildUser({ role: "user", enabled_modules: [] }));
    mockGetMyPermissions.mockResolvedValue({ granted_keys: [] });

    render(
      <ProtectedPage title="GAIA Catasto" description="Dashboard operativa" requiredModule="catasto">
        <div>contenuto</div>
      </ProtectedPage>,
    );

    expect(await screen.findByText("Accesso non autorizzato")).toBeInTheDocument();
    expect(
      screen.getByText("Questa sezione e disponibile solo per gli utenti abilitati al modulo richiesto."),
    ).toBeInTheDocument();
  });

  test("renders the embedded unauthorized fallback copy for section-based denial", async () => {
    window.history.replaceState({}, "", "/catasto?embedded=1");
    mockGetStoredAccessToken.mockReturnValue("token");
    mockGetCurrentUser.mockResolvedValue(buildUser());
    mockGetMyPermissions.mockResolvedValue({ granted_keys: [] });
    mockHasSectionAccess.mockReturnValue(false);

    render(
      <ProtectedPage title="GAIA Catasto" description="Dashboard operativa" requiredSection="catasto.restricted">
        <div>contenuto</div>
      </ProtectedPage>,
    );

    expect(await screen.findByText("Accesso non autorizzato")).toBeInTheDocument();
    expect(
      screen.getByText("Questa sezione e disponibile solo per admin, super admin o utenti esplicitamente abilitati."),
    ).toBeInTheDocument();
  });

  test("renders embedded content and supports hiding the content header", async () => {
    window.history.replaceState({}, "", "/catasto?embedded=1");
    mockGetStoredAccessToken.mockReturnValue("token");
    mockGetCurrentUser.mockResolvedValue(buildUser());
    mockGetMyPermissions.mockResolvedValue({ granted_keys: [] });

    render(
      <ProtectedPage title="GAIA Catasto" description="Dashboard operativa" hideContentHeader>
        <div>contenuto embedded</div>
      </ProtectedPage>,
    );

    expect(await screen.findByText("contenuto embedded")).toBeInTheDocument();
    expect(screen.queryByTestId("app-shell")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "GAIA Catasto" })).not.toBeInTheDocument();
  });

  test("renders embedded content without the shell when hideContentHeader is false", async () => {
    window.history.replaceState({}, "", "/catasto?embedded=1");
    mockGetStoredAccessToken.mockReturnValue("token");
    mockGetCurrentUser.mockResolvedValue(buildUser());
    mockGetMyPermissions.mockResolvedValue({ granted_keys: [] });

    render(
      <ProtectedPage title="GAIA Catasto" description="Dashboard operativa">
        <div>contenuto embedded</div>
      </ProtectedPage>,
    );

    expect(await screen.findByText("contenuto embedded")).toBeInTheDocument();
    expect(screen.queryByTestId("app-shell")).not.toBeInTheDocument();
  });

  test("renders the shell without the content header when hideContentHeader is true", async () => {
    mockGetStoredAccessToken.mockReturnValue("token");
    mockGetCurrentUser.mockResolvedValue(buildUser());
    mockGetMyPermissions.mockResolvedValue({ granted_keys: [] });

    render(
      <ProtectedPage title="GAIA Catasto" description="Dashboard operativa" hideContentHeader>
        <div>contenuto</div>
      </ProtectedPage>,
    );

    expect(await screen.findByTestId("app-shell")).toBeInTheDocument();
    expect(screen.queryAllByRole("heading", { name: "GAIA Catasto" })).toHaveLength(0);
  });

  test("renders the shell unauthorized copy for role and section restrictions", async () => {
    mockGetStoredAccessToken.mockReturnValue("token");
    mockGetCurrentUser.mockResolvedValue(buildUser({ role: "user" }));
    mockGetMyPermissions.mockResolvedValue({ granted_keys: [] });

    const { rerender } = render(
      <ProtectedPage title="GAIA Catasto" description="Dashboard operativa" requiredRoles={["admin"]}>
        <div>contenuto</div>
      </ProtectedPage>,
    );

    expect(await screen.findByText("Questa sezione e disponibile solo per i ruoli autorizzati.")).toBeInTheDocument();

    mockGetCurrentUser.mockResolvedValue(buildUser());
    mockHasSectionAccess.mockReturnValue(false);

    rerender(
      <ProtectedPage title="GAIA Catasto" description="Dashboard operativa" requiredSection="catasto.restricted">
        <div>contenuto</div>
      </ProtectedPage>,
    );

    expect(
      await screen.findByText("Questa sezione e disponibile solo per admin, super admin o utenti esplicitamente abilitati."),
    ).toBeInTheDocument();
  });

  test("allows logging out from the shell", async () => {
    mockGetStoredAccessToken.mockReturnValue("token");
    mockGetCurrentUser.mockResolvedValue(buildUser());
    mockGetMyPermissions.mockResolvedValue({ granted_keys: [] });

    render(
      <ProtectedPage title="GAIA Catasto" description="Dashboard operativa">
        <div>contenuto</div>
      </ProtectedPage>,
    );

    expect(await screen.findByTestId("app-shell")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "logout" }));

    expect(replaceMock).toHaveBeenCalledWith("/login");
    expect(screen.queryByText("contenuto")).not.toBeInTheDocument();
  });
});
