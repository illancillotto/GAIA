import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import GaiaUsersActivityPage from "@/app/gaia/users/attivita/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  getPresenceSummary: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    getPresenceSummary: mocks.getPresenceSummary,
  };
});

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children, title }: { children: ReactNode; title: string }) => (
    <div>
      <h1>{title}</h1>
      {children}
    </div>
  ),
}));

describe("Gaia user activity page", () => {
  beforeEach(() => {
    mocks.getStoredAccessToken.mockReset();
    mocks.getPresenceSummary.mockReset();
    mocks.getStoredAccessToken.mockReturnValue("token");
  });

  test("renders recent user presence summary", async () => {
    mocks.getPresenceSummary.mockResolvedValue({
      window_minutes: 15,
      active_users: 2,
      visible_users: 1,
      by_module: [{ module_key: "operazioni", count: 2 }],
      items: [
        {
          user_id: 7,
          username: "mrossi",
          full_name: "Mario Rossi",
          role: "admin",
          module_key: "operazioni",
          route_label: "Operazioni",
          path: "/operazioni",
          visible: true,
          last_seen_at: "2026-06-29T10:00:00Z",
          minutes_since_last_seen: 1,
          last_login_at: "2026-06-29T09:00:00Z",
        },
      ],
    });

    render(<GaiaUsersActivityPage />);

    await waitFor(() => {
      expect(screen.getByText("Mario Rossi")).toBeInTheDocument();
    });

    expect(screen.getByText("Attività utenti GAIA")).toBeInTheDocument();
    expect(screen.getByText("operazioni: 2")).toBeInTheDocument();
    expect(screen.getByText("1 min fa")).toBeInTheDocument();
  });

  test("renders api error when summary load fails", async () => {
    mocks.getPresenceSummary.mockRejectedValue(new Error("backend KO"));

    render(<GaiaUsersActivityPage />);

    await waitFor(() => {
      expect(screen.getByText("backend KO")).toBeInTheDocument();
    });
  });
});
