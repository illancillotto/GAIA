import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
          action_label: "Consultazione dashboard operativa",
          path: "/operazioni",
          visible: true,
          last_seen_at: "2026-06-29T10:00:00Z",
          minutes_since_last_seen: 1,
          last_login_at: "2026-06-29T09:00:00Z",
          recent_routes: [
            {
              path: "/operazioni",
              route_label: "Operazioni",
              module_key: "operazioni",
              seen_at: "2026-06-29T10:00:00Z",
            },
            {
              path: "/operazioni/attivita",
              route_label: "Operazioni / Attività",
              module_key: "operazioni",
              seen_at: "2026-06-29T09:58:00Z",
            },
          ],
          recent_actions: [
            {
              action_label: "Consultazione dashboard operativa",
              occurred_at: "2026-06-29T10:00:00Z",
            },
            {
              action_label: "Apertura lista attivita",
              occurred_at: "2026-06-29T09:59:00Z",
            },
          ],
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
    expect(screen.getByText("Operazioni / Attività")).toBeInTheDocument();
    expect(screen.getByText("Consultazione dashboard operativa")).toBeInTheDocument();
    expect(screen.getByText("Percorso più frequente")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Apri pagina" })).toHaveAttribute("href", "/operazioni");
    expect(screen.getByRole("link", { name: "Vedi attività operatore" })).toHaveAttribute(
      "href",
      "/operazioni/attivita?operator_user_id=7",
    );
  });

  test("filters users by search term, module and route", async () => {
    mocks.getPresenceSummary.mockResolvedValue({
      window_minutes: 15,
      active_users: 2,
      visible_users: 1,
      by_module: [
        { module_key: "operazioni", count: 1 },
        { module_key: "wiki", count: 1 },
      ],
      items: [
        {
          user_id: 7,
          username: "mrossi",
          full_name: "Mario Rossi",
          role: "admin",
          module_key: "operazioni",
          route_label: "Operazioni",
          action_label: null,
          path: "/operazioni",
          visible: true,
          last_seen_at: "2026-06-29T10:00:00Z",
          minutes_since_last_seen: 1,
          last_login_at: "2026-06-29T09:00:00Z",
          recent_routes: [],
          recent_actions: [],
        },
        {
          user_id: 8,
          username: "lbianchi",
          full_name: "Luca Bianchi",
          role: "viewer",
          module_key: "wiki",
          route_label: "Wiki",
          action_label: "Consultazione pagina wiki",
          path: "/wiki",
          visible: false,
          last_seen_at: "2026-06-29T10:02:00Z",
          minutes_since_last_seen: 3,
          last_login_at: "2026-06-29T09:30:00Z",
          recent_routes: [],
          recent_actions: [
            {
              action_label: "Consultazione pagina wiki",
              occurred_at: "2026-06-29T10:02:00Z",
            },
          ],
        },
      ],
    });

    render(<GaiaUsersActivityPage />);

    await waitFor(() => {
      expect(screen.getByText("Mario Rossi")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText("Utente, ruolo, modulo o path"), {
      target: { value: "luca" },
    });

    expect(screen.queryByText("Mario Rossi")).not.toBeInTheDocument();
    expect(screen.getByText("Luca Bianchi")).toBeInTheDocument();

    fireEvent.change(screen.getByDisplayValue("Tutti i moduli"), {
      target: { value: "operazioni" },
    });

    expect(screen.getByText("Nessun utente corrisponde ai filtri correnti.")).toBeInTheDocument();

    fireEvent.change(screen.getByDisplayValue("operazioni (1)"), {
      target: { value: "all" },
    });
    fireEvent.change(screen.getByDisplayValue("Tutti i percorsi"), {
      target: { value: "Wiki" },
    });

    expect(screen.getByText("Luca Bianchi")).toBeInTheDocument();
    expect(screen.queryByText("Mario Rossi")).not.toBeInTheDocument();
  });

  test("renders api error when summary load fails", async () => {
    mocks.getPresenceSummary.mockRejectedValue(new Error("backend KO"));

    render(<GaiaUsersActivityPage />);

    await waitFor(() => {
      expect(screen.getByText("backend KO")).toBeInTheDocument();
    });
  });
});
