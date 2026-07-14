import { fireEvent, render, screen } from "@testing-library/react";
import type { MouseEvent, ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { PlatformSidebar } from "@/components/layout/platform-sidebar";
import { Sidebar } from "@/components/layout/sidebar";
import type { CurrentUser } from "@/types/api";

const mocks = vi.hoisted(() => ({
  pathname: "/gis/catalogo",
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
    username: "gis-viewer",
    email: "gis-viewer@example.local",
    role: "viewer",
    is_active: true,
    module_accessi: false,
    module_rete: false,
    module_inventario: false,
    module_catasto: true,
    module_utenze: false,
    module_operazioni: false,
    module_riordino: false,
    module_ruolo: false,
    module_presenze: false,
    enabled_modules: ["catasto"],
    ...overrides,
  };
}

describe("GIS platform navigation", () => {
  beforeEach(() => {
    mocks.pathname = "/gis/catalogo";
  });

  test("keeps GIS Platform separate from the Catasto GIS workspace", () => {
    render(<Sidebar currentUser={buildUser()} onLogout={vi.fn()} />);

    expect(screen.getByRole("button", { name: /GIS Platform/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Catalogo layer" })).toHaveAttribute("href", "/gis/catalogo");
    expect(screen.getByRole("link", { name: "GIS Catasto" })).toHaveAttribute("href", "/catasto/gis");
  });

  test("shows GIS Platform as an autonomous platform module", () => {
    render(<Sidebar currentUser={buildUser({ module_catasto: false, enabled_modules: ["gis"] })} onLogout={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /GIS Platform/ }));

    expect(screen.getByRole("link", { name: "GIS Platform" })).toHaveAttribute("href", "/gis/catalogo");
    expect(screen.queryByRole("link", { name: "Catasto" })).not.toBeInTheDocument();
  });

  test("uses the GIS alias and closes the platform switcher after selection", () => {
    mocks.pathname = "/gis";
    render(<PlatformSidebar currentModuleLabel="GIS Platform" currentUser={buildUser({ enabled_modules: ["gis"] })} />);

    fireEvent.click(screen.getByRole("button", { name: /GIS Platform/ }));
    const link = screen.getByRole("link", { name: "GIS Platform" });

    expect(link).toHaveAttribute("href", "/gis/catalogo");

    fireEvent.click(link);

    expect(screen.queryByRole("link", { name: "GIS Platform" })).not.toBeInTheDocument();
  });

  test("uses nested GIS aliases for active platform detection", () => {
    mocks.pathname = "/gis/extra";
    render(<PlatformSidebar currentModuleLabel="GIS Platform" currentUser={buildUser({ enabled_modules: ["gis"] })} />);

    fireEvent.click(screen.getByRole("button", { name: /GIS Platform/ }));

    expect(screen.getByRole("link", { name: "GIS Platform" })).toHaveAttribute("href", "/gis/catalogo");
  });

  test("marks GIS Platform active for nested catalog routes", () => {
    mocks.pathname = "/gis/catalogo/layers";
    render(<PlatformSidebar currentModuleLabel="GIS Platform" currentUser={buildUser({ enabled_modules: ["gis"] })} />);

    fireEvent.click(screen.getByRole("button", { name: /GIS Platform/ }));

    expect(screen.getByRole("link", { name: "GIS Platform" })).toHaveAttribute("href", "/gis/catalogo");
  });

  test("falls back to the provided module label when no platform module is active", () => {
    mocks.pathname = "/unknown";
    render(<PlatformSidebar currentModuleLabel="Modulo corrente" currentUser={buildUser({ enabled_modules: [] })} />);

    expect(screen.getByRole("button", { name: /Modulo corrente/ })).toBeInTheDocument();
  });
});
