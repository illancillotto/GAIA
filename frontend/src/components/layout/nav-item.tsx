"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ComponentType, SVGProps } from "react";
import { useEffect, useState } from "react";

import { cn } from "@/lib/cn";

type NavItemProps = {
  href: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  label: string;
  badge?: number;
  badgeVariant?: "danger" | "warning";
  match?: "exact" | "prefix";
  disabled?: boolean;
  /** Se presente, questo link non risulta attivo quando l'hash è uguale (pathname deve già coincidere). */
  inactiveWhenHash?: string;
};

export function NavItem({
  href,
  icon: Icon,
  label,
  badge,
  badgeVariant = "warning",
  match = "exact",
  disabled = false,
  inactiveWhenHash,
}: NavItemProps) {
  const pathname = usePathname();
  const [locHash, setLocHash] = useState("");

  useEffect(() => {
    const sync = () => setLocHash(typeof window !== "undefined" ? window.location.hash : "");
    sync();
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, []);

  const hashIndex = href.indexOf("#");
  const baseHref = hashIndex >= 0 ? href.slice(0, hashIndex) : href;
  const requiredHash = hashIndex >= 0 ? href.slice(hashIndex) : null;

  const pathMatches =
    match === "prefix"
      ? pathname === baseHref || pathname.startsWith(`${baseHref}/`)
      : pathname === baseHref;

  let isActive = pathMatches;
  if (requiredHash) {
    isActive = pathMatches && locHash === requiredHash;
  } else if (inactiveWhenHash) {
    isActive = pathMatches && locHash !== inactiveWhenHash;
  }

  const className = cn(
    "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors",
    disabled
      ? "cursor-not-allowed text-gray-300"
      : isActive
        ? "bg-[#EAF3E8] font-medium text-[#1D4E35]"
        : "text-gray-500 hover:bg-gray-50 hover:text-gray-800",
  );

  const content = (
    <>
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
    </>
  );

  if (disabled) {
    return (
      <span aria-disabled="true" className={className} title="Accesso non abilitato">
        {content}
      </span>
    );
  }

  return (
    <Link href={href} className={className}>
      {content}
    </Link>
  );
}
