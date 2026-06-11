import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { WikiRequestsPage } from "@/features/wiki/WikiRequestsPage";
import { WikiSupportAnalyticsPage } from "@/features/wiki/WikiSupportAnalyticsPage";
import { WikiSupportPage } from "@/features/wiki/WikiSupportPage";

const mocks = vi.hoisted(() => ({
  createWikiRequest: vi.fn(),
  getMyWikiRequests: vi.fn(),
  getMyWikiRequestsSummary: vi.fn(),
  getStoredAccessToken: vi.fn(),
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
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  createWikiRequest: mocks.createWikiRequest,
  getMyWikiRequests: mocks.getMyWikiRequests,
  getMyWikiRequestsSummary: mocks.getMyWikiRequestsSummary,
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

vi.mock("next/navigation", () => ({
  useSearchParams: mocks.useSearchParams,
}));

describe("Wiki support surfaces", () => {
  beforeEach(() => {
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.useSearchParams.mockReturnValue(new URLSearchParams());

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

  test("renders support page with my requests", async () => {
    render(<WikiSupportPage />);

    await waitFor(() => {
      expect(screen.getByText("Supporto Wiki")).toBeInTheDocument();
      expect(screen.getByText("Mi serve supporto")).toBeInTheDocument();
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
