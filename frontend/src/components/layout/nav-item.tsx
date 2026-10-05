"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ComponentType, MouseEvent, SVGProps } from "react";
import { useEffect, useState } from "react";

import { cn } from "@/lib/cn";

type NavItemProps = {
  href: string;
  aliases?: string[];
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  label: string;
  badge?: number;
  badgeVariant?: "danger" | "warning";
  match?: "exact" | "prefix";
  disabled?: boolean;
  /** Se presente, questo link non risulta attivo quando l'hash è uguale (pathname deve già coincidere). */
  inactiveWhenHash?: string;
};

function splitNavigationHref(href: string): { base: string; hash: string | null } {
  const hashIndex = href.indexOf("#");
  return {
    base: hashIndex >= 0 ? href.slice(0, hashIndex) : href,
    hash: hashIndex >= 0 ? href.slice(hashIndex) : null,
  };
}

function matchesNavigationPath(
  pathname: string,
  targets: string[],
  match: NavItemProps["match"],
): boolean {
  return targets.some((target) => pathname === target || (match === "prefix" && pathname.startsWith(`${target}/`)));
}

function isPlainNavigationClick(event: MouseEvent<HTMLAnchorElement>): boolean {
  return !event.defaultPrevented && event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;
}

function clearCurrentNavigationHash(
  event: MouseEvent<HTMLAnchorElement>,
  href: string,
  setHash: (hash: string) => void,
): boolean {
  const targetUrl = new URL(href, window.location.origin);
  const targetPath = `${targetUrl.pathname}${targetUrl.search}`;
  const currentPath = `${window.location.pathname}${window.location.search}`;
  if (targetPath !== currentPath || !window.location.hash) return false;
  event.preventDefault();
  window.history.pushState(null, "", targetPath);
  setHash("");
  try {
    window.scrollTo({ top: 0, left: 0 });
  } catch {
  }
  window.dispatchEvent(new PopStateEvent("popstate"));
  return true;
}

export function NavItem({
  href,
  aliases = [],
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
    const sync = () => setLocHash(window.location.hash);
    sync();
    window.addEventListener("popstate", sync);
    window.addEventListener("hashchange", sync);
    return () => {
      window.removeEventListener("popstate", sync);
      window.removeEventListener("hashchange", sync);
    };
  }, []);

  const { base: baseHref, hash: requiredHash } = splitNavigationHref(href);
  const aliasBases = aliases.map((alias) => splitNavigationHref(alias).base);
  const pathMatches = matchesNavigationPath(pathname, [baseHref, ...aliasBases], match);

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

  function handleClick(event: MouseEvent<HTMLAnchorElement>): void {
    if (!requiredHash && isPlainNavigationClick(event) && clearCurrentNavigationHash(event, href, setLocHash)) {
      return;
    }
    window.setTimeout(() => setLocHash(window.location.hash), 0);
  }

  return (
    <Link href={href} className={className} onClick={handleClick}>
      {content}
    </Link>
  );
}
