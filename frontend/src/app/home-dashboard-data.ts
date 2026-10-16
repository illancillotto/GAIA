import {
  getDashboardSummary,
  getPresenceSummary,
  getUtenzeStats,
  SESSION_BOOTSTRAP_TIMEOUT_MS,
} from "@/lib/api";
import { catastoGetIndiciOverview } from "@/lib/api/catasto";
import { getRuoloStats, getRuoloStatsAnalytics } from "@/lib/ruolo-api";
import { hasSectionAccess } from "@/lib/section-access";
import type {
  AnagraficaStats,
  CurrentUser,
  DashboardSummary,
  UserPresenceSummary,
} from "@/types/api";
import type { CatIndiceOverview } from "@/types/catasto";
import type { RuoloStatsAnalyticsResponse, RuoloStatsResponse } from "@/types/ruolo";

export type HomeDashboardData = {
  dashboardSummary: DashboardSummary;
  utenzeSummary: AnagraficaStats;
  presenceSummary: UserPresenceSummary;
  ruoloStats: RuoloStatsResponse;
  ruoloAnalytics: RuoloStatsAnalyticsResponse | null;
  catastoIndiciOverview: CatIndiceOverview | null;
};

type HomeDashboardUser = Pick<CurrentUser, "role" | "enabled_modules">;

const emptyPresenceSummary: UserPresenceSummary = {
  window_minutes: 15,
  active_users: 0,
  visible_users: 0,
  items: [],
  by_module: [],
};

const emptyUtenzeSummary: AnagraficaStats = {
  total_subjects: 0,
  total_persons: 0,
  total_companies: 0,
  total_unknown: 0,
  total_documents: 0,
  requires_review: 0,
  active_subjects: 0,
  inactive_subjects: 0,
  documents_unclassified: 0,
  deceased_updates_last_24h: 0,
  deceased_updates_current_month: 0,
  deceased_updates_current_year: 0,
  by_letter: {},
};

const emptyDashboardSummary: DashboardSummary = {
  nas_users: 0,
  nas_groups: 0,
  shares: 0,
  reviews: 0,
  snapshots: 0,
  sync_runs: 0,
};

const emptyRuoloStats: RuoloStatsResponse = {
  items: [],
};

export const emptyHomeDashboardData: HomeDashboardData = {
  dashboardSummary: emptyDashboardSummary,
  utenzeSummary: emptyUtenzeSummary,
  presenceSummary: emptyPresenceSummary,
  ruoloStats: emptyRuoloStats,
  ruoloAnalytics: null,
  catastoIndiciOverview: null,
};

function settledValue<T>(result: PromiseSettledResult<T>, fallback: T): T {
  return result.status === "fulfilled" ? result.value : fallback;
}

function settledError(result: PromiseSettledResult<unknown>): unknown {
  return result.status === "rejected" ? result.reason : null;
}

export function canReadHomePresenceSummary(user: HomeDashboardUser, grantedSectionKeys: string[]): boolean {
  return (
    (user.role === "admin" || user.role === "super_admin")
    && user.enabled_modules.includes("accessi")
    && hasSectionAccess(grantedSectionKeys, "accessi.users")
  );
}

export async function loadHomeDashboardData(
  token: string,
  user: HomeDashboardUser,
  grantedSectionKeys: string[],
): Promise<HomeDashboardData> {
  const hasCatasto = user.enabled_modules.includes("catasto");
  const hasRuolo = user.enabled_modules.includes("ruolo");
  const hasUtenze = user.enabled_modules.includes("utenze");
  const hasAccessi = user.enabled_modules.includes("accessi");

  const [dashboardSummaryResult, utenzeStatsResult, presenceSummaryResult, ruoloStatsResult] = await Promise.allSettled([
    hasAccessi ? getDashboardSummary(token, { timeoutMs: SESSION_BOOTSTRAP_TIMEOUT_MS }) : Promise.resolve(emptyDashboardSummary),
    hasUtenze ? getUtenzeStats(token) : Promise.resolve(emptyUtenzeSummary),
    canReadHomePresenceSummary(user, grantedSectionKeys) ? getPresenceSummary(token, { windowMinutes: 15 }) : Promise.resolve(emptyPresenceSummary),
    hasRuolo ? getRuoloStats(token) : Promise.resolve(emptyRuoloStats),
  ]);

  const ruoloStats = settledValue(ruoloStatsResult, emptyRuoloStats);
  const latestRuoloYear = ruoloStats.items[0]?.anno_tributario;
  const [ruoloAnalyticsResult, catastoIndiciOverviewResult] = await Promise.allSettled([
    hasRuolo && latestRuoloYear != null ? getRuoloStatsAnalytics(token, latestRuoloYear) : Promise.resolve(null),
    hasCatasto ? catastoGetIndiciOverview(token, latestRuoloYear) : Promise.resolve(null),
  ]);

  const settledResults = [dashboardSummaryResult, utenzeStatsResult, presenceSummaryResult, ruoloStatsResult, ruoloAnalyticsResult, catastoIndiciOverviewResult];
  if (settledResults.some((result) => result.status === "rejected")) {
    console.warn("Home dashboard loaded with partial module data", {
      dashboardError: settledError(dashboardSummaryResult),
      utenzeError: settledError(utenzeStatsResult),
      presenceSummaryError: settledError(presenceSummaryResult),
      ruoloStatsError: settledError(ruoloStatsResult),
      ruoloAnalyticsError: settledError(ruoloAnalyticsResult),
      catastoIndiciOverviewError: settledError(catastoIndiciOverviewResult),
    });
  }

  return {
    dashboardSummary: settledValue(dashboardSummaryResult, emptyDashboardSummary),
    utenzeSummary: settledValue(utenzeStatsResult, emptyUtenzeSummary),
    presenceSummary: settledValue(presenceSummaryResult, emptyPresenceSummary),
    ruoloStats,
    ruoloAnalytics: settledValue(ruoloAnalyticsResult, null),
    catastoIndiciOverview: settledValue(catastoIndiciOverviewResult, null),
  };
}
