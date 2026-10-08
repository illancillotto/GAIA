import { AlertTriangleIcon, RefreshIcon, SearchIcon, UsersIcon } from "@/components/ui/icons";
import { buildBonificaDiagnosis } from "@/lib/elaborazioni-credential-diagnostics";
import { formatDateTime } from "@/lib/presentation";

type PoolCredential = {
  active: boolean;
  last_error: string | null;
  last_used_at: string | null;
};

type ProviderPoolSummary = {
  total: number;
  active: number;
  warnings: number;
  latestUsage: string | undefined;
  description: string;
  tone: "default" | "success" | "warning";
};

export function summarizeProviderPool(credentials: readonly PoolCredential[]): ProviderPoolSummary {
  const active = credentials.filter((credential) => credential.active).length;
  const warnings = credentials.filter((credential) => Boolean(credential.last_error)).length;
  const latestUsage = credentials
    .map((credential) => credential.last_used_at)
    .filter((value): value is string => Boolean(value))
    .sort()
    .at(-1);
  return {
    total: credentials.length,
    active,
    warnings,
    latestUsage,
    description: credentials.length > 0
      ? `${warnings} warning recenti${latestUsage ? ` · ultimo uso ${formatDateTime(latestUsage)}` : ""}`
      : "Nessun account ancora configurato",
    tone: warnings > 0 ? "warning" : active > 0 ? "success" : "default",
  };
}

const GREEN_CARD = { card: "border-[#dfe7dd] bg-[#f8faf8]", icon: "text-[#1D4E35]" };
const BLUE_CARD = { card: "border-[#e4e9f6] bg-[#f6f8ff]", icon: "text-[#3056d3]" };
const PROVIDER_MONITOR = {
  bonifica: {
    distribution: GREEN_CARD,
    warningSuffix: "controllo o nuovo test.",
    warningFallback: "Nessun errore recente registrato sul provider.",
  },
  capacitas: {
    distribution: BLUE_CARD,
    warningSuffix: "controllo o nuovo test di connessione.",
    warningFallback: "Nessun errore recente registrato sul pool.",
  },
};

function bonificaDiagnosis(issue: string | null): string {
  return issue
    ? buildBonificaDiagnosis(issue, null) ?? issue
    : "Nessuna anomalia aperta sul flusso di login Laravel.";
}

type MonitorCard = {
  title: string;
  description: string;
  Icon: typeof UsersIcon;
  palette: { card: string; icon: string };
};

function providerMonitorCards(
  provider: "bonifica" | "capacitas",
  summary: ProviderPoolSummary,
  latestIssue: string | null,
): MonitorCard[] {
  const config = PROVIDER_MONITOR[provider];
  const details: MonitorCard = provider === "bonifica"
    ? { title: "Diagnosi corrente", description: bonificaDiagnosis(latestIssue), Icon: RefreshIcon, palette: BLUE_CARD }
    : {
      title: "Ultimo utilizzo",
      description: summary.latestUsage
        ? `Pool utilizzato l'ultima volta ${formatDateTime(summary.latestUsage)}.`
        : "Nessun utilizzo registrato finora.",
      Icon: SearchIcon,
      palette: GREEN_CARD,
    };
  return [
    {
      title: "Distribuzione account",
      description: summary.total > 0
        ? `${summary.active} account attivi, ${summary.total - summary.active} disattivi.`
        : "Nessun account disponibile nel pool.",
      Icon: UsersIcon,
      palette: config.distribution,
    },
    {
      title: "Warning recenti",
      description: summary.warnings > 0
        ? `${summary.warnings} account richiedono ${config.warningSuffix}`
        : config.warningFallback,
      Icon: AlertTriangleIcon,
      palette: { card: "border-[#f1e0af] bg-[#fff9e8]", icon: "text-[#a36900]" },
    },
    details,
  ];
}

export function SettingsProviderPoolMonitor({
  provider,
  summary,
  latestIssue,
  embedded,
}: {
  provider: "bonifica" | "capacitas";
  summary: ProviderPoolSummary;
  latestIssue: string | null;
  embedded: boolean;
}) {
  const cards = providerMonitorCards(provider, summary, latestIssue);
  return (
    <article className={`rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel ${embedded ? "p-5" : "p-6"}`}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-400">Monitor operativo</p>
      <div className={`grid gap-3 ${embedded ? "mt-3 md:grid-cols-3" : "mt-4"}`}>
        {cards.map(({ title, description, Icon, palette }) => (
          <div key={title} className={`rounded-2xl border ${palette.card} ${embedded ? "p-3" : "p-4"}`}>
            <div className="flex items-start gap-3">
              <div className={`rounded-xl bg-white p-2 ${palette.icon}`}>
                <Icon className="h-4 w-4" />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-900">{title}</p>
                <p className={`mt-1 text-sm text-gray-600 ${embedded ? "leading-5" : "leading-6"}`}>{description}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}
