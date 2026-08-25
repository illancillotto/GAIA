import { render, screen } from "@testing-library/react";
import type { MouseEvent, ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import {
  DesktopTopNavigation,
  isNavigationItemActive,
} from "@/components/layout/desktop-top-navigation";
import { AppShellProvider } from "@/components/layout/app-shell-context";
import type { NavigationItem } from "@/components/layout/navigation";
import { GridIcon } from "@/components/ui/icons";
import type { CurrentUser } from "@/types/api";

const mocks = vi.hoisted(() => ({
  pathname: "/nas-control/reviews",
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    className,
    onClick,
  }: {
    href: string;
    children: ReactNode;
    className?: string;
    onClick?: (event: MouseEvent<HTMLAnchorElement>) => void;
  }) => (
    <a
      href={href}
      className={className}
      onClick={(event) => {
        event.preventDefault();
        onClick?.(event);
      }}
    >
      {children}
    </a>
  ),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => mocks.pathname,
}));

function buildUser(overrides: Partial<CurrentUser> = {}): CurrentUser {
  return {
    id: 1,
    username: "desktop-admin",
    email: "desktop-admin@example.local",
    role: "admin",
    is_active: true,
    module_accessi: true,
    module_rete: false,
    module_inventario: false,
    module_catasto: true,
    module_utenze: false,
    module_operazioni: true,
    module_riordino: false,
    module_ruolo: false,
    module_presenze: false,
    enabled_modules: ["accessi", "catasto", "operazioni"],
    ...overrides,
  };
}

function renderNavigation(user: CurrentUser, options?: { grantedSectionKeys?: string[]; reviewBadge?: number; userBadge?: number }) {
  return render(
    <AppShellProvider
      currentUser={user}
      grantedSectionKeys={options?.grantedSectionKeys ?? []}
      reviewBadge={options?.reviewBadge ?? 0}
      userBadge={options?.userBadge ?? 0}
    >
      <DesktopTopNavigation />
    </AppShellProvider>,
  );
}

describe("DesktopTopNavigation", () => {
  beforeEach(() => {
    mocks.pathname = "/nas-control/reviews";
    window.history.replaceState({}, "", "/nas-control/reviews");
  });

  test("renders only desktop platform navigation without admin or module submenu links", () => {
    renderNavigation(buildUser(), { grantedSectionKeys: ["accessi.users"], reviewBadge: 5, userBadge: 9 });

    expect(screen.queryByRole("link", { name: "Home GAIA" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "La mia attività" })).toHaveAttribute("href", "/me");
    expect(screen.getByRole("link", { name: "NAS Control" })).toHaveAttribute("href", "/nas-control");
    expect(screen.getByRole("link", { name: "Catasto" })).toHaveAttribute("href", "/catasto");
    expect(screen.getByRole("link", { name: "Wiki" })).toHaveAttribute("href", "/wiki");
    expect(screen.queryByText("Admin")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Utenti GAIA" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Cruscotto operatori" })).not.toBeInTheDocument();
    expect(screen.queryByText("Panoramica")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Dashboard" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Sincronizzazione" })).not.toBeInTheDocument();
    expect(screen.queryByText("Dominio NAS")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Review NAS" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Modulo attivo/)).not.toBeInTheDocument();
  });

  test("renders self-service without current module sections in desktop top navigation", () => {
    mocks.pathname = "/me";

    renderNavigation(buildUser());

    expect(screen.getByRole("link", { name: "La mia attività" })).toHaveAttribute("href", "/me");
    expect(screen.queryByText("Self service")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Panoramica" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Presenze" })).not.toBeInTheDocument();
  });

  test("does not present organigramma as a top-level module", () => {
    mocks.pathname = "/organigramma";
    window.history.replaceState({}, "", "/organigramma#override");

    render(
      <AppShellProvider currentUser={buildUser({ role: "viewer", enabled_modules: ["organigramma"] })} grantedSectionKeys={[]}>
        <DesktopTopNavigation />
      </AppShellProvider>,
    );

    expect(screen.queryByRole("link", { name: "Organigramma" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Albero & dettaglio" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Eccezioni visibilità" })).not.toBeInTheDocument();
  });

  test("evaluates desktop navigation active state for hashes, aliases and inactive hash branches", () => {
    const aliasItem: NavigationItem = {
      href: "/target",
      aliases: ["/legacy", "/legacy#old"],
      icon: GridIcon,
      label: "Alias",
      match: "prefix",
    };
    const hashItem: NavigationItem = {
      href: "/organigramma#override",
      icon: GridIcon,
      label: "Override",
    };
    const inactiveWhenHashItem: NavigationItem = {
      href: "/organigramma",
      icon: GridIcon,
      label: "Root",
      inactiveWhenHash: "#override",
    };

    expect(isNavigationItemActive(aliasItem, "/legacy/path", "")).toBe(true);
    expect(isNavigationItemActive(hashItem, "/organigramma", "#override")).toBe(true);
    expect(isNavigationItemActive(inactiveWhenHashItem, "/organigramma", "#override")).toBe(false);
    expect(isNavigationItemActive(inactiveWhenHashItem, "/organigramma", "")).toBe(true);
    expect(isNavigationItemActive({ href: "/exact", icon: GridIcon, label: "Exact" }, "/other", "")).toBe(false);
  });

  test("returns nothing when no current user is available in the shell context", () => {
    render(
      <AppShellProvider currentUser={null} grantedSectionKeys={[]}>
        <DesktopTopNavigation />
      </AppShellProvider>,
    );

    expect(screen.queryByText("Home GAIA")).not.toBeInTheDocument();
  });
});
