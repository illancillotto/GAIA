import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import AdeAlignmentPanel from "@/components/catasto/gis/AdeAlignmentPanel";
import type { AdeAlignmentReportResponse, AdeWfsRunStatusResponse } from "@/types/gis";

const completedRun: AdeWfsRunStatusResponse = {
  run_id: "run-1234567890",
  status: "completed",
  progress_phase: "completed",
  progress_message: "Run completato",
  requested_bbox: { minx: 1, miny: 2, maxx: 3, maxy: 4 },
  tiles: 12,
  tiles_completed: 12,
  progress_percent: 100,
  features: 3456,
  upserted: 123,
  with_geometry: 3000,
  error: null,
  started_at: "2026-08-19T08:00:00Z",
  completed_at: "2026-08-19T08:30:00Z",
};

const failedRun: AdeWfsRunStatusResponse = {
  ...completedRun,
  status: "failed",
  error: "Errore WFS",
};

const runningRun: AdeWfsRunStatusResponse = {
  ...completedRun,
  status: "running",
  progress_phase: "fetch_tiles",
  progress_percent: 42.5,
  progress_message: null,
  completed_at: null,
};

const reportWithSamples: AdeAlignmentReportResponse = {
  run_id: "run-1234567890",
  status: "completed",
  requested_bbox: { minx: 1, miny: 2, maxx: 3, maxy: 4 },
  geometry_threshold_m: 2.5,
  started_at: "2026-08-19T08:00:00Z",
  completed_at: "2026-08-19T08:30:00Z",
  counters: {
    staged_particelle: 10,
    allineate: 4,
    nuove_in_ade: 3,
    geometrie_variate: 2,
    match_ambiguo: 1,
    mancanti_in_ade: 5,
  },
  geojson: {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        properties: { category: "nuove_in_ade" },
        geometry: { type: "Point", coordinates: [9, 40] },
      },
    ],
  },
  samples: [
    {
      category: "nuove_in_ade",
      national_cadastral_reference: "A001-001-0001",
      codice_catastale: "A001",
      foglio: "1",
      particella: "10",
      distance_m: 12.34,
    },
    {
      category: "mancanti_in_ade",
      national_cadastral_reference: null,
      codice_catastale: null,
      foglio: "2",
      particella: "20",
      distance_m: null,
    },
  ],
};

describe("AdeAlignmentPanel", () => {
  test("renders run status, report counters, map preview and samples", () => {
    render(<AdeAlignmentPanel isDark={false} adeRunStatus={completedRun} adeReport={reportWithSamples} />);

    expect(screen.getByRole("link", { name: /Apri workspace/i })).toHaveAttribute("href", "/elaborazioni/ade-alignment");
    expect(screen.getByText("Run run-1234")).toBeInTheDocument();
    expect(screen.getByText("Completato")).toBeInTheDocument();
    expect(screen.getByText(/12 \/ 12 tile/)).toHaveTextContent(/3\.?456 feature/);
    expect(screen.getByText(/Run completato/)).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("allineate")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("nuove AdE")).toBeInTheDocument();
    expect(screen.getByText(/Preview in mappa/)).toBeInTheDocument();
    expect(screen.getByText("A001-001-0001")).toBeInTheDocument();
    expect(screen.getByText(/A001 · Fg\. 1 · Part\. 10 · 12,34 m/)).toBeInTheDocument();
    expect(screen.getByText("2/20")).toBeInTheDocument();
  });

  test("renders empty, running, failed and dark variants without report", () => {
    const { rerender } = render(<AdeAlignmentPanel isDark adeRunStatus={null} adeReport={null} />);

    expect(screen.getByText(/Nessun run AdE disponibile/)).toBeInTheDocument();

    rerender(<AdeAlignmentPanel isDark adeRunStatus={runningRun} adeReport={{ ...reportWithSamples, geojson: null, samples: [] }} />);
    expect(screen.getByText("running")).toBeInTheDocument();
    expect(screen.getByText(/fetch_tiles/)).toBeInTheDocument();
    expect(screen.getByText(/42,5%/)).toBeInTheDocument();
    expect(screen.queryByText(/Preview in mappa/)).not.toBeInTheDocument();
    expect(screen.queryByText("A001-001-0001")).not.toBeInTheDocument();

    rerender(<AdeAlignmentPanel isDark={false} adeRunStatus={failedRun} adeReport={null} />);
    expect(screen.getByText("Fallito")).toBeInTheDocument();
    expect(screen.getByText("Errore WFS")).toBeInTheDocument();
  });

  test("falls back for unknown statuses, invalid dates and non-finite distances", () => {
    render(
      <AdeAlignmentPanel
        isDark={false}
        adeRunStatus={{
          ...runningRun,
          status: "custom_status",
          progress_phase: "custom_phase",
          started_at: "not-a-date",
          completed_at: "not-a-date",
        }}
        adeReport={{
          ...reportWithSamples,
          completed_at: "not-a-date",
          geojson: { type: "FeatureCollection", features: [] },
          samples: [
            { ...reportWithSamples.samples[0], distance_m: Number.POSITIVE_INFINITY },
            {
              category: "match_ambiguo",
              national_cadastral_reference: null,
              codice_catastale: null,
              foglio: null,
              particella: null,
              distance_m: null,
            },
          ],
        }}
      />,
    );

    expect(screen.getByText("custom_status")).toBeInTheDocument();
    expect(screen.getByText(/custom_phase/)).toBeInTheDocument();
    expect(screen.getAllByText(/Invalid Date/).length).toBeGreaterThan(0);
    expect(screen.getByText(/A001 · Fg\. 1 · Part\. 10 · -/)).toBeInTheDocument();
  });
});
