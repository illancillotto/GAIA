import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import AttivitaDetailPage from "@/app/operazioni/attivita/[id]/page";
import AttivitaPage from "@/app/operazioni/attivita/page";
import AttivitaContatoriPage from "@/app/operazioni/attivita-contatori/page";

const mocks = vi.hoisted(() => ({
  getActivities: vi.fn(),
  getOperators: vi.fn(),
  getActivity: vi.fn(),
  getActivityAttachments: vi.fn(),
  getActivityGpsSummary: vi.fn(),
  getActivityGpsViewer: vi.fn(),
  getAttachmentPreviewData: vi.fn(),
  downloadAttachment: vi.fn(),
  useParams: vi.fn(),
  useSearchParams: vi.fn(),
}));

vi.mock("@/features/operazioni/api/client", () => ({
  getActivities: mocks.getActivities,
  getOperators: mocks.getOperators,
  getActivity: mocks.getActivity,
  getActivityAttachments: mocks.getActivityAttachments,
  getActivityGpsSummary: mocks.getActivityGpsSummary,
  getActivityGpsViewer: mocks.getActivityGpsViewer,
  getAttachmentPreviewData: mocks.getAttachmentPreviewData,
  downloadAttachment: mocks.downloadAttachment,
}));

vi.mock("next/navigation", () => ({
  useParams: mocks.useParams,
  useSearchParams: mocks.useSearchParams,
}));

vi.mock("@/components/operazioni/operazioni-module-page", () => ({
  OperazioniModulePage: ({ children }: { children: () => ReactNode }) => <div>{children()}</div>,
}));

vi.mock("@/components/operazioni/gps-track-viewer-dialog", () => ({
  OperazioniGpsTrackViewerDialog: () => null,
}));

vi.mock("@/components/operazioni/attachment-preview-dialog", () => ({
  OperazioniAttachmentPreviewDialog: () => null,
}));

describe("Operazioni attivita pages", () => {
  beforeEach(() => {
    mocks.getActivities.mockReset();
    mocks.getOperators.mockReset();
    mocks.getActivity.mockReset();
    mocks.getActivityAttachments.mockReset();
    mocks.getActivityGpsSummary.mockReset();
    mocks.getActivityGpsViewer.mockReset();
    mocks.getAttachmentPreviewData.mockReset();
    mocks.downloadAttachment.mockReset();
    mocks.useParams.mockReset();
    mocks.useSearchParams.mockReset();

    mocks.useParams.mockReturnValue({ id: "activity-1" });
    mocks.useSearchParams.mockReturnValue(new URLSearchParams());
    mocks.getOperators.mockResolvedValue({
      items: [
        {
          id: "wc-operator-1",
          gaia_user_id: 7,
          username: "mrossi",
          first_name: "Mario",
          last_name: "Rossi",
          email: "mario.rossi@example.test",
        },
        {
          id: "wc-operator-2",
          gaia_user_id: 8,
          username: "lbianchi",
          first_name: "Luca",
          last_name: "Bianchi",
          email: "luca.bianchi@example.test",
        },
      ],
    });
    mocks.getActivityAttachments.mockResolvedValue([]);
    mocks.getActivityGpsSummary.mockResolvedValue(null);
  });

  test("activities list shows mobile meter badge and meter context", async () => {
    mocks.getActivities.mockResolvedValue({
      items: [
        {
          id: "activity-1",
          status: "in_progress",
          started_at: "2026-06-29T08:00:00Z",
          operator_user_id: 7,
          catalog_name: "Lettura contatori",
          text_note: "Attivita mobile",
          linked_meter_reading: {
            id: "reading-1",
            punto_consegna: "CNT-001",
            matricola: "MAT-001",
            lettura_finale: "258.000",
            data_lettura: "2026-06-29",
            photo_url: null,
            source: "mobile",
            record_kind: "meter_reading",
          },
        },
      ],
      total: 1,
      page: 1,
      page_size: 50,
    });

    render(<AttivitaPage />);

    expect(await screen.findByText("Lettura contatori")).toBeInTheDocument();
    expect(screen.getByText("Contatore mobile")).toBeInTheDocument();
    expect(screen.getByText(/Contatore CNT-001/)).toBeInTheDocument();
    expect(screen.getByText(/Lettura 258.000/)).toBeInTheDocument();
    expect(screen.getByText(/Mario Rossi · 29\/06\/2026/)).toBeInTheDocument();
  });

  test("activities list can request only mobile meter activities", async () => {
    mocks.getActivities
      .mockResolvedValueOnce({
        items: [
          {
            id: "activity-1",
            status: "in_progress",
            started_at: "2026-06-29T08:00:00Z",
            operator_user_id: 7,
            catalog_name: "Lettura contatori",
            text_note: "Attivita mobile",
            linked_meter_reading: {
              id: "reading-1",
              punto_consegna: "CNT-001",
              matricola: "MAT-001",
              lettura_finale: "258.000",
              data_lettura: "2026-06-29",
              photo_url: null,
              source: "mobile",
              record_kind: "meter_reading",
            },
          },
          {
            id: "activity-2",
            status: "submitted",
            started_at: "2026-06-29T09:00:00Z",
            operator_user_id: 8,
            catalog_name: "Sopralluogo",
            text_note: "Attivita generica",
            linked_meter_reading: null,
          },
        ],
        total: 2,
        page: 1,
        page_size: 50,
      })
      .mockResolvedValueOnce({
        items: [
          {
            id: "activity-1",
            status: "in_progress",
            started_at: "2026-06-29T08:00:00Z",
            operator_user_id: 7,
            catalog_name: "Lettura contatori",
            text_note: "Attivita mobile",
            linked_meter_reading: {
              id: "reading-1",
              punto_consegna: "CNT-001",
              matricola: "MAT-001",
              lettura_finale: "258.000",
              data_lettura: "2026-06-29",
              photo_url: null,
              source: "mobile",
              record_kind: "meter_reading",
            },
          },
        ],
        total: 1,
        page: 1,
        page_size: 50,
      });

    render(<AttivitaPage />);

    await screen.findByText("Sopralluogo");
    fireEvent.click(screen.getByRole("button", { name: "Solo contatori mobile" }));

    await waitFor(() => {
      expect(mocks.getActivities).toHaveBeenLastCalledWith({
        page_size: "50",
        mobile_meter_only: "true",
      });
    });
    expect(screen.queryByText("Sopralluogo")).not.toBeInTheDocument();
    expect(screen.getByText("Lettura contatori")).toBeInTheDocument();
  });

  test("activities list can filter by operator and prefill from query string", async () => {
    mocks.useSearchParams.mockReturnValue(new URLSearchParams("operator_user_id=7"));
    mocks.getActivities.mockResolvedValue({
      items: [
        {
          id: "activity-1",
          status: "in_progress",
          started_at: "2026-06-29T08:00:00Z",
          ended_at: null,
          operator_user_id: 7,
          catalog_name: "Lettura contatori",
          text_note: "Attivita mobile",
          linked_meter_reading: null,
        },
      ],
      total: 1,
      page: 1,
      page_size: 50,
    });

    render(<AttivitaPage />);

    await waitFor(() => {
      expect(mocks.getActivities).toHaveBeenCalledWith({
        page_size: "50",
        operator_user_id: "7",
      });
    });

    expect(screen.getByDisplayValue("Mario Rossi")).toBeInTheDocument();
    expect(screen.getByText(/Filtro operatore attivo su Mario Rossi/)).toBeInTheDocument();
  });

  test("dedicated meter activities page starts with mobile meter filter", async () => {
    mocks.getActivities.mockResolvedValue({
      items: [
        {
          id: "activity-1",
          status: "in_progress",
          started_at: "2026-06-29T08:00:00Z",
          operator_user_id: 7,
          catalog_name: "Lettura contatori",
          text_note: "Attivita mobile",
          linked_meter_reading: {
            id: "reading-1",
            punto_consegna: "CNT-001",
            matricola: "MAT-001",
            lettura_finale: "258.000",
            data_lettura: "2026-06-29",
            photo_url: null,
            source: "mobile",
            record_kind: "meter_reading",
          },
        },
      ],
      total: 1,
      page: 1,
      page_size: 50,
    });

    render(<AttivitaContatoriPage />);

    await waitFor(() => {
      expect(mocks.getActivities).toHaveBeenCalledWith({
        page_size: "50",
        mobile_meter_only: "true",
      });
    });

    expect(screen.getByText(/attività gate mobile/i)).toBeInTheDocument();
    expect(screen.getByText("Solo contatori mobile")).toBeInTheDocument();
  });

  test("activity detail shows linked meter reading summary and catasto link", async () => {
    mocks.getActivity.mockResolvedValue({
      id: "activity-1",
      activity_catalog_id: "catalog-1",
      catalog_name: "Lettura contatori",
      status: "in_progress",
      started_at: "2026-06-29T08:00:00Z",
      ended_at: null,
      operator_user_id: 7,
      team_id: null,
      vehicle_id: null,
      duration_minutes_declared: null,
      duration_minutes_calculated: null,
      gps_track_summary_id: null,
      audio_note_attachment_id: null,
      text_note: "Attivita mobile",
      submitted_at: null,
      reviewed_by_user_id: null,
      reviewed_at: null,
      review_outcome: null,
      review_note: null,
      server_received_at: "2026-06-29T08:01:00Z",
      created_at: "2026-06-29T08:01:00Z",
      updated_at: "2026-06-29T08:01:00Z",
      linked_meter_reading: {
        id: "reading-1",
        punto_consegna: "CNT-001",
        matricola: "MAT-001",
        lettura_finale: "258.000",
        data_lettura: "2026-06-29",
        photo_url: null,
        source: "mobile",
        record_kind: "meter_reading",
      },
    });

    render(<AttivitaDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Contatore mobile collegato")).toBeInTheDocument();
    });

    expect(screen.getByText("CNT-001")).toBeInTheDocument();
    expect(screen.getByText(/Matr. MAT-001/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Apri registro Catasto" })).toHaveAttribute(
      "href",
      "/catasto/letture-contatori",
    );
  });
});
