import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type BadgeVariant = "success" | "danger" | "warning" | "info" | "neutral";

const variantMap: Record<BadgeVariant, string> = {
  success: "bg-green-50 text-green-700",
  danger: "bg-red-50 text-red-700",
  warning: "bg-amber-50 text-amber-700",
  info: "bg-blue-50 text-blue-700",
  neutral: "bg-gray-100 text-gray-500",
};

type BadgeProps = {
  children: ReactNode;
  variant?: BadgeVariant;
  className?: string;
};

export function Badge({ children, variant = "neutral", className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        variantMap[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}
