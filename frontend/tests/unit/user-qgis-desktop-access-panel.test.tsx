import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { UserQgisDesktopAccessPanel } from "@/components/app/user-qgis-desktop-access-panel";

const mocks = vi.hoisted(() => ({
  token: vi.fn(),
  status: vi.fn(),
  provision: vi.fn(),
  revoke: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/api", () => ({
  getApplicationUserQgisDesktopAccess: mocks.status,
  provisionApplicationUserQgisDesktopAccess: mocks.provision,
  revokeApplicationUserQgisDesktopAccess: mocks.revoke,
}));

const user = { id: 7, username: "utente.gis", is_active: true, module_gis: true };

describe("UserQgisDesktopAccessPanel", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.clearAllMocks();
    mocks.token.mockReturnValue("token");
    mocks.status.mockResolvedValue({
      enabled: false,
      username: "gaia_qgis_u_7",
      layer_count: 0,
    });
    mocks.provision.mockResolvedValue({
      enabled: true,
      username: "gaia_qgis_u_7",
      password: "one-time-secret",
      layer_count: 3,
    });
    mocks.revoke.mockResolvedValue({
      enabled: false,
      username: "gaia_qgis_u_7",
      layer_count: 0,
    });
  });

  test("provisions a login and shows its password once", async () => {
    render(<UserQgisDesktopAccessPanel user={user} />);
    fireEvent.click(await screen.findByRole("button", { name: "Abilita QGIS Desktop" }));

    expect(await screen.findByText("one-time-secret")).toBeInTheDocument();
    expect(screen.getByText("gaia_qgis_u_7")).toBeInTheDocument();
    expect(screen.getByText("Password mostrata solo ora")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Nascondi credenziali" }));
    expect(screen.queryByText("one-time-secret")).not.toBeInTheDocument();
  });

  test("rotates credentials for enabled users and confirms revocation", async () => {
    mocks.status.mockResolvedValue({
      enabled: true,
      username: "gaia_qgis_u_7",
      layer_count: 2,
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<UserQgisDesktopAccessPanel user={user} />);

    fireEvent.click(await screen.findByRole("button", { name: "Ruota password QGIS" }));
    expect(await screen.findByText("one-time-secret")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Disabilita QGIS Desktop" }));
    await waitFor(() => expect(mocks.revoke).toHaveBeenCalledWith("token", 7));
    expect(screen.queryByText("one-time-secret")).not.toBeInTheDocument();
  });

  test("does not revoke when confirmation is declined", async () => {
    mocks.status.mockResolvedValue({ enabled: true, username: "gaia_qgis_u_7", layer_count: 1 });
    vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<UserQgisDesktopAccessPanel user={user} />);

    fireEvent.click(await screen.findByRole("button", { name: "Disabilita QGIS Desktop" }));
    expect(mocks.revoke).not.toHaveBeenCalled();
  });

  test("does not call provision or revoke without a session", async () => {
    mocks.token.mockReturnValueOnce("token").mockReturnValueOnce(null);
    const { rerender } = render(<UserQgisDesktopAccessPanel user={user} />);
    fireEvent.click(await screen.findByRole("button", { name: "Abilita QGIS Desktop" }));
    expect(await screen.findByText("Sessione GAIA non disponibile.")).toBeInTheDocument();

    mocks.token.mockReturnValueOnce("token").mockReturnValueOnce(null);
    mocks.status.mockResolvedValue({ enabled: true, username: "gaia_qgis_u_7", layer_count: 1 });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    rerender(<UserQgisDesktopAccessPanel user={{ ...user, id: 8 }} />);
    fireEvent.click(await screen.findByRole("button", { name: "Disabilita QGIS Desktop" }));
    expect(await screen.findByText("Sessione GAIA non disponibile.")).toBeInTheDocument();
    expect(mocks.revoke).not.toHaveBeenCalled();
  });

  test("ignores access status results after the selected user changes", async () => {
    let resolveOldStatus: ((value: { enabled: boolean; username: string; layer_count: number }) => void) | undefined;
    mocks.status.mockReturnValueOnce(new Promise((resolve) => {
      resolveOldStatus = resolve;
    }));
    const view = render(<UserQgisDesktopAccessPanel user={user} />);
    view.rerender(<UserQgisDesktopAccessPanel user={{ ...user, id: 8 }} />);
    resolveOldStatus?.({ enabled: true, username: "stale", layer_count: 99 });

    expect(await screen.findByRole("button", { name: "Abilita QGIS Desktop" })).toBeInTheDocument();
    expect(screen.queryByText("stale")).not.toBeInTheDocument();
  });

  test("ignores access status errors after the selected user changes", async () => {
    let rejectOldStatus: ((reason: Error) => void) | undefined;
    mocks.status.mockReturnValueOnce(new Promise((_resolve, reject) => {
      rejectOldStatus = reject;
    }));
    const view = render(<UserQgisDesktopAccessPanel user={user} />);
    view.rerender(<UserQgisDesktopAccessPanel user={{ ...user, id: 8 }} />);
    rejectOldStatus?.(new Error("stale failure"));

    expect(await screen.findByRole("button", { name: "Abilita QGIS Desktop" })).toBeInTheDocument();
    expect(screen.queryByText("stale failure")).not.toBeInTheDocument();
  });

  test("requires the active account and GIS module", async () => {
    render(<UserQgisDesktopAccessPanel user={{ ...user, module_gis: false }} />);

    expect(await screen.findByText(/Attiva e salva prima l'account/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Abilita QGIS Desktop" })).not.toBeInTheDocument();
  });

  test("reports missing sessions and status errors", async () => {
    mocks.token.mockReturnValue(null);
    const { rerender } = render(<UserQgisDesktopAccessPanel user={user} />);
    expect(await screen.findByText("Sessione GAIA non disponibile.")).toBeInTheDocument();

    mocks.token.mockReturnValue("token");
    mocks.status.mockRejectedValueOnce(new Error("status failed"));
    rerender(<UserQgisDesktopAccessPanel user={{ ...user, id: 8 }} />);
    expect(await screen.findByText("status failed")).toBeInTheDocument();
  });

  test("uses a fallback message for non-Error status failures", async () => {
    mocks.status.mockRejectedValueOnce("offline");
    render(<UserQgisDesktopAccessPanel user={user} />);

    expect(
      await screen.findByText("Operazione QGIS Desktop non riuscita."),
    ).toBeInTheDocument();
  });

  test("surfaces provision and revoke failures", async () => {
    mocks.provision.mockRejectedValueOnce("provision failed");
    render(<UserQgisDesktopAccessPanel user={user} />);
    fireEvent.click(await screen.findByRole("button", { name: "Abilita QGIS Desktop" }));
    expect(await screen.findByText("Operazione QGIS Desktop non riuscita.")).toBeInTheDocument();

    mocks.status.mockResolvedValue({ enabled: true, username: "gaia_qgis_u_7", layer_count: 1 });
    mocks.revoke.mockRejectedValueOnce(new Error("revoke failed"));
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const { unmount } = render(<UserQgisDesktopAccessPanel user={{ ...user, id: 9 }} />);
    fireEvent.click(await screen.findByRole("button", { name: "Disabilita QGIS Desktop" }));
    expect(await screen.findByText("revoke failed")).toBeInTheDocument();
    unmount();
  });
});
