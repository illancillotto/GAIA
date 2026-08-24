import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { OperationalSearchBox } from "@/components/search/operational-search-box";
import type { CurrentUser } from "@/types/api";

const mocks = vi.hoisted(() => ({
  push: vi.fn(),
  getStoredAccessToken: vi.fn(),
  searchOperational: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mocks.push }),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/operational-search-api", () => ({
  searchOperational: mocks.searchOperational,
}));

const adminUser: CurrentUser = {
  id: 1,
  username: "admin",
  email: "admin@example.local",
  role: "admin",
  is_active: true,
  module_accessi: false,
  module_rete: false,
  module_inventario: false,
  module_gis: false,
  module_catasto: false,
  module_utenze: false,
  module_operazioni: false,
  module_riordino: false,
  module_ruolo: false,
  module_presenze: false,
  enabled_modules: [],
};

describe("OperationalSearchBox compact mode", () => {
  beforeEach(() => {
    mocks.push.mockReset();
    mocks.getStoredAccessToken.mockReset();
    mocks.searchOperational.mockReset();
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.searchOperational.mockResolvedValue({ query: "", items: [], total: 0, modules: [] });
  });

  test("supports the global shortcut and compact search-page navigation", () => {
    render(
      <OperationalSearchBox
        currentUser={adminUser}
        grantedSectionKeys={[]}
        variant="compact"
        enableHotkey
      />,
    );

    const input = screen.getByPlaceholderText("Cerca in GAIA…");
    expect(screen.getByText("Ctrl K")).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "k" });
    fireEvent.keyDown(document, { key: "x", ctrlKey: true });
    fireEvent.keyDown(document, { key: "k", metaKey: true });
    expect(document.activeElement).toBe(input);
    fireEvent.keyDown(document, { key: "k", ctrlKey: true });

    fireEvent.change(input, { target: { value: "dashboard" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(mocks.push).toHaveBeenCalledWith("/search?q=dashboard");
  });

  test("navigates to the only menu shortcut and denies coordinate shortcuts without Catasto", () => {
    render(
      <OperationalSearchBox
        currentUser={{ ...adminUser, role: "viewer" }}
        grantedSectionKeys={[]}
        variant="compact"
      />,
    );

    const input = screen.getByPlaceholderText("Cerca in GAIA…");
    fireEvent.change(input, { target: { value: "La mia attività · Panoramica" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(mocks.push).toHaveBeenCalledWith("/me");

    mocks.push.mockClear();
    fireEvent.change(input, { target: { value: "39.9042, 8.5917" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(mocks.push).toHaveBeenCalledWith("/search?q=39.9042%2C%208.5917");
  });

  test("shows Utenze before payment notices regardless of API result order", async () => {
    vi.useFakeTimers();
    mocks.searchOperational.mockResolvedValue({
      query: "porcu alberto",
      total: 2,
      modules: ["ruolo", "utenze"],
      items: [
        {
          id: "notice-1",
          module: "ruolo",
          type: "avviso",
          title: "Avviso 01.2025",
          subtitle: "Ruolo · 2025",
          href: "/ruolo/avvisi/notice-1",
        },
        {
          id: "account-1",
          module: "utenze",
          type: "utenza",
          title: "Utenza PORCU ALBERTO",
          subtitle: "PRCLRT83P20B354J",
          href: "/utenze/account-1",
        },
      ],
    });

    render(
      <OperationalSearchBox
        currentUser={adminUser}
        grantedSectionKeys={[]}
        variant="compact"
      />,
    );

    const input = screen.getByPlaceholderText("Cerca in GAIA…");
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "porcu alberto" } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(180);
    });

    const utenzeHeading = screen.getByText("Utenze");
    const ruoloHeading = screen.getByText("Ruolo");
    expect(utenzeHeading.compareDocumentPosition(ruoloHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    vi.useRealTimers();
  });
});
