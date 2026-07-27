import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import {
  UtenzeSubjectVisuraCard,
  isVisuraYoungerThanSevenDays,
  type SubjectVisuraRequestInfo,
} from "@/components/utenze/utenze-subject-visura-card";
import type { AnagraficaCatastoDocument, ElaborazioneBatchDetail } from "@/types/api";

const requestState: SubjectVisuraRequestInfo = {
  identifier: "RSSMRA80A01H501Z",
  identifierLabel: "Codice fiscale",
  subjectKind: "PF",
};

function buildDocument(createdAt: string): AnagraficaCatastoDocument {
  return {
    id: "document-1",
    request_id: "request-1",
    comune: "ORISTANO",
    foglio: "1",
    particella: "2",
    subalterno: null,
    catasto: "Terreni",
    tipo_visura: "Sintetica",
    filename: "visura-soggetto.pdf",
    codice_fiscale: "RSSMRA80A01H501Z",
    created_at: createdAt,
  };
}

function buildBatch(): ElaborazioneBatchDetail {
  return {
    id: "batch-1",
    user_id: 1,
    credential_id: null,
    name: "Visura soggetto",
    status: "pending",
    batch_kind: "manual_single",
    total_items: 1,
    completed_items: 0,
    failed_items: 0,
    skipped_items: 0,
    not_found_items: 0,
    source_filename: null,
    current_operation: null,
    report_json_path: null,
    report_md_path: null,
    created_at: "2026-07-27T08:00:00Z",
    started_at: null,
    completed_at: null,
    requests: [],
  };
}

describe("UtenzeSubjectVisuraCard", () => {
  test("detects visure younger than seven days", () => {
    const nowMs = new Date("2026-07-27T08:00:00Z").getTime();
    expect(isVisuraYoungerThanSevenDays(buildDocument("2026-07-21T08:00:01Z"), nowMs)).toBe(true);
    expect(isVisuraYoungerThanSevenDays(buildDocument("2026-07-20T08:00:00Z"), nowMs)).toBe(false);
    expect(isVisuraYoungerThanSevenDays(buildDocument("2026-07-28T08:00:00Z"), nowMs)).toBe(false);
    expect(isVisuraYoungerThanSevenDays(buildDocument("invalid"), nowMs)).toBe(false);
    expect(isVisuraYoungerThanSevenDays(null, nowMs)).toBe(false);
  });

  test("shows latest visura link and previews it", () => {
    const onPreviewLatest = vi.fn();
    render(
      <UtenzeSubjectVisuraCard
        requestState={requestState}
        latestVisura={buildDocument("2026-07-26T08:00:00Z")}
        isRequesting={false}
        error={null}
        result={null}
        isEmbedded={false}
        nowMs={new Date("2026-07-27T08:00:00Z").getTime()}
        onRequest={vi.fn()}
        onPreviewLatest={onPreviewLatest}
      />,
    );

    expect(screen.getByText("Ultima visura scaricata")).toBeInTheDocument();
    expect(screen.getByText("visura-soggetto.pdf")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Visualizza visura" }));
    expect(onPreviewLatest).toHaveBeenCalledWith(expect.objectContaining({ id: "document-1" }));
  });

  test("asks confirmation when latest visura is less than seven days old", () => {
    const onRequest = vi.fn();
    render(
      <UtenzeSubjectVisuraCard
        requestState={requestState}
        latestVisura={buildDocument("2026-07-26T08:00:00Z")}
        isRequesting={false}
        error={null}
        result={null}
        isEmbedded={false}
        nowMs={new Date("2026-07-27T08:00:00Z").getTime()}
        onRequest={onRequest}
        onPreviewLatest={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Richiedi visura" }));
    expect(screen.getByRole("dialog", { name: "Conferma nuova visura" })).toBeInTheDocument();
    expect(screen.getAllByText(/ha meno di 7 giorni/)).toHaveLength(2);
    expect(onRequest).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Annulla" }));
    expect(screen.queryByRole("dialog", { name: "Conferma nuova visura" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Richiedi visura" }));
    fireEvent.click(screen.getByRole("button", { name: "Conferma richiesta" }));
    expect(onRequest).toHaveBeenCalledTimes(1);
  });

  test("requests directly when there is no recent visura and renders status messages", () => {
    const onRequest = vi.fn();
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);
    render(
      <UtenzeSubjectVisuraCard
        requestState={requestState}
        latestVisura={buildDocument("2026-07-10T08:00:00Z")}
        isRequesting={false}
        error="Errore richiesta"
        result={buildBatch()}
        isEmbedded
        nowMs={new Date("2026-07-27T08:00:00Z").getTime()}
        onRequest={onRequest}
        onPreviewLatest={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Richiedi visura" }));
    expect(onRequest).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("dialog", { name: "Conferma nuova visura" })).not.toBeInTheDocument();
    expect(screen.getByText("Errore richiesta")).toBeInTheDocument();
    expect(screen.getByText("Richiesta visura avviata sul batch Visura soggetto.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Apri batch" }));
    expect(openSpy).toHaveBeenCalledWith("/elaborazioni/batches/batch-1", "_blank", "noopener,noreferrer");
    openSpy.mockRestore();
  });

  test("renders completed request without batch link outside embedded mode", () => {
    render(
      <UtenzeSubjectVisuraCard
        requestState={requestState}
        latestVisura={null}
        isRequesting={false}
        error={null}
        result={buildBatch()}
        isEmbedded={false}
        onRequest={vi.fn()}
        onPreviewLatest={vi.fn()}
      />,
    );

    expect(screen.getByText("Richiesta visura avviata sul batch Visura soggetto.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Apri batch" })).not.toBeInTheDocument();
  });

  test("disables request without identifier and shows fallback labels", () => {
    render(
      <UtenzeSubjectVisuraCard
        requestState={null}
        latestVisura={null}
        isRequesting={false}
        error={null}
        result={null}
        isEmbedded={false}
        onRequest={vi.fn()}
        onPreviewLatest={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Richiedi visura" })).toBeDisabled();
    expect(screen.getByText("Non disponibile")).toBeInTheDocument();
    expect(screen.getByText("Codice fiscale o partita IVA mancanti")).toBeInTheDocument();
  });

  test("keeps confirm action disabled while request is running", () => {
    render(
      <UtenzeSubjectVisuraCard
        requestState={requestState}
        latestVisura={buildDocument("2026-07-26T08:00:00Z")}
        isRequesting
        error={null}
        result={null}
        isEmbedded={false}
        nowMs={new Date("2026-07-27T08:00:00Z").getTime()}
        onRequest={vi.fn()}
        onPreviewLatest={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Richiesta in corso..." })).toBeDisabled();
  });
});
