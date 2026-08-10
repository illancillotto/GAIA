import { fireEvent, render, screen } from "@testing-library/react";
import type { MouseEvent, ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { MobileSidebarDrawer, Sidebar } from "@/components/layout/sidebar";
import type { CurrentUser } from "@/types/api";

const mocks = vi.hoisted(() => ({
  pathname: "/nas-control",
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

vi.mock("@/components/layout/platform-sidebar", () => ({
  PlatformSidebar: ({ currentModuleLabel }: { currentModuleLabel: string }) => (
    <div data-testid="platform-sidebar">{currentModuleLabel}</div>
  ),
}));

vi.mock("@/components/layout/module-sidebar", () => ({
  ModuleSidebar: ({ currentModuleKey }: { currentModuleKey: string }) => (
    <div data-testid="module-sidebar">{currentModuleKey}</div>
  ),
}));

function buildUser(overrides: Partial<CurrentUser> = {}): CurrentUser {
  return {
    id: 1,
    username: "drawer-user",
    email: "drawer-user@example.local",
    role: "viewer",
    is_active: true,
    module_accessi: false,
    module_rete: false,
    module_inventario: false,
    module_catasto: false,
    module_utenze: false,
    module_operazioni: false,
    module_riordino: false,
    module_ruolo: false,
    module_presenze: false,
    enabled_modules: [],
    ...overrides,
  };
}

describe("Sidebar mobile drawer", () => {
  beforeEach(() => {
    mocks.pathname = "/nas-control";
  });

  test("maps routes to the expected current module key and label", () => {
    const cases = [
      ["/gaia/users", "gaia", "Utenti GAIA"],
      ["/me", "me", "La mia attività"],
      ["/nas-control", "nas_control", "NAS Control"],
      ["/elaborazioni", "elaborazioni", "Elaborazioni"],
      ["/gis", "gis", "GIS Platform"],
      ["/catasto", "catasto", "Catasto"],
      ["/utenze", "utenze", "Utenze"],
      ["/anagrafica/anpr-config", "utenze", "Utenze"],
      ["/network", "network", "Rete"],
      ["/inventory", "inventory", "Inventario"],
      ["/operazioni", "operazioni", "Operazioni"],
      ["/riordino", "riordino", "Riordino"],
      ["/ruolo", "ruolo", "Ruolo"],
      ["/presenze", "presenze", "Presenze"],
      ["/organigramma", "organigramma", "Organigramma"],
      ["/wiki", "wiki", "Wiki"],
      ["/unknown", "nas_control", "NAS Control"],
    ] as const;

    cases.forEach(([pathname, expectedKey, expectedLabel]) => {
      mocks.pathname = pathname;
      const { unmount } = render(<Sidebar currentUser={buildUser()} onLogout={vi.fn()} />);
      expect(screen.getByTestId("module-sidebar")).toHaveTextContent(expectedKey);
      expect(screen.getByTestId("platform-sidebar")).toHaveTextContent(expectedLabel);
      unmount();
    });
  });

  test("renders admin quick links only for authorized GAIA managers", () => {
    const admin = buildUser({ role: "admin", enabled_modules: ["accessi"] });

    render(<Sidebar currentUser={admin} onLogout={vi.fn()} />);

    expect(screen.getByRole("link", { name: "Utenti GAIA" })).toHaveAttribute("href", "/gaia/users");
    expect(screen.getByRole("link", { name: "Cruscotto operatori" })).toHaveAttribute(
      "href",
      "/gaia/users/operatori-cruscotto",
    );
  });

  test("marks the active admin quick link based on the current route", () => {
    const admin = buildUser({ role: "admin", enabled_modules: ["accessi"] });

    mocks.pathname = "/gaia/users";
    const { rerender } = render(<Sidebar currentUser={admin} onLogout={vi.fn()} />);

    expect(screen.getByRole("link", { name: "Utenti GAIA" })).toHaveClass("bg-[#EAF3E8]");

    mocks.pathname = "/gaia/users/operatori-cruscotto";
    rerender(<Sidebar currentUser={admin} onLogout={vi.fn()} />);

    expect(screen.getByRole("link", { name: "Cruscotto operatori" })).toHaveClass("bg-[#EAF3E8]");
  });

  test("hides admin quick links for non-admin users", () => {
    render(<Sidebar currentUser={buildUser()} onLogout={vi.fn()} />);

    expect(screen.queryByRole("link", { name: "Utenti GAIA" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Cruscotto operatori" })).not.toBeInTheDocument();
  });

  test("does not render the drawer while closed", () => {
    render(<MobileSidebarDrawer currentUser={buildUser()} onLogout={vi.fn()} isOpen={false} onClose={vi.fn()} />);

    expect(screen.queryByText("Navigazione")).not.toBeInTheDocument();
  });

  test("closes the drawer on overlay, escape and route changes, and keeps logout available", () => {
    const onClose = vi.fn();
    const onLogout = vi.fn();
    const { rerender } = render(
      <MobileSidebarDrawer currentUser={buildUser()} onLogout={onLogout} isOpen onClose={onClose} />,
    );

    expect(screen.getByText("Navigazione")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Chiudi navigazione" })[0]);
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    fireEvent.click(screen.getByRole("button", { name: "Logout" }));

    mocks.pathname = "/catasto";
    rerender(<MobileSidebarDrawer currentUser={buildUser()} onLogout={onLogout} isOpen onClose={onClose} />);

    expect(onClose).toHaveBeenCalledTimes(4);
    expect(onLogout).toHaveBeenCalledTimes(1);
  });
});
