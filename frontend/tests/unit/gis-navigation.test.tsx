import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { Sidebar } from "@/components/layout/sidebar";
import type { CurrentUser } from "@/types/api";

const mocks = vi.hoisted(() => ({
  pathname: "/gis/catalogo",
}));

vi.mock("next/link", () => ({
  default: ({ href, children, className }: { href: string; children: ReactNode; className?: string }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => mocks.pathname,
}));

function buildUser(): CurrentUser {
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
});
