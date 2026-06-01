import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { WikiConversationsAnalyticsPage } from "@/features/wiki/WikiConversationsAnalyticsPage";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  getWikiConversationMetricsSummary: vi.fn(),
  getWikiConversationMetricsSeries: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  getWikiConversationMetricsSummary: mocks.getWikiConversationMetricsSummary,
  getWikiConversationMetricsSeries: mocks.getWikiConversationMetricsSeries,
}));

describe("WikiConversationsAnalyticsPage", () => {
  beforeEach(() => {
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getWikiConversationMetricsSummary.mockResolvedValue({
      total_threads: 12,
      created_count: 4,
      closed_count: 2,
      open_count: 5,
      in_review_count: 3,
      waiting_user_count: 1,
      resolved_count: 3,
      high_priority_count: 2,
      needs_review_count: 4,
      review_entered_count: 2,
      reassigned_count: 1,
      reopened_count: 1,
      avg_time_to_review_hours: 6,
      avg_time_to_resolve_hours: 12,
      avg_open_to_review_hours: 4,
      avg_review_to_resolve_hours: 8,
      avg_waiting_user_hours: 3,
      data_complete_from: "2026-05-01",
      last_backfill_at: "2026-05-29T07:00:00Z",
      top_statuses: [{ key: "open", count: 5 }],
      top_priorities: [{ key: "high", count: 2 }],
      top_owners: [{ key: "admin", count: 3 }],
      top_review_reasons: [{ key: "denied_present", count: 2 }],
      top_event_types: [{ key: "status_changed", count: 4 }],
    });
    mocks.getWikiConversationMetricsSeries.mockResolvedValue({
      dimension_type: "global",
      dimension_key: null,
      days: 30,
      granularity: "day",
      items: [
        {
          metric_date: "2026-05-28",
          period_label: "2026-05-28",
          created_count: 2,
          closed_count: 1,
          open_count: 4,
          in_review_count: 2,
          waiting_user_count: 1,
          resolved_count: 2,
          high_priority_count: 1,
          needs_review_count: 3,
          denied_threads_count: 1,
          fallback_threads_count: 1,
          no_match_threads_count: 0,
          review_entered_count: 1,
          reassigned_count: 0,
          reopened_count: 0,
          avg_time_to_review_hours: 5,
          avg_time_to_resolve_hours: 10,
          avg_open_to_review_hours: 4,
          avg_review_to_resolve_hours: 7,
          avg_waiting_user_hours: 2,
        },
      ],
    });
  });

  test("renders conversation analytics KPIs and trends", async () => {
    render(<WikiConversationsAnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByText("Trend backlog conversazioni")).toBeInTheDocument();
      expect(screen.getByText("12")).toBeInTheDocument();
      expect(screen.getByText("Trend needs review")).toBeInTheDocument();
      expect(screen.getByText("Per review reason")).toBeInTheDocument();
      expect(screen.getByText("denied_present")).toBeInTheDocument();
      expect(screen.getByText("Top eventi workflow")).toBeInTheDocument();
      expect(screen.getByText(/Dati completi da/)).toBeInTheDocument();
    });
  });
});
