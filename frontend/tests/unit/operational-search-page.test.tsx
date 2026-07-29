import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import OperationalSearchPage from "@/app/search/page";

const mocks = vi.hoisted(() => ({
  push: vi.fn(),
  query: "",
  getStoredAccessToken: vi.fn(),
  searchOperational: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mocks.push }),
  useSearchParams: () => new URLSearchParams(mocks.query),
}));

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children, title }: { children: ReactNode; title: string }) => (
    <main>
      <h1>{title}</h1>
      {children}
    </main>
  ),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/operational-search-api", () => ({
  searchOperational: mocks.searchOperational,
}));

describe("OperationalSearchPage", () => {
  beforeEach(() => {
    mocks.push.mockReset();
    mocks.getStoredAccessToken.mockReset();
    mocks.searchOperational.mockReset();
    mocks.query = "";
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.searchOperational.mockResolvedValue({ query: "", total: 0, modules: [], items: [] });
  });

  test("prompts for a valid query and handles empty submit", () => {
    const { rerender } = render(<OperationalSearchPage />);

    expect(screen.getByText("Ricerca GAIA")).toBeInTheDocument();
    expect(screen.getByText("Inserisci almeno 2 caratteri")).toBeInTheDocument();
    expect(screen.getByText("Usa la barra in alto per cercare soggetti, avvisi, fogli e particelle.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Cerca" }));

    expect(mocks.push).toHaveBeenCalledWith("/search");
    expect(mocks.searchOperational).not.toHaveBeenCalled();

    mocks.query = "q=a";
    rerender(<OperationalSearchPage />);
    expect(screen.getByLabelText("Query ricerca operativa")).toHaveValue("a");
  });

  test("shows grouped results and filters by module", async () => {
    mocks.query = "q=rossi";
    mocks.searchOperational.mockResolvedValue({
      query: "rossi",
      total: 3,
      modules: ["utenze", "ruolo", "catasto"],
      items: [
        {
          id: "subject-1",
          module: "utenze",
          type: "subject_person",
          title: "Rossi Mario",
          subtitle: "Utenze · Persona",
          description: "RSSMRA80A01H501U",
          href: "/utenze/subject-1",
          score: 91,
          metadata: {},
        },
        {
          id: "avviso-1",
          module: "ruolo",
          type: "avviso",
          title: "Avviso 123",
          subtitle: "Ruolo · 2026",
          description: null,
          href: "/ruolo/avvisi/avviso-1",
          score: 80,
          metadata: {},
        },
        {
          id: "particella-1",
          module: "catasto",
          type: "particella",
          title: "Oristano · F. 1 · P. 2",
          subtitle: "Catasto · Particella",
          description: "Distretto 1",
          href: "/catasto/particelle/particella-1",
          score: 70,
          metadata: {},
        },
      ],
    });

    render(<OperationalSearchPage />);

    expect(screen.getByText("Ricerca in corso…")).toBeInTheDocument();
    await waitFor(() => expect(mocks.searchOperational).toHaveBeenCalledWith("token", "rossi", { limit: 30 }));
    expect(await screen.findByText("Rossi Mario")).toBeInTheDocument();
    expect(screen.getByText("Avviso 123")).toBeInTheDocument();
    expect(screen.getByText("Oristano · F. 1 · P. 2")).toBeInTheDocument();
    expect(screen.getByText("3 risultati visibili")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Ruolo 1" }));

    expect(screen.queryByText("Rossi Mario")).not.toBeInTheDocument();
    expect(screen.getByText("Avviso 123")).toBeInTheDocument();
    expect(screen.queryByText("Oristano · F. 1 · P. 2")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Tutto 3" }));
    expect(screen.getByText("Rossi Mario")).toBeInTheDocument();
  });

  test("submits a new query to the SERP URL", async () => {
    mocks.query = "q=rossi";

    render(<OperationalSearchPage />);

    const input = screen.getByLabelText("Query ricerca operativa");
    fireEvent.change(input, { target: { value: "  piras al  " } });
    fireEvent.click(screen.getByRole("button", { name: "Cerca" }));

    expect(mocks.push).toHaveBeenCalledWith("/search?q=piras%20al");
  });

  test("does not search without a token", () => {
    mocks.query = "q=rossi";
    mocks.getStoredAccessToken.mockReturnValue(null);

    render(<OperationalSearchPage />);

    expect(screen.getByText("Nessun risultato trovato per i permessi correnti.")).toBeInTheDocument();
    expect(mocks.searchOperational).not.toHaveBeenCalled();
  });

  test("shows empty and unavailable states", async () => {
    mocks.query = "q=zz";
    mocks.searchOperational.mockResolvedValueOnce({ query: "zz", total: 0, modules: [], items: [] });
    const firstRender = render(<OperationalSearchPage />);

    expect(await screen.findByText("Nessun risultato trovato per i permessi correnti.")).toBeInTheDocument();
    firstRender.unmount();

    mocks.searchOperational.mockRejectedValueOnce("offline");
    const secondRender = render(<OperationalSearchPage />);

    expect(await screen.findByText("Ricerca non disponibile")).toBeInTheDocument();
    secondRender.unmount();

    mocks.searchOperational.mockRejectedValueOnce(new Error("Backend ricerca non disponibile"));
    render(<OperationalSearchPage />);

    expect(await screen.findByText("Backend ricerca non disponibile")).toBeInTheDocument();
  });
});
