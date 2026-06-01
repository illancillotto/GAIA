import { buildWikiAuditStats, formatWikiAuditBoolean, formatWikiAuditLatency } from "@/features/wiki/audit-utils";

describe("Wiki audit utils", () => {
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
