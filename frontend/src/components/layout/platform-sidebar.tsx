"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { GridIcon, LockIcon, SearchIcon, ServerIcon } from "@/components/ui/icons";
import { cn } from "@/lib/cn";

type PlatformSidebarProps = {
  currentModuleLabel: string;
};

type PlatformModule = {
  href: string;
  label: string;
  icon: typeof GridIcon;
};

const platformModules: PlatformModule[] = [
  { href: "/accessi", label: "Accessi", icon: LockIcon },
  { href: "/network", label: "Rete", icon: ServerIcon },
  { href: "/inventory", label: "Inventario", icon: SearchIcon },
  { href: "/catasto", label: "Catasto", icon: GridIcon },
];

export function PlatformSidebar({ currentModuleLabel }: PlatformSidebarProps) {
  const pathname = usePathname();

  return (
    <>
      <div className="border-b border-gray-100 px-4 py-5">
        <div className="mb-3 flex w-fit items-center gap-2 rounded-lg bg-[#1D4E35] px-3 py-2 text-white">
          <ServerIcon className="h-4 w-4" />
          <span className="text-xs font-medium tracking-wide">GAIA</span>
        </div>
        <p className="text-sm font-medium leading-tight text-gray-800">Consorzio di Bonifica</p>
        <p className="text-xs text-gray-400">dell&apos;Oristanese</p>
      </div>

      <nav className="px-2 py-3">
        <div className="mx-2 mb-3 border-b border-gray-100 pb-3">
          <Link
            href="/"
            className="block rounded-lg px-2.5 py-2 text-xs font-medium tracking-wide text-gray-500 transition hover:bg-gray-50 hover:text-gray-800"
          >
            ← Home GAIA
          </Link>
        </div>

        <p className="px-2 pb-1 text-[10px] font-medium uppercase tracking-widest text-gray-400">
          Modulo: {currentModuleLabel}
        </p>

        <div className="space-y-0.5">
          {platformModules.map(({ href, label, icon: Icon }) => {
            const isActive = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
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
              </Link>
            );
          })}
        </div>
      </nav>
    </>
  );
}
