import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { WikiAuditPage } from "@/features/wiki/WikiAuditPage";

const mocks = vi.hoisted(() => ({
  exportWikiToolAuditLogs: vi.fn(),
  getStoredAccessToken: vi.fn(),
  resolveWikiConversationContextLink: vi.fn(),
  getWikiToolAuditLogs: vi.fn(),
  getWikiToolAuditSummary: vi.fn(),
  getWikiToolAuditLogDetail: vi.fn(),
  getWikiToolAuditRelatedLogs: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  exportWikiToolAuditLogs: mocks.exportWikiToolAuditLogs,
  resolveWikiConversationContextLink: mocks.resolveWikiConversationContextLink,
  getWikiToolAuditLogs: mocks.getWikiToolAuditLogs,
  getWikiToolAuditSummary: mocks.getWikiToolAuditSummary,
  getWikiToolAuditLogDetail: mocks.getWikiToolAuditLogDetail,
  getWikiToolAuditRelatedLogs: mocks.getWikiToolAuditRelatedLogs,
}));

describe("WikiAuditPage", () => {
  beforeEach(() => {
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.resolveWikiConversationContextLink.mockResolvedValue({
      href: "/operazioni/pratiche/case-1",
      resolved: true,
      resolution_kind: "operazioni_case",
    });
    mocks.getWikiToolAuditLogs.mockResolvedValue({
      items: [
        {
          id: "audit-1",
          username: "admin",
          role: "admin",
          intent: "logic",
          mode: "hybrid",
          tool_name: "explain_operazioni_case_status",
          module_key: "operazioni",
          conversation_id: "conv-1",
          question_hash: "hash-1",
          question_preview: "spiega il case 1",
          context_article: "OPERAZIONI.md",
          entity_key: "operazioni.cases.case-1",
          entity_label: "Dettaglio case Operazioni",
          response_excerpt: "Case in lavorazione",
          fallback_reason: "docs_enrichment",
          success: true,
          found: true,
          latency_ms: 88,
          docs_source_count: 2,
          evidence_count: 3,
          created_at: "2026-05-28T10:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      page_size: 25,
    });
    mocks.getWikiToolAuditSummary.mockResolvedValue({
      total: 1,
      success_count: 1,
      denied_count: 0,
      no_match_count: 0,
      docs_only_count: 0,
      live_count: 0,
      logic_count: 0,
      hybrid_count: 1,
      avg_latency_ms: 88,
      top_tools: [{ key: "explain_operazioni_case_status", count: 1 }],
      top_modules: [{ key: "operazioni", count: 1 }],
      top_intents: [{ key: "logic", count: 1 }],
      top_denied_tools: [],
      latency_by_mode: [{ mode: "hybrid", avg_latency_ms: 88 }],
      daily_counts: [{ day: "2026-05-28", total: 1, denied: 0 }],
    });
    mocks.getWikiToolAuditLogDetail.mockResolvedValue({
      item: {
        id: "audit-1",
        username: "admin",
        role: "admin",
        intent: "logic",
        mode: "hybrid",
        tool_name: "explain_operazioni_case_status",
        module_key: "operazioni",
        conversation_id: "conv-1",
        question_hash: "hash-1",
        question_preview: "spiega il case 1",
        context_article: "OPERAZIONI.md",
        entity_key: "operazioni.cases.case-1",
        entity_label: "Dettaglio case Operazioni",
        response_excerpt: "Case in lavorazione",
        fallback_reason: "docs_enrichment",
        success: true,
        found: true,
        latency_ms: 88,
        docs_source_count: 2,
        evidence_count: 3,
        created_at: "2026-05-28T10:00:00Z",
      },
    });
    mocks.getWikiToolAuditRelatedLogs.mockResolvedValue({
      items: [
        {
          id: "audit-2",
          username: "admin",
          role: "admin",
          intent: "logic",
          mode: "hybrid",
          tool_name: "explain_operazioni_case_status",
          module_key: "operazioni",
          conversation_id: "conv-1",
          question_hash: "hash-1",
          question_preview: "case correlato",
          context_article: "OPERAZIONI.md",
          entity_key: "operazioni.cases.case-1",
          entity_label: "Dettaglio case Operazioni",
          response_excerpt: "Case correlato",
          fallback_reason: "docs_enrichment",
          success: true,
          found: true,
          latency_ms: 90,
          docs_source_count: 1,
          evidence_count: 2,
          created_at: "2026-05-28T10:05:00Z",
        },
      ],
    });
    mocks.exportWikiToolAuditLogs.mockResolvedValue(new Blob(["csv"]));
  });

  test("renders detail drill-down for selected audit row", async () => {
    render(<WikiAuditPage />);

    await screen.findByText("Registro operativo Wiki Agent");
    await screen.findByText("spiega il case 1");

    fireEvent.click(screen.getByText("spiega il case 1"));

    await waitFor(() => {
      expect(screen.getByText("Dettaglio tool call")).toBeInTheDocument();
      expect(screen.getByText("operazioni.cases.case-1")).toBeInTheDocument();
      expect(screen.getByText("docs_enrichment")).toBeInTheDocument();
      expect(screen.getByText("Case in lavorazione")).toBeInTheDocument();
      expect(screen.getByText("Apri record modulo")).toBeInTheDocument();
      expect(screen.getByText("Apri conversazione")).toBeInTheDocument();
      expect(screen.getByText("Attività correlate")).toBeInTheDocument();
      expect(screen.getByText("case correlato")).toBeInTheDocument();
      expect(screen.getByText("Export CSV")).toBeInTheDocument();
    });
  });
});
