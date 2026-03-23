"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ComponentType, SVGProps } from "react";

import { cn } from "@/lib/cn";

type NavItemProps = {
  href: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  label: string;
  badge?: number;
  badgeVariant?: "danger" | "warning";
};

export function NavItem({
  href,
  icon: Icon,
  label,
  badge,
  badgeVariant = "warning",
}: NavItemProps) {
  const pathname = usePathname();
  const isActive = pathname === href;

  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors",
        isActive
          ? "bg-[#EAF3E8] font-medium text-[#1D4E35]"
          : "text-gray-500 hover:bg-gray-50 hover:text-gray-800",
      )}
    >
      <Icon className="h-4 w-4 shrink-0" />
      <span className="flex-1">{label}</span>
      {badge !== undefined ? (
        <span
          className={cn(
            "rounded-full px-1.5 py-0.5 text-[10px] font-medium",
            badgeVariant === "danger" ? "bg-red-50 text-red-600" : "bg-amber-50 text-amber-700",
          )}
        >
          {badge}
        </span>
      ) : null}
    </Link>
  );
}
