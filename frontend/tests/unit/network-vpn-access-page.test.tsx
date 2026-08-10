import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import NetworkVpnAccessPage from "@/app/network/vpn-access/page";

const mocks = vi.hoisted(() => ({
  listDevices: vi.fn(),
  listSessions: vi.fn(),
  updateStatus: vi.fn(),
}));

vi.mock("@/components/network/network-module-page", () => ({
  NetworkModulePage: ({ children, title }: { children: (context: { token: string; currentUser: unknown }) => ReactNode; title: string }) => (
    <main>
      <h1>{title}</h1>
      {children({
        token: "token",
        currentUser: {
          id: 1,
          username: "admin",
          email: "admin@example.local",
          role: "admin",
          is_active: true,
          enabled_modules: ["rete"],
        },
      })}
    </main>
  ),
}));

vi.mock("@/lib/api", () => ({
  listNetworkVpnAccessDevices: (...args: unknown[]) => mocks.listDevices(...args),
  listNetworkVpnAccessSessions: (...args: unknown[]) => mocks.listSessions(...args),
  updateNetworkVpnAccessDeviceStatus: (...args: unknown[]) => mocks.updateStatus(...args),
}));

describe("NetworkVpnAccessPage", () => {
  beforeEach(() => {
    mocks.listDevices.mockReset();
    mocks.listSessions.mockReset();
    mocks.updateStatus.mockReset();
    mocks.listDevices.mockResolvedValue({
      items: [
        {
          id: 7,
          user_id: 3,
          device_fingerprint: "fingerprint-abcdef",
          client_device_id: "browser-123456",
          display_name: "Windows · it-IT",
          status: "active",
          user_agent_hash: "hash",
          user_agent_sample: "Mozilla/5.0",
          first_client_ip: "10.250.10.20",
          last_client_ip: "10.250.10.21",
          first_seen_at: "2026-08-10T08:00:00Z",
          last_seen_at: "2026-08-10T09:00:00Z",
          created_at: "2026-08-10T08:00:00Z",
          updated_at: "2026-08-10T09:00:00Z",
        },
      ],
      total: 1,
      skip: 0,
      limit: 100,
    });
    mocks.listSessions.mockResolvedValue({
      items: [
        {
          id: 9,
          user_id: 3,
          device_id: 7,
          source: "gaia_login",
          event_type: "login_blocked",
          username: "admin",
          client_ip: "10.250.10.22",
          vpn_ip: null,
          public_ip: null,
          device_fingerprint: "fingerprint-new",
          user_agent_hash: "hash",
          user_agent_sample: "Mozilla/5.0",
          blocked_reason: "max_active_devices:4",
          observed_at: "2026-08-10T10:00:00Z",
          created_at: "2026-08-10T10:00:00Z",
        },
      ],
      total: 1,
      skip: 0,
      limit: 100,
    });
    mocks.updateStatus.mockResolvedValue({ id: 7, status: "revoked" });
  });

  test("renders VPN devices, blocked sessions and can revoke a device", async () => {
    render(<NetworkVpnAccessPage />);

    expect(await screen.findByText("Windows · it-IT")).toBeInTheDocument();
    expect(screen.getByText("Login bloccato")).toBeInTheDocument();
    expect(screen.getByText("Motivo blocco: max_active_devices:4")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Revoca" }));

    await waitFor(() => {
      expect(mocks.updateStatus).toHaveBeenCalledWith("token", 7, "revoked");
    });
    expect(await screen.findByText("Dispositivo #7 aggiornato a revocato.")).toBeInTheDocument();
  });
});
