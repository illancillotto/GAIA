import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { WikiConversationsPage } from "@/features/wiki/WikiConversationsPage";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

describe("WikiConversationsPage", () => {
  beforeEach(() => {
    mocks.getStoredAccessToken.mockReturnValue("token");
    vi.stubGlobal(
      "fetch",
      vi.fn()
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          headers: new Headers({ "content-type": "application/json" }),
          json: async () => ({
            id: 1,
            username: "admin",
            email: "admin@test.local",
            role: "admin",
            is_active: true,
            module_accessi: true,
            module_rete: false,
            module_inventario: false,
            module_catasto: true,
            module_utenze: true,
            module_operazioni: false,
            module_riordino: false,
            module_ruolo: false,
            module_presenze: false,
            enabled_modules: ["accessi", "catasto", "utenze"],
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          headers: new Headers({ "content-type": "application/json" }),
          json: async () => ({
            total: 2,
            open_count: 1,
            in_review_count: 0,
            waiting_user_count: 0,
            resolved_count: 1,
            needs_review_count: 1,
            high_priority_count: 1,
            unassigned_review_count: 1,
            open_denied_count: 1,
            open_fallback_count: 1,
            avg_time_to_review_hours: 2,
            avg_time_to_resolve_hours: 4,
            top_mode: "hybrid",
            top_tool: "find_share_by_name",
            top_review_reasons: [{ key: "denied_present", count: 1 }],
            backlog_by_status: [{ key: "open", count: 1 }, { key: "resolved", count: 1 }],
            backlog_by_priority: [{ key: "high", count: 1 }, { key: "medium", count: 1 }],
            backlog_by_owner: [{ key: "unassigned", count: 1 }],
            aging_buckets: [{ key: "lt_24h", count: 2 }],
            items_needing_review: [
              {
                id: "conv-1",
                title: "Thread ricerca share progetti",
                created_by: "admin",
                context_article: "docs/accessi.md",
                status: "open",
                priority: "high",
                assigned_to: null,
                review_reason: "denied_present",
                last_reviewed_at: null,
                resolved_by: null,
                resolved_at: null,
                last_mode: "hybrid",
                top_tool_name: "find_share_by_name",
                denied_count: 1,
                fallback_count: 1,
                no_match_count: 0,
                needs_review: true,
                review_score: 380,
                created_at: "2026-05-28T10:00:00Z",
                updated_at: "2026-05-28T10:05:00Z",
                message_count: 4,
              },
            ],
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          headers: new Headers({ "content-type": "application/json" }),
          json: async () => [
            {
              id: "conv-1",
              title: "Thread ricerca share progetti",
              created_by: "admin",
              context_article: "docs/accessi.md",
              status: "open",
              priority: "high",
              assigned_to: null,
              review_reason: "denied_present",
              last_reviewed_at: null,
              resolved_by: null,
              resolved_at: null,
              last_mode: "hybrid",
              top_tool_name: "find_share_by_name",
              denied_count: 1,
              fallback_count: 1,
              no_match_count: 0,
              needs_review: true,
              review_score: 380,
              created_at: "2026-05-28T10:00:00Z",
              updated_at: "2026-05-28T10:05:00Z",
              message_count: 4,
            },
          ],
        })
        .mockResolvedValue({
          ok: true,
          status: 200,
          headers: new Headers({ "content-type": "application/json" }),
          json: async () => [
            {
              id: "conv-1",
              title: "Thread ricerca share progetti",
              created_by: "admin",
              context_article: "docs/accessi.md",
              status: "resolved",
              priority: "medium",
              assigned_to: "admin",
              review_reason: null,
              last_reviewed_at: "2026-05-28T10:10:00Z",
              resolved_by: "admin",
              resolved_at: "2026-05-28T10:10:00Z",
              last_mode: "hybrid",
              top_tool_name: "find_share_by_name",
              denied_count: 0,
              fallback_count: 0,
              no_match_count: 0,
              needs_review: false,
              review_score: 0,
              created_at: "2026-05-28T10:00:00Z",
              updated_at: "2026-05-28T10:05:00Z",
              message_count: 4,
            },
          ],
        }),
    );
  });

  test("renders persisted conversations list", async () => {
    render(<WikiConversationsPage />);

    await waitFor(() => {
      expect(screen.getByText("Conversazioni Wiki")).toBeInTheDocument();
      expect(screen.getAllByText("Thread ricerca share progetti")).toHaveLength(2);
      expect(screen.getByText(/4 messaggi/)).toBeInTheDocument();
      expect(screen.getByText("open")).toBeInTheDocument();
      expect(screen.getByText("high")).toBeInTheDocument();
      expect(screen.getByText("find_share_by_name · hybrid")).toBeInTheDocument();
      expect(screen.getByText("Conversazioni da rivedere")).toBeInTheDocument();
      expect(screen.getByText("Open con denied o fallback: 1 / 1")).toBeInTheDocument();
      expect(screen.getByText("Review reason: Denied")).toBeInTheDocument();
      expect(screen.getByText("Assegna a me")).toBeInTheDocument();
    });
  });
});
