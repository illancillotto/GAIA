import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type AlertBannerProps = {
  icon?: ReactNode;
  title?: string;
  children: ReactNode;
  action?: ReactNode;
  variant?: "warning" | "danger" | "info";
};

const bannerStyles = {
  warning: "border-amber-200 bg-amber-50 text-amber-800",
  danger: "border-red-200 bg-red-50 text-red-800",
  info: "border-blue-200 bg-blue-50 text-blue-800",
};

export function AlertBanner({
  icon,
  title,
  children,
  action,
  variant = "warning",
}: AlertBannerProps) {
  return (
    <div className={cn("flex items-start gap-3 rounded-lg border px-4 py-3", bannerStyles[variant])}>
      {icon ? <div className="mt-0.5 shrink-0">{icon}</div> : null}
      <div className="min-w-0 flex-1 text-sm">
        {title ? <p className="mb-1 font-medium">{title}</p> : null}
        <div>{children}</div>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}
