"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import {
  getVisiblePlatformModules,
  type NavigationItem,
} from "@/components/layout/navigation";
import { useAppShellContext } from "@/components/layout/app-shell-context";
import { cn } from "@/lib/cn";

type DesktopNavigationLinkProps = {
  item: NavigationItem;
  pathname: string;
  locHash: string;
};

export function isNavigationItemActive(item: NavigationItem, pathname: string, locHash: string): boolean {
  const aliases = item.aliases ?? [];
  const match = item.match ?? "exact";
  const hashIndex = item.href.indexOf("#");
  const baseHref = hashIndex >= 0 ? item.href.slice(0, hashIndex) : item.href;
  const requiredHash = hashIndex >= 0 ? item.href.slice(hashIndex) : null;
  const aliasBases = aliases.map((alias) => {
    const aliasHashIndex = alias.indexOf("#");
    return aliasHashIndex >= 0 ? alias.slice(0, aliasHashIndex) : alias;
  });

  const pathMatches =
    match === "prefix"
      ? pathname === baseHref ||
        pathname.startsWith(`${baseHref}/`) ||
        aliasBases.some((aliasBase) => pathname === aliasBase || pathname.startsWith(`${aliasBase}/`))
      : pathname === baseHref || aliasBases.includes(pathname);

  if (requiredHash) {
    return pathMatches && locHash === requiredHash;
  }
  if (item.inactiveWhenHash) {
    return pathMatches && locHash !== item.inactiveWhenHash;
  }
  return pathMatches;
}

function DesktopNavigationLink({
  item,
  pathname,
  locHash,
}: DesktopNavigationLinkProps) {
  const isActive = isNavigationItemActive(item, pathname, locHash);
  const Icon = item.icon;
  const className = cn(
    "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
    isActive
      ? "border-[#8CB39D] bg-[#EAF3E8] text-[#1D4E35]"
      : "border-gray-200 bg-white/80 text-gray-600 hover:border-gray-300 hover:bg-white hover:text-gray-900",
  );

  return (
    <Link href={item.href} className={className}>
      <Icon className="h-3.5 w-3.5 shrink-0" />
      <span className="whitespace-nowrap">{item.label}</span>
    </Link>
  );
}

export function DesktopTopNavigation() {
  const pathname = usePathname();
  const [locHash, setLocHash] = useState("");
  const { currentUser } = useAppShellContext();

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

  const platformModules = useMemo(
    () => (currentUser ? getVisiblePlatformModules(currentUser) : []),
    [currentUser],
  );

  if (!currentUser) {
    return null;
  }

  return (
    <div className="hidden border-b border-gray-100 bg-[linear-gradient(180deg,#fdfefc_0%,#f7faf7_100%)] md:block">
      <div className="flex flex-col gap-3 px-7 py-3">
        <div className="overflow-x-auto pb-1">
          <div className="flex min-w-max items-center gap-2">
            {platformModules.map(({ href, label, icon, aliases }) => (
              <DesktopNavigationLink
                key={href}
                item={{ href, label, icon, aliases, match: "prefix" }}
                pathname={pathname}
                locHash={locHash}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
