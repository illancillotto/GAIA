"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/cn";

const links: { href: string; label: string; match?: "exact" | "prefix" }[] = [
  { href: "/catasto", label: "Dashboard", match: "exact" },
  { href: "/catasto/distretti", label: "Distretti", match: "prefix" },
  { href: "/catasto/particelle", label: "Particelle", match: "prefix" },
  { href: "/catasto/anomalie", label: "Anomalie", match: "prefix" },
  { href: "/catasto/import", label: "Import", match: "prefix" },
];

function isActive(pathname: string, href: string, match: "exact" | "prefix" = "prefix"): boolean {
  if (match === "exact") return pathname === href;
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function CatastoPhase1Nav() {
  const pathname = usePathname();

  return (
    <nav className="flex flex-wrap gap-2 rounded-2xl border border-gray-100 bg-white p-2 shadow-sm">
      {links.map((item) => {
        const active = isActive(pathname, item.href, item.match);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "rounded-xl px-3 py-2 text-sm font-medium transition",
              active ? "bg-[#EAF3E8] text-[#1D4E35]" : "text-gray-600 hover:bg-gray-50 hover:text-gray-900",
            )}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

