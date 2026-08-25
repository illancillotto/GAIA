import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  ActiveOperationsOverview,
  type DashboardRunningOperation,
} from "@/components/elaborazioni/active-operations-overview";

const baseOperation: DashboardRunningOperation = {
  id: "batch-1",
  area: "Batch runtime",
  title: "Visure terreni",
  detail: "Elaborazione delle visure in corso",
  startedAt: "2026-08-25T08:00:00.000Z",
  statusLabel: "In corso",
  href: "/elaborazioni/batches/1",
};

describe("ActiveOperationsOverview", () => {
  it("spiega chiaramente lo stato vuoto senza polling", () => {
    render(<ActiveOperationsOverview attentionCount={0} isLive={false} onOpen={vi.fn()} operations={[]} />);

    expect(screen.getByRole("heading", { name: "Nessuna lavorazione in corso" })).toBeInTheDocument();
    expect(screen.getByText("Il quadro si aggiorna quando torni su questa pagina.")).toBeInTheDocument();
    expect(screen.getByText("Nessun problema")).toBeInTheDocument();
    expect(screen.getByText("Tutto tranquillo")).toBeInTheDocument();
  });

  it("mostra avanzamenti reali, errori e apre il monitor scelto", () => {
    const onOpen = vi.fn();
    const operations: DashboardRunningOperation[] = [
      {
        ...baseOperation,
        progress: { completed: 12, total: 10, percent: 140, failed: 2 },
      },
      {
        ...baseOperation,
        id: "sync-2",
        title: "Import posizioni",
        statusLabel: "In ripresa",
        progress: { completed: 5, total: 20, percent: null },
      },
      {
        ...baseOperation,
        id: "sync-3",
        title: "Sincronizzazione iniziale",
        statusLabel: "In coda",
        progress: { completed: 0, total: 10, percent: -20, failed: 0 },
      },
      {
        ...baseOperation,
        id: "sync-4",
        title: "WhiteCompany",
        progress: { completed: 4, total: 0, percent: null },
      },
      {
        ...baseOperation,
        id: "sync-5",
        title: "Poste Online",
        progress: { completed: null, total: 8, percent: null },
      },
      {
        ...baseOperation,
        id: "sync-6",
        title: "Avanzamento stimato",
        progress: { completed: null, total: null, percent: 50 },
      },
    ];

    render(<ActiveOperationsOverview attentionCount={3} isLive onOpen={onOpen} operations={operations} />);

    expect(screen.getByRole("heading", { name: "6 lavorazioni in corso" })).toBeInTheDocument();
    expect(screen.getByText("I dati si aggiornano automaticamente. Non serve ricaricare la pagina.")).toBeInTheDocument();
    expect(screen.getByText("3 da controllare")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Avanzamento Visure terreni" })).toHaveAttribute("aria-valuenow", "100");
    expect(screen.getByRole("progressbar", { name: "Avanzamento Import posizioni" })).toHaveAttribute("aria-valuenow", "25");
    expect(screen.getByRole("progressbar", { name: "Avanzamento Sincronizzazione iniziale" })).toHaveAttribute("aria-valuenow", "0");
    expect(screen.getByText("— di —")).toBeInTheDocument();
    expect(screen.getByText("2 con errore")).toBeInTheDocument();
    expect(screen.getAllByText("Avviata")).toHaveLength(2);

    fireEvent.click(screen.getAllByRole("button", { name: "Apri monitor" })[1]);
    expect(onOpen).toHaveBeenCalledWith(operations[1]);
  });
});
