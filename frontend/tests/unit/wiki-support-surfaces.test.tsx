import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { WikiRequestsPage } from "@/features/wiki/WikiRequestsPage";
import { WikiSupportAnalyticsPage } from "@/features/wiki/WikiSupportAnalyticsPage";
import { WikiSupportPage } from "@/features/wiki/WikiSupportPage";

const mocks = vi.hoisted(() => ({
  createWikiRequestWithArtifacts: vi.fn(),
  getMyWikiRequests: vi.fn(),
  getMyWikiRequestsSummary: vi.fn(),
  getStoredAccessToken: vi.fn(),
  downloadWikiRequestArtifact: vi.fn(),
  getWikiRequestArtifacts: vi.fn(),
  getWikiRequestAssignees: vi.fn(),
  getWikiRequestDuplicates: vi.fn(),
  getWikiRequestEvents: vi.fn(),
  getWikiRequestFamily: vi.fn(),
  getWikiRequestLinkedDuplicates: vi.fn(),
  getWikiRequests: vi.fn(),
  getWikiSupportAnalyticsClusters: vi.fn(),
  getWikiSupportAnalyticsInsights: vi.fn(),
  getWikiSupportAnalyticsSeries: vi.fn(),
  getWikiSupportAnalyticsSummary: vi.fn(),
  makeWikiRequestCanonical: vi.fn(),
  markWikiRequestViewed: vi.fn(),
  markWikiRequestDuplicate: vi.fn(),
  reopenWikiRequest: vi.fn(),
  unlinkWikiRequestDuplicate: vi.fn(),
  updateWikiRequest: vi.fn(),
  updateWikiRequestFeedback: vi.fn(),
  useSearchParams: vi.fn(),
  captureWikiRequestArtifacts: vi.fn(),
  consumeWikiSupportDraft: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  createWikiRequestWithArtifacts: mocks.createWikiRequestWithArtifacts,
  downloadWikiRequestArtifact: mocks.downloadWikiRequestArtifact,
  getMyWikiRequests: mocks.getMyWikiRequests,
  getMyWikiRequestsSummary: mocks.getMyWikiRequestsSummary,
  getWikiRequestArtifacts: mocks.getWikiRequestArtifacts,
  getWikiRequestAssignees: mocks.getWikiRequestAssignees,
  getWikiRequestDuplicates: mocks.getWikiRequestDuplicates,
  getWikiRequestEvents: mocks.getWikiRequestEvents,
  getWikiRequestFamily: mocks.getWikiRequestFamily,
  getWikiRequestLinkedDuplicates: mocks.getWikiRequestLinkedDuplicates,
  getWikiRequests: mocks.getWikiRequests,
  getWikiSupportAnalyticsClusters: mocks.getWikiSupportAnalyticsClusters,
  getWikiSupportAnalyticsInsights: mocks.getWikiSupportAnalyticsInsights,
  getWikiSupportAnalyticsSeries: mocks.getWikiSupportAnalyticsSeries,
  getWikiSupportAnalyticsSummary: mocks.getWikiSupportAnalyticsSummary,
  makeWikiRequestCanonical: mocks.makeWikiRequestCanonical,
  markWikiRequestViewed: mocks.markWikiRequestViewed,
  markWikiRequestDuplicate: mocks.markWikiRequestDuplicate,
  reopenWikiRequest: mocks.reopenWikiRequest,
  unlinkWikiRequestDuplicate: mocks.unlinkWikiRequestDuplicate,
  updateWikiRequest: mocks.updateWikiRequest,
  updateWikiRequestFeedback: mocks.updateWikiRequestFeedback,
}));

vi.mock("@/features/wiki/request-support", () => ({
  captureWikiRequestArtifacts: mocks.captureWikiRequestArtifacts,
  consumeWikiSupportDraft: mocks.consumeWikiSupportDraft,
}));

vi.mock("next/navigation", () => ({
  useSearchParams: mocks.useSearchParams,
}));

describe("Wiki support surfaces", () => {
  beforeEach(() => {
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => "blob:wiki-request"),
      revokeObjectURL: vi.fn(),
    });
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.useSearchParams.mockReturnValue(new URLSearchParams());
    mocks.captureWikiRequestArtifacts.mockResolvedValue({ uiSnapshot: { module_snapshot: { module: "wiki" } } });
    mocks.consumeWikiSupportDraft.mockReturnValue(null);
    mocks.downloadWikiRequestArtifact.mockResolvedValue(new Blob(["fake-image"], { type: "image/jpeg" }));
    mocks.getWikiRequestArtifacts.mockResolvedValue([
      {
        id: "artifact-screen",
        request_id: "req-1",
        artifact_type: "screenshot",
        filename: "screen.jpg",
        mime_type: "image/jpeg",
        payload: null,
        created_by: "utente",
        created_at: "2026-06-10T10:00:00Z",
      },
      {
        id: "artifact-meta",
        request_id: "req-1",
        artifact_type: "screenshot_meta",
        filename: null,
        mime_type: "application/json",
        payload: { capture_method: "svg_foreign_object", width: 1280 },
        created_by: "utente",
        created_at: "2026-06-10T10:00:00Z",
      },
      {
        id: "artifact-ui",
        request_id: "req-1",
        artifact_type: "ui_snapshot",
        filename: null,
        mime_type: "application/json",
        payload: {
          module_snapshot: {
            module: "operazioni",
            route_type: "pratiche",
            route_key: "operazioni/pratiche/123",
            entity_id: "123",
            active_tabs: ["Dettaglio"],
            filters: { context: "miniapp", status: "open" },
            entity: {
              title: "Pratica operativa",
              case_number: "CASE-123",
              status: "In lavorazione",
            },
          },
        },
        created_by: "utente",
        created_at: "2026-06-10T10:00:00Z",
      },
    ]);
    mocks.createWikiRequestWithArtifacts.mockResolvedValue({
      id: "req-created",
      user_question: "Nuova richiesta",
      agent_response: "Risposta agente",
      category: "support_request",
      request_type: "help_request",
      status: "new",
      priority: "medium",
      severity: "medium",
      created_by: "me",
      assigned_to: null,
      assigned_to_name: null,
      module_key: "wiki",
      page_path: "/wiki",
      source_channel: "support_page",
      impact_scope: "single_user",
      conversation_id: "conv-created",
      context_article: null,
      context_entity_key: null,
      dedupe_key: null,
      canonical_request_id: null,
      canonical_request_question: null,
      canonical_request_status: null,
      desired_outcome: null,
      observed_behavior: null,
      expected_behavior: null,
      resolution_message: null,
      last_admin_update_at: null,
      user_last_viewed_at: null,
      has_unread_update: false,
      user_feedback_rating: null,
      user_feedback_notes: null,
      user_feedback_submitted_at: null,
      admin_notes: null,
      created_at: "2026-06-10T10:00:00Z",
      updated_at: "2026-06-10T10:00:00Z",
    });

    mocks.getWikiRequests.mockResolvedValue([
      {
        id: "req-1",
        user_question: "Non trovo una funzione",
        agent_response: "Risposta agente",
        category: "support_request",
        request_type: "help_request",
        status: "new",
        priority: "medium",
        severity: "medium",
        created_by: "utente",
        assigned_to: null,
        assigned_to_name: null,
        module_key: "wiki",
        page_path: "/wiki",
        source_channel: "widget",
        impact_scope: "single_user",
        conversation_id: "conv-1",
        context_article: null,
        context_entity_key: null,
        dedupe_key: null,
        canonical_request_id: null,
        canonical_request_question: null,
        canonical_request_status: null,
        desired_outcome: null,
        observed_behavior: null,
        expected_behavior: null,
        resolution_message: null,
        last_admin_update_at: null,
        user_last_viewed_at: null,
        has_unread_update: false,
        user_feedback_rating: null,
        user_feedback_notes: null,
        user_feedback_submitted_at: null,
        admin_notes: null,
        created_at: "2026-06-10T10:00:00Z",
        updated_at: "2026-06-10T10:00:00Z",
      },
    ]);
    mocks.getWikiRequestAssignees.mockResolvedValue([]);
    mocks.getWikiRequestEvents.mockResolvedValue([]);
    mocks.getWikiRequestDuplicates.mockResolvedValue([]);
    mocks.getWikiRequestLinkedDuplicates.mockResolvedValue([]);
    mocks.getWikiRequestFamily.mockResolvedValue(null);
    mocks.getMyWikiRequests.mockResolvedValue([
      {
        id: "req-me",
        user_question: "Mi serve supporto",
        agent_response: "Risposta agente",
        category: "support_request",
        request_type: "help_request",
        status: "waiting_user",
        priority: "medium",
        severity: "medium",
        created_by: "me",
        assigned_to: null,
        assigned_to_name: null,
        module_key: "wiki",
        page_path: "/wiki",
        source_channel: "support_page",
        impact_scope: "single_user",
        conversation_id: "conv-me",
        context_article: null,
        context_entity_key: null,
        dedupe_key: null,
        canonical_request_id: null,
        canonical_request_question: null,
        canonical_request_status: null,
        desired_outcome: null,
        observed_behavior: null,
        expected_behavior: null,
        resolution_message: null,
        last_admin_update_at: null,
        user_last_viewed_at: null,
        has_unread_update: false,
        user_feedback_rating: null,
        user_feedback_notes: null,
        user_feedback_submitted_at: null,
        admin_notes: null,
        created_at: "2026-06-10T10:00:00Z",
        updated_at: "2026-06-10T10:00:00Z",
      },
    ]);
    mocks.getMyWikiRequestsSummary.mockResolvedValue({
      total_requests: 1,
      open_requests: 1,
      unread_updates: 0,
      waiting_user_requests: 1,
      resolved_feedback_pending: 0,
    });
    mocks.markWikiRequestViewed.mockResolvedValue({
      id: "req-me",
      user_question: "Mi serve supporto",
      agent_response: "Risposta agente",
      category: "support_request",
      request_type: "help_request",
      status: "waiting_user",
      priority: "medium",
      severity: "medium",
      created_by: "me",
      assigned_to: null,
      assigned_to_name: null,
      module_key: "wiki",
      page_path: "/wiki",
      source_channel: "support_page",
      impact_scope: "single_user",
      conversation_id: "conv-me",
      context_article: null,
      context_entity_key: null,
      dedupe_key: null,
      canonical_request_id: null,
      canonical_request_question: null,
      canonical_request_status: null,
      desired_outcome: null,
      observed_behavior: null,
      expected_behavior: null,
      resolution_message: null,
      last_admin_update_at: null,
      user_last_viewed_at: null,
      has_unread_update: false,
      user_feedback_rating: null,
      user_feedback_notes: null,
      user_feedback_submitted_at: null,
      admin_notes: null,
      created_at: "2026-06-10T10:00:00Z",
      updated_at: "2026-06-10T10:00:00Z",
    });
    mocks.getWikiSupportAnalyticsSummary.mockResolvedValue({
      total_requests: 10,
      open_requests: 6,
      resolved_requests: 4,
      assigned_requests: 7,
      urgent_requests: 1,
      high_severity_requests: 2,
      feature_requests: 2,
      bug_reports: 1,
      access_issues: 1,
      data_issues: 1,
      help_requests: 5,
      duplicate_requests: 1,
      canonical_cases: 2,
      reopened_requests: 1,
      no_match_origin_requests: 2,
      guardrail_origin_requests: 1,
      docs_only_origin_requests: 3,
      top_modules: [{ key: "wiki", count: 5 }],
      top_request_types: [{ key: "help_request", count: 4 }],
      top_impact_scopes: [{ key: "single_user", count: 6 }],
      top_statuses: [],
      top_priorities: [],
      top_severities: [],
      top_pages: [],
      top_assignees: [],
      top_creators: [],
      top_source_channels: [],
    });
    mocks.getWikiSupportAnalyticsSeries.mockResolvedValue({
      items: [
        {
          metric_date: "2026-06-10",
          period_label: "2026-06-10",
          created_count: 3,
          resolved_count: 2,
          open_count: 4,
          feature_request_count: 1,
          bug_report_count: 1,
          urgent_count: 0,
          high_severity_count: 1,
        },
      ],
    });
    mocks.getWikiSupportAnalyticsClusters.mockResolvedValue({
      items: [
        {
          cluster_key: "wiki-help",
          title: "Supporto Wiki",
          request_type: "help_request",
          module_key: "wiki",
          page_path: "/wiki",
          total_requests: 3,
          open_requests: 2,
          duplicate_requests: 0,
          affected_users: 2,
          canonical_case_count: 1,
          latest_created_at: "2026-06-10T10:00:00Z",
          sample_questions: ["Non trovo una funzione"],
        },
      ],
    });
    mocks.getWikiSupportAnalyticsInsights.mockResolvedValue({
      items: [
        {
          insight_type: "trend",
          title: "Trend richieste",
          description: "Aumento richieste wiki",
          severity: "info",
          metric_value: 3,
          action_hint: null,
          related_key: "wiki",
        },
      ],
    });
  });

  test("renders requests admin page", async () => {
    render(<WikiRequestsPage />);

    await waitFor(() => {
      expect(screen.getByText("Richieste registrate dal Wiki")).toBeInTheDocument();
      expect(screen.getAllByText("Non trovo una funzione").length).toBeGreaterThan(0);
    });
  });

  test("renders support inbox variant filtered to support items", async () => {
    render(<WikiRequestsPage supportOnly />);

    await waitFor(() => {
      expect(screen.getByText("Inbox supporto Wiki")).toBeInTheDocument();
      expect(screen.getAllByText("Supporto operativo").length).toBeGreaterThan(0);
    });
  });

  test("renders request detail variant selecting the provided id", async () => {
    render(<WikiRequestsPage initialRequestId="req-1" />);

    await waitFor(() => {
      expect(screen.getByText("Dettaglio richiesta")).toBeInTheDocument();
      expect(screen.getAllByText("Non trovo una funzione").length).toBeGreaterThan(0);
    });
  });

  test("renders snapshot panel with contextual summary and technical details", async () => {
    render(<WikiRequestsPage initialRequestId="req-1" />);

    await waitFor(() => {
      expect(screen.getByText("Snapshot del caso")).toBeInTheDocument();
      expect(screen.getByText("Contesto modulo")).toBeInTheDocument();
      expect(screen.getByText("Stato operativo catturato")).toBeInTheDocument();
      expect(screen.getByText("Filtri e parametri attivi")).toBeInTheDocument();
      expect(screen.getByText("CASE-123")).toBeInTheDocument();
      expect(screen.getByText("Apri immagine")).toBeInTheDocument();
      expect(screen.getByText("Dettagli tecnici snapshot")).toBeInTheDocument();
    });
  });

  test("downloads screenshot artifact from request detail", async () => {
    render(<WikiRequestsPage initialRequestId="req-1" />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Scarica screenshot" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Scarica screenshot" }));

    await waitFor(() => {
      expect(mocks.downloadWikiRequestArtifact).toHaveBeenCalledWith("token", "req-1", "artifact-screen");
    });
  });

  test("renders support page with my requests", async () => {
    render(<WikiSupportPage />);

    await waitFor(() => {
      expect(screen.getByText("Supporto Wiki")).toBeInTheDocument();
      expect(screen.getByText("Mi serve supporto")).toBeInTheDocument();
    });
  });

  test("support page submits via createWikiRequestWithArtifacts using draft artifacts when available", async () => {
    mocks.useSearchParams.mockReturnValue(
      new URLSearchParams("draft_id=draft-1&question=Serve%20supporto%20operativo&answer=Risposta%20Wiki&module_key=operazioni&page_path=%2Foperazioni%2Fpratiche%2F123"),
    );
    mocks.consumeWikiSupportDraft.mockReturnValue({
      uiSnapshot: { module_snapshot: { module: "operazioni", entity_id: "123" } },
    });

    render(<WikiSupportPage />);

    await waitFor(() => {
      expect(screen.getByDisplayValue("Serve supporto operativo")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Registra segnalazione" }));

    await waitFor(() => {
      expect(mocks.createWikiRequestWithArtifacts).toHaveBeenCalledTimes(1);
    });

    expect(mocks.consumeWikiSupportDraft).toHaveBeenCalledWith("draft-1");
    expect(mocks.captureWikiRequestArtifacts).not.toHaveBeenCalled();
    expect(mocks.createWikiRequestWithArtifacts.mock.calls[0]?.[2]).toEqual({
      uiSnapshot: { module_snapshot: { module: "operazioni", entity_id: "123" } },
    });
  });

  test("renders support analytics page summary", async () => {
    render(<WikiSupportAnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByText("Support Analytics")).toBeInTheDocument();
      expect(screen.getByText("Richieste totali")).toBeInTheDocument();
      expect(screen.getByText("Supporto Wiki")).toBeInTheDocument();
    });
  });
});
