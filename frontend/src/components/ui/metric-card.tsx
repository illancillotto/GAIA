import { cn } from "@/lib/cn";

type MetricCardProps = {
  label: string;
  value: string | number;
  sub?: string;
  variant?: "default" | "success" | "danger" | "warning" | "info";
};

const valueColor = {
  default: "text-gray-900",
  success: "text-green-700",
  danger: "text-red-600",
  warning: "text-amber-600",
  info: "text-blue-700",
};

export function MetricCard({ label, value, sub, variant = "default" }: MetricCardProps) {
  return (
    <div className="metric-card">
      <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-gray-400">{label}</p>
      <p className={cn("text-2xl font-medium", valueColor[variant])}>{value}</p>
      {sub ? <p className="mt-1 text-xs text-gray-400">{sub}</p> : null}
    </div>
  );
}
