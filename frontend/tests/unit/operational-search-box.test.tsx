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

  test("supports the global shortcut and opens the extended results modal", () => {
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
    expect(mocks.push).not.toHaveBeenCalled();
    expect(screen.getByRole("heading", { name: "Risultati per “dashboard”" })).toBeInTheDocument();
  });

  test("navigates to the only menu shortcut and opens results for coordinates without Catasto", () => {
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
    expect(mocks.push).not.toHaveBeenCalled();
    expect(screen.getByRole("heading", { name: "Risultati per “39.9042, 8.5917”" })).toBeInTheDocument();
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
          description: "Avviso per PORCU ALBERTO",
          href: "/ruolo/avvisi/notice-1",
        },
        {
          id: "account-1",
          module: "utenze",
          type: "utenza",
          title: "Utenza PORCU ALBERTO",
          subtitle: "PRCLRT83P20B354J",
          description: "Codice fiscale PRCLRT83P20B354J",
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

    fireEvent.click(screen.getByRole("button", { name: "Vedi tutti i risultati" }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(180);
    });

    expect(mocks.searchOperational).toHaveBeenLastCalledWith("token", "porcu alberto", { limit: 30 });
    expect(screen.getByRole("heading", { name: "Risultati per “porcu alberto”" })).toBeInTheDocument();
    vi.useRealTimers();
  });

  test("uses the same modal controls as the home search", async () => {
    vi.useFakeTimers();
    mocks.searchOperational.mockResolvedValue({
      query: "cliente",
      total: 2,
      modules: ["utenze", "ruolo"],
      items: [
        {
          id: "account-1",
          module: "utenze",
          type: "utenza",
          title: "Cliente Uno",
          subtitle: "Utenze",
          description: "Dettaglio cliente",
          href: "/utenze/account-1",
        },
        {
          id: "notice-1",
          module: "ruolo",
          type: "avviso",
          title: "Avviso Cliente",
          subtitle: "Ruolo",
          description: "Dettaglio avviso",
          href: "/ruolo/avvisi/notice-1",
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
    fireEvent.change(input, { target: { value: "cliente" } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(180);
    });

    fireEvent.click(screen.getByRole("button", { name: "Vedi tutti i risultati" }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(180);
    });

    expect(screen.getByText("Dettaglio cliente")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Vista estesa" }));
    expect(mocks.push).toHaveBeenCalledWith("/search?q=cliente");
    vi.useRealTimers();
  });

  test("keeps coordinate navigation and handles unavailable results", async () => {
    vi.useFakeTimers();
    const { rerender } = render(
      <OperationalSearchBox
        currentUser={{ ...adminUser, module_catasto: true, enabled_modules: ["catasto"] }}
        grantedSectionKeys={[]}
        variant="hero"
        autoFocus
      />,
    );

    const input = screen.getByPlaceholderText("Cerca utenza, ruolo, catasto o coordinate…");
    expect(document.activeElement).toBe(input);
    fireEvent.change(input, { target: { value: "39.9042, 8.5917" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(mocks.push).toHaveBeenCalled();

    mocks.push.mockClear();
    mocks.searchOperational.mockRejectedValueOnce(new Error("Backend non disponibile"));
    rerender(
      <OperationalSearchBox
        currentUser={adminUser}
        grantedSectionKeys={[]}
        variant="compact"
      />,
    );

    const compactInput = screen.getByPlaceholderText("Cerca in GAIA…");
    fireEvent.focus(compactInput);
    fireEvent.change(compactInput, { target: { value: "errore" } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(180);
    });

    expect(screen.getByText("Backend non disponibile")).toBeInTheDocument();
    fireEvent.keyDown(compactInput, { key: "Escape" });
    expect(screen.queryByText("Backend non disponibile")).not.toBeInTheDocument();
    vi.useRealTimers();
  });

  test("handles dropdown and modal result interactions", async () => {
    vi.useFakeTimers();
    mocks.searchOperational.mockResolvedValue({
      query: "cliente",
      total: 2,
      modules: ["utenze", "ruolo"],
      items: [
        { id: "account-1", module: "utenze", type: "utenza", title: "Cliente Uno", subtitle: "Utenze", href: "/utenze/account-1" },
        { id: "notice-1", module: "ruolo", type: "avviso", title: "Avviso Cliente", subtitle: "Ruolo", href: "/ruolo/avvisi/notice-1" },
      ],
    });

    const { unmount } = render(
      <OperationalSearchBox currentUser={adminUser} grantedSectionKeys={[]} variant="compact" />,
    );
    const input = screen.getByPlaceholderText("Cerca in GAIA…");
    fireEvent.keyDown(input, { key: "Enter" });
    fireEvent.mouseDown(document);
    fireEvent.change(input, { target: { value: "Catasto · Dashboard" } });
    expect(screen.getByText("Catasto · Dashboard")).toBeInTheDocument();
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "cliente" } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(180);
    });

    fireEvent.mouseDown(document.body);
    expect(screen.queryByText("Cliente Uno")).not.toBeInTheDocument();
    fireEvent.focus(input);
    fireEvent.click(screen.getByRole("button", { name: /Cliente Uno/ }));
    expect(mocks.push).toHaveBeenCalledWith("/utenze/account-1");
    unmount();

    render(
      <OperationalSearchBox currentUser={adminUser} grantedSectionKeys={[]} variant="compact" />,
    );
    const modalInput = screen.getByPlaceholderText("Cerca in GAIA…");
    fireEvent.change(modalInput, { target: { value: "cliente" } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(180);
    });
    fireEvent.click(screen.getByRole("button", { name: "Vedi tutti i risultati" }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(180);
    });
    fireEvent.click(screen.getByRole("button", { name: /Cliente Uno/ }));
    expect(mocks.push).toHaveBeenCalledWith("/utenze/account-1");

    fireEvent.change(modalInput, { target: { value: "cliente" } });
    fireEvent.keyDown(modalInput, { key: "Enter" });
    fireEvent.click(screen.getByRole("button", { name: "Chiudi risultati ricerca" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    fireEvent.keyDown(modalInput, { key: "Enter" });
    fireEvent.click(screen.getByRole("button", { name: "Chiudi modal ricerca" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    vi.useRealTimers();
  });

  test("navigates through menu shortcuts in the dropdown and modal", async () => {
    vi.useFakeTimers();
    render(
      <OperationalSearchBox currentUser={adminUser} grantedSectionKeys={[]} variant="compact" />,
    );

    const input = screen.getByPlaceholderText("Cerca in GAIA…");
    fireEvent.change(input, { target: { value: "dashboard" } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(180);
    });
    fireEvent.click(screen.getByRole("button", { name: "Utenze · Dashboard" }));
    expect(mocks.push).toHaveBeenCalledWith("/utenze");

    fireEvent.change(input, { target: { value: "dashboard" } });
    fireEvent.keyDown(input, { key: "Enter" });
    fireEvent.click(screen.getByRole("button", { name: "Utenze · Dashboard" }));
    expect(mocks.push).toHaveBeenCalledWith("/utenze");
    vi.useRealTimers();
  });

  test("renders unavailable and unexpected operational results in both surfaces", async () => {
    vi.useFakeTimers();
    mocks.searchOperational.mockRejectedValue("offline");
    const { unmount } = render(
      <OperationalSearchBox currentUser={adminUser} grantedSectionKeys={[]} variant="compact" />,
    );
    const input = screen.getByPlaceholderText("Cerca in GAIA…");
    fireEvent.change(input, { target: { value: "offline" } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(180);
    });
    expect(screen.getByText("Ricerca non disponibile")).toBeInTheDocument();
    expect(screen.getByText("Nessun risultato disponibile per i permessi correnti.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Vedi tutti i risultati" }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(180);
    });
    expect(screen.getByRole("dialog")).toHaveTextContent("Ricerca non disponibile");
    expect(screen.getByRole("dialog")).toHaveTextContent("Nessun risultato disponibile per i permessi correnti.");
    unmount();

    mocks.searchOperational.mockResolvedValue({
      query: "anomalia",
      total: 1,
      modules: [],
      items: [{ id: "unexpected", module: "unknown", type: "unexpected", title: "Risultato inatteso", subtitle: "Dettaglio", href: "/unexpected" }],
    });
    render(
      <OperationalSearchBox currentUser={adminUser} grantedSectionKeys={[]} variant="compact" />,
    );
    const unexpectedInput = screen.getByPlaceholderText("Cerca in GAIA…");
    fireEvent.change(unexpectedInput, { target: { value: "anomalia" } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(180);
    });
    expect(screen.getByText("unknown")).toBeInTheDocument();
    fireEvent.keyDown(unexpectedInput, { key: "Enter" });
    expect(screen.getByRole("dialog")).toHaveTextContent("unknown");
    vi.useRealTimers();
  });
});
