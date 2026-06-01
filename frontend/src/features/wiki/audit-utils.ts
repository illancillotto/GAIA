import { formatDateTime, formatDuration } from "@/lib/presentation";
import type { WikiToolAuditLog } from "@/types/api";

export type WikiAuditStats = {
  successCount: number;
  deniedCount: number;
  noMatchCount: number;
  docsCount: number;
  liveCount: number;
  logicCount: number;
  hybridCount: number;
  avgLatencyMs: number;
  topTools: Array<{ key: string; count: number }>;
  topModules: Array<{ key: string; count: number }>;
  topIntents: Array<{ key: string; count: number }>;
  topDeniedTools: Array<{ key: string; count: number }>;
};

export function buildWikiAuditStats(items: WikiToolAuditLog[]): WikiAuditStats {
  const toolCounts = new Map<string, number>();
  const moduleCounts = new Map<string, number>();
  const intentCounts = new Map<string, number>();
  const deniedToolCounts = new Map<string, number>();
  let latencyTotal = 0;

  const base = items.reduce<Omit<WikiAuditStats, "avgLatencyMs" | "topTools" | "topModules" | "topIntents" | "topDeniedTools">>(
    (acc, item) => {
      if (item.success) {
        acc.successCount += 1;
      } else {
        acc.deniedCount += 1;
        deniedToolCounts.set(item.tool_name, (deniedToolCounts.get(item.tool_name) ?? 0) + 1);
      }
      if (!item.found) {
        acc.noMatchCount += 1;
      }
      if (item.mode === "docs_only") {
        acc.docsCount += 1;
      }
      if (item.mode === "live_data") {
        acc.liveCount += 1;
      }
      if (item.mode === "logic") {
        acc.logicCount += 1;
      }
      if (item.mode === "hybrid") {
        acc.hybridCount += 1;
      }
      latencyTotal += item.latency_ms;
      toolCounts.set(item.tool_name, (toolCounts.get(item.tool_name) ?? 0) + 1);
      moduleCounts.set(item.module_key ?? "n/d", (moduleCounts.get(item.module_key ?? "n/d") ?? 0) + 1);
      intentCounts.set(item.intent, (intentCounts.get(item.intent) ?? 0) + 1);
      return acc;
    },
    {
      successCount: 0,
      deniedCount: 0,
      noMatchCount: 0,
      docsCount: 0,
      liveCount: 0,
      logicCount: 0,
      hybridCount: 0,
    },
  );

  const sortCounts = (entries: Iterable<[string, number]>) =>
    [...entries]
      .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
      .slice(0, 3)
      .map(([key, count]) => ({ key, count }));

  return {
    ...base,
    avgLatencyMs: items.length > 0 ? Math.round(latencyTotal / items.length) : 0,
    topTools: sortCounts(toolCounts.entries()),
    topModules: sortCounts(moduleCounts.entries()),
    topIntents: sortCounts(intentCounts.entries()),
    topDeniedTools: sortCounts(deniedToolCounts.entries()),
  };
}

export function formatWikiAuditCreatedAt(value: string): string {
  return formatDateTime(value);
}

export function formatWikiAuditLatency(value: number): string {
  return formatDuration(value);
}

export function formatWikiAuditBoolean(value: boolean, truthy: string, falsy: string): string {
  return value ? truthy : falsy;
}
