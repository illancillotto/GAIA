import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  BatchStatisticsInline,
  BatchStatisticsPanel,
  formatBatchDuration,
  shouldRetainBatchDetail,
} from "@/components/elaborazioni/batch-statistics";
import type { CatastoBatchStatistics } from "@/types/api";


function statistics(overrides: Partial<CatastoBatchStatistics> = {}): CatastoBatchStatistics {
  return {
    duration_seconds: 3723,
    processed_items: 8,
    remaining_items: 2,
    progress_percent: 80,
    success_rate_percent: 75,
    completed_per_hour: 5.8,
    processed_per_hour: 7.7,
    estimated_remaining_seconds: 930,
    total_attempts: 11,
    average_attempts: 1.38,
    credentials_used: [
      {
        credential_id: "credential-1",
        label: "Alessandro",
        sister_username: "USR-ALE",
        request_count: 6,
        execution_count: 7,
      },
      {
        credential_id: "credential-2",
        label: "Credenziale rimossa",
        sister_username: null,
        request_count: 2,
        execution_count: 4,
      },
    ],
    ...overrides,
  };
}


describe("batch statistics presentation", () => {
  it("formats missing, negative, short, minute and hour durations", () => {
    expect(formatBatchDuration(undefined)).toBe("—");
    expect(formatBatchDuration(-2)).toBe("0s");
    expect(formatBatchDuration(42)).toBe("42s");
    expect(formatBatchDuration(125)).toBe("2m 05s");
    expect(formatBatchDuration(3723)).toBe("1h 02m");
  });

  it("retains cached details only for terminal batches", () => {
    const detail = { id: "batch" } as never;
    expect(shouldRetainBatchDetail(undefined, "completed")).toBe(false);
    expect(shouldRetainBatchDetail(detail, "processing")).toBe(false);
    expect(shouldRetainBatchDetail(detail, "completed")).toBe(true);
  });

  it("renders the compact loading, empty and populated states", () => {
    const { rerender } = render(<BatchStatisticsInline />);
    expect(screen.getByText("Calcolo statistiche...")).toBeInTheDocument();

    rerender(<BatchStatisticsInline statistics={statistics({ completed_per_hour: null, credentials_used: [] })} />);
    expect(screen.getByText(/— visure\/ora/)).toBeInTheDocument();
    expect(screen.getByText("Nessuna credenziale usata")).toBeInTheDocument();

    rerender(<BatchStatisticsInline statistics={statistics()} />);
    expect(screen.getByText(/5,8 visure\/ora/)).toBeInTheDocument();
    expect(screen.getByText("Alessandro, Credenziale rimossa")).toHaveAttribute("title", "Alessandro, Credenziale rimossa");
  });

  it("renders all metrics and credential usage", () => {
    const { rerender } = render(<BatchStatisticsPanel />);
    expect(screen.queryByLabelText("Statistiche batch")).not.toBeInTheDocument();

    rerender(<BatchStatisticsPanel statistics={statistics()} />);
    expect(screen.getByLabelText("Statistiche batch")).toBeInTheDocument();
    expect(screen.getByText("Durata totale")).toBeInTheDocument();
    expect(screen.getByText("1h 02m")).toBeInTheDocument();
    expect(screen.getByText("75%")).toBeInTheDocument();
    expect(screen.getByText("Alessandro").parentElement).toHaveTextContent("Alessandro · USR-ALE · 6 richieste · 7 esecuzioni");
    expect(screen.getByText("Credenziale rimossa").parentElement).toHaveTextContent("Credenziale rimossa · 2 richieste · 4 esecuzioni");
  });

  it("renders unavailable rates and an empty credential set", () => {
    render(
      <BatchStatisticsPanel
        statistics={statistics({
          success_rate_percent: null,
          completed_per_hour: null,
          estimated_remaining_seconds: null,
          credentials_used: [],
        })}
      />,
    );

    expect(screen.getAllByText("—")).toHaveLength(3);
    expect(screen.getByText("Nessuna credenziale ancora utilizzata.")).toBeInTheDocument();
  });
});
