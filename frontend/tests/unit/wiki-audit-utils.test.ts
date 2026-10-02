import { buildWikiAuditStats, formatWikiAuditBoolean, formatWikiAuditCreatedAt, formatWikiAuditLatency } from "@/features/wiki/audit-utils";
import { formatDateTime } from "@/lib/presentation";
import type { WikiToolAuditLog } from "@/types/api";

function auditItem(overrides: Partial<WikiToolAuditLog> = {}): WikiToolAuditLog {
  return {
    id: "1", username: "admin", role: "admin", intent: "live_data",
    mode: "live_data", tool_name: "tool", module_key: "wiki",
    conversation_id: null, question_hash: "hash", question_preview: "question",
    context_article: null, entity_key: null, entity_label: null,
    response_excerpt: null, fallback_reason: null, success: true, found: true,
    latency_ms: 10, docs_source_count: 0, evidence_count: 0,
    created_at: "2026-05-27T10:00:00Z", ...overrides,
  };
}

describe("Wiki audit utils", () => {
  test("returns empty counters and rankings without audit items", () => {
    expect(buildWikiAuditStats([])).toEqual({
      successCount: 0, deniedCount: 0, noMatchCount: 0, docsCount: 0,
      liveCount: 0, logicCount: 0, hybridCount: 0, avgLatencyMs: 0,
      topTools: [], topModules: [], topIntents: [], topDeniedTools: [],
    });
  });

  test.each(["docs_only", "live_data", "logic", "hybrid", "unknown", "toString", "__proto__", ""])(
    "counts only the exact known mode %s without mutating items", (mode) => {
      const items = [auditItem({ mode }), auditItem({ mode })];
      const original = structuredClone(items);
      const stats = buildWikiAuditStats(items);

      expect([stats.docsCount, stats.liveCount, stats.logicCount, stats.hybridCount]).toEqual([
        mode === "docs_only" ? 2 : 0,
        mode === "live_data" ? 2 : 0,
        mode === "logic" ? 2 : 0,
        mode === "hybrid" ? 2 : 0,
      ]);
      expect(stats.topIntents).toEqual([{ key: "live_data", count: 2 }]);
      expect(items).toEqual(original);
    },
  );

  test("retains ranking, top-three limit, missing module and rounded latency", () => {
    const items = [
      auditItem({ tool_name: "delta", module_key: null, latency_ms: 1, success: false }),
      auditItem({ tool_name: "beta", module_key: "", latency_ms: 2, success: false }),
      auditItem({ tool_name: "alpha", module_key: null, latency_ms: 2, success: false }),
      auditItem({ tool_name: "charlie", module_key: "wiki", latency_ms: 2, success: false }),
      auditItem({ tool_name: "delta", module_key: "wiki", latency_ms: 2, success: false }),
    ];
    const stats = buildWikiAuditStats(items);
    const ranking = [{ key: "delta", count: 2 }, { key: "alpha", count: 1 }, { key: "beta", count: 1 }];
    expect(stats.topTools).toEqual(ranking);
    expect(stats.topDeniedTools).toEqual(ranking);
    expect(stats.topModules).toEqual([{ key: "n/d", count: 2 }, { key: "wiki", count: 2 }, { key: "", count: 1 }]);
    expect(stats.avgLatencyMs).toBe(2);
    expect(stats.deniedCount).toBe(5);
  });

  test("formats audit creation time using the shared formatter", () => {
    const value = "2026-05-27T10:00:00Z";
    expect(formatWikiAuditCreatedAt(value)).toBe(formatDateTime(value));
  });

  test("aggregates audit stats from current page items", () => {
    const stats = buildWikiAuditStats([
      {
        id: "1",
        username: "admin",
        role: "admin",
        intent: "live_data",
        mode: "live_data",
        tool_name: "find_nas_user",
        module_key: "accessi",
        conversation_id: null,
        question_hash: "hash-1",
        question_preview: "mostrami l'utente NAS",
        context_article: null,
        entity_key: "accessi.nas-users.mrossi",
        entity_label: "Dettaglio utente NAS",
        response_excerpt: "Lookup utente NAS",
        fallback_reason: null,
        success: true,
        found: true,
        latency_ms: 42,
        docs_source_count: 0,
        evidence_count: 1,
        created_at: "2026-05-27T10:00:00Z",
      },
      {
        id: "2",
        username: "viewer",
        role: "viewer",
        intent: "logic",
        mode: "hybrid",
        tool_name: "explain_operazioni_case_status",
        module_key: "operazioni",
        conversation_id: null,
        question_hash: "hash-2",
        question_preview: "spiega il case",
        context_article: "OPERAZIONI.md",
        entity_key: "operazioni.cases.case-1",
        entity_label: "Dettaglio case Operazioni",
        response_excerpt: "Il case è in progress",
        fallback_reason: "docs_enrichment",
        success: false,
        found: false,
        latency_ms: 1420,
        docs_source_count: 2,
        evidence_count: 3,
        created_at: "2026-05-27T10:01:00Z",
      },
    ]);

    expect(stats).toEqual({
      successCount: 1,
      deniedCount: 1,
      noMatchCount: 1,
      docsCount: 0,
      liveCount: 1,
      logicCount: 0,
      hybridCount: 1,
      avgLatencyMs: 731,
      topIntents: [
        { key: "live_data", count: 1 },
        { key: "logic", count: 1 },
      ],
      topDeniedTools: [
        { key: "explain_operazioni_case_status", count: 1 },
      ],
      topTools: [
        { key: "explain_operazioni_case_status", count: 1 },
        { key: "find_nas_user", count: 1 },
      ],
      topModules: [
        { key: "accessi", count: 1 },
        { key: "operazioni", count: 1 },
      ],
    });
  });

  test("formats booleans and latency for audit table", () => {
    expect(formatWikiAuditBoolean(true, "Successo", "Denied")).toBe("Successo");
    expect(formatWikiAuditBoolean(false, "Successo", "Denied")).toBe("Denied");
    expect(formatWikiAuditLatency(1420)).toBe("1.4 s");
  });
});
