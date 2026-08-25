import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { MouseEvent, ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { AppShell } from "@/components/layout/app-shell";
import { ModuleSidebar } from "@/components/layout/module-sidebar";
import { NavItem } from "@/components/layout/nav-item";
import { Topbar } from "@/components/layout/topbar";

const mocks = vi.hoisted(() => ({
  usePresenceHeartbeat: vi.fn(),
  push: vi.fn(),
  getStoredAccessToken: vi.fn(),
  clearStoredAccessToken: vi.fn(),
  searchOperational: vi.fn(),
  pathname: "/presenze/regole",
}));

vi.mock("@/components/layout/sidebar", () => ({
  Sidebar: ({ currentUser, onLogout }: { currentUser: { username: string }; onLogout: () => void }) => (
    <aside>
      Sidebar {currentUser.username}
      <button type="button" onClick={onLogout}>
        logout shell
      </button>
    </aside>
  ),
  MobileSidebarDrawer: ({
    currentUser,
    onLogout,
    isOpen,
  }: {
    currentUser: { username: string };
    onLogout: () => void;
    isOpen: boolean;
  }) => (
    <aside>
      Mobile drawer {currentUser.username}
      {isOpen ? (
        <button type="button" onClick={onLogout}>
          logout drawer
        </button>
      ) : null}
    </aside>
  ),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    className,
  }: {
    href: string;
    children: ReactNode;
    className?: string;
    onClick?: (event: MouseEvent<HTMLAnchorElement>) => void;
  }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

vi.mock("@/lib/use-presence-heartbeat", () => ({
  usePresenceHeartbeat: mocks.usePresenceHeartbeat,
}));

vi.mock("next/navigation", () => ({
  usePathname: () => mocks.pathname,
  useRouter: () => ({ push: mocks.push }),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
  clearStoredAccessToken: mocks.clearStoredAccessToken,
}));

vi.mock("@/lib/operational-search-api", () => ({
  searchOperational: mocks.searchOperational,
}));

function TestIcon({ className }: { className?: string }) {
  return <svg className={className} aria-hidden="true" />;
}

describe("AppShell", () => {
  beforeEach(() => {
    mocks.pathname = "/presenze/regole";
    mocks.push.mockReset();
    mocks.getStoredAccessToken.mockReset();
    mocks.clearStoredAccessToken.mockReset();
    mocks.searchOperational.mockReset();
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.searchOperational.mockResolvedValue({ query: "", items: [], total: 0, modules: [] });
    window.history.pushState(null, "", "/");
    Object.defineProperty(window, "scrollTo", { value: vi.fn(), writable: true });
  });

  test("renders shell and enables presence heartbeat for authenticated users", () => {
    const onLogout = vi.fn();

    render(
      <AppShell currentUser={{ username: "admin", role: "admin", enabled_modules: ["accessi"] } as never} onLogout={onLogout}>
        <Topbar pageTitle="Shell" />
        <div>contenuto</div>
      </AppShell>,
    );

    expect(mocks.usePresenceHeartbeat).toHaveBeenCalledWith({ enabled: true });
    expect(screen.getByText("Sidebar admin")).toBeInTheDocument();
    expect(screen.getByText("Mobile drawer admin")).toBeInTheDocument();
    expect(screen.getByText("contenuto")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Apri navigazione" }));
    expect(screen.getByRole("button", { name: "logout drawer" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "logout shell" }));
    expect(mocks.clearStoredAccessToken).toHaveBeenCalledTimes(1);
    expect(onLogout).toHaveBeenCalledTimes(1);
  });

  test("renders compact operational search in topbar and focuses it with keyboard shortcut", () => {
    render(
      <AppShell
        currentUser={{
          username: "admin",
          role: "viewer",
          enabled_modules: ["gis"],
        } as never}
      >
        <Topbar pageTitle="Catasto" breadcrumb="Particelle" />
      </AppShell>,
    );

    const input = screen.getByPlaceholderText("Cerca in GAIA…");
    expect(screen.getByText("/ Particelle")).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "k", ctrlKey: true });
    expect(document.activeElement).toBe(input);

    fireEvent.change(input, { target: { value: "GIS Platform · Catalogo" } });
    fireEvent.keyDown(input, { key: "Enter" });

    expect(mocks.push).toHaveBeenCalledWith("/gis/catalogo");
  });

  test("opens the extended results modal from compact operational search for multiple matches", () => {
    render(
      <AppShell
        currentUser={{
          username: "admin",
          role: "admin",
          enabled_modules: [],
        } as never}
      >
        <Topbar pageTitle="Ruolo" />
      </AppShell>,
    );

    const input = screen.getByPlaceholderText("Cerca in GAIA…");
    fireEvent.change(input, { target: { value: "dashboard" } });
    fireEvent.keyDown(input, { key: "Enter" });

    expect(mocks.push).not.toHaveBeenCalled();
    expect(screen.getByRole("heading", { name: "Risultati per “dashboard”" })).toBeInTheDocument();
  });

  test("does not render compact operational search when topbar is outside an authenticated shell", () => {
    render(<Topbar pageTitle="Standalone" />);

    expect(screen.getByText("Standalone")).toBeInTheDocument();
    expect(screen.queryByPlaceholderText("Cerca in GAIA…")).not.toBeInTheDocument();
  });

  test("renders children without sidebar when no user is available", () => {
    render(
      <AppShell currentUser={null}>
        <div>guest</div>
      </AppShell>,
    );

    expect(mocks.usePresenceHeartbeat).toHaveBeenCalledWith({ enabled: false });
    expect(screen.queryByText(/Sidebar/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Mobile drawer/)).not.toBeInTheDocument();
    expect(screen.getByText("guest")).toBeInTheDocument();
  });

  test("renders Presenze rules navigation entry", () => {
    render(<ModuleSidebar currentModuleKey="presenze" />);

    expect(screen.getByRole("link", { name: "Regole" })).toHaveAttribute("href", "/presenze/regole");
    expect(screen.getByRole("link", { name: "Squadre" })).toHaveAttribute("href", "/presenze/squadre");
    expect(screen.queryByRole("link", { name: "Sync" })).not.toBeInTheDocument();
  });

  test("renders Presenze INAZ Sync under Elaborazioni operations", () => {
    render(<ModuleSidebar currentModuleKey="elaborazioni" />);

    expect(screen.getByRole("link", { name: "Presenze INAZ Sync" })).toHaveAttribute("href", "/elaborazioni/presenze-sync");
  });

  test("renders Ruolo registered mail navigation entry", () => {
    mocks.pathname = "/ruolo/tributi";
    render(<ModuleSidebar currentModuleKey="ruolo" />);

    expect(screen.getByRole("link", { name: "Tributi" })).toHaveAttribute("href", "/ruolo/tributi");
    expect(screen.getByRole("link", { name: "Raccomandate" })).toHaveAttribute("href", "/ruolo/raccomandate");
  });

  test("keeps ruolo tributi and registered mails active states separated by route", async () => {
    mocks.pathname = "/ruolo/tributi";
    window.history.pushState(null, "", "/ruolo/tributi");
    const { rerender } = render(<ModuleSidebar currentModuleKey="ruolo" />);

    expect(screen.getByRole("link", { name: "Tributi" })).toHaveClass("bg-[#EAF3E8]");
    expect(screen.getByRole("link", { name: "Raccomandate" })).not.toHaveClass("bg-[#EAF3E8]");

    mocks.pathname = "/ruolo/raccomandate";
    window.history.pushState(null, "", "/ruolo/raccomandate");
    window.dispatchEvent(new PopStateEvent("popstate"));
    rerender(<ModuleSidebar currentModuleKey="ruolo" />);
    await waitFor(() => expect(screen.getByRole("link", { name: "Raccomandate" })).toHaveClass("bg-[#EAF3E8]"));
    expect(screen.getByRole("link", { name: "Tributi" })).not.toHaveClass("bg-[#EAF3E8]");
  });

  test("does not clear hash for modified nav clicks", async () => {
    mocks.pathname = "/hashless";
    window.history.pushState(null, "", "/hashless#old");
    render(<NavItem href="/hashless" icon={TestIcon} label="Hashless" />);

    const link = screen.getByRole("link", { name: "Hashless" });
    fireEvent.click(link, { ctrlKey: true });
    await new Promise((resolve) => window.setTimeout(resolve, 0));

    expect(link).toHaveAttribute("href", "/hashless");
  });

  test("covers nav item alias and click hash sync branches", async () => {
    mocks.pathname = "/legacy/section/detail";
    render(<NavItem href="/target" aliases={["/legacy/section#old", "/other"]} icon={TestIcon} label="Alias prefix" match="prefix" />);
    const aliasPrefix = screen.getByRole("link", { name: "Alias prefix" });
    expect(aliasPrefix).toHaveClass("bg-[#EAF3E8]");
    fireEvent.click(aliasPrefix);
    await new Promise((resolve) => window.setTimeout(resolve, 0));

    mocks.pathname = "/alias-exact";
    const { unmount } = render(<NavItem href="/target" aliases={["/alias-exact"]} icon={TestIcon} label="Alias exact" />);
    expect(screen.getByRole("link", { name: "Alias exact" })).toHaveClass("bg-[#EAF3E8]");
    unmount();

    mocks.pathname = "/hash-target";
    window.history.pushState(null, "", "/hash-target#required");
    render(<NavItem href="/hash-target#required" icon={TestIcon} label="Hash target" />);
    expect(screen.getByRole("link", { name: "Hash target" })).toHaveClass("bg-[#EAF3E8]");
  });

  test("covers module sidebar variants and permission branches", () => {
    const cases = [
      { key: "nas_control", expected: "Utenti" },
      { key: "me", expected: "Dotazioni" },
      { key: "catasto", expected: "GIS" },
      { key: "gis", expected: "GIS Catasto" },
      { key: "elaborazioni", expected: "Poste Online" },
      { key: "network", expected: "VPN / Proxy Bypass" },
      { key: "gaia", expected: "Utenti GAIA" },
      { key: "utenze", expected: "Import dati" },
      { key: "operazioni", expected: "Carte carburante" },
      { key: "riordino", expected: "Configurazione" },
      { key: "presenze", expected: "Banca ore" },
      { key: "organigramma", expected: "Albero & dettaglio" },
      { key: "wiki", expected: "Audit tool call" },
      { key: "inventory", expected: "Dashboard" },
    ] as const;

    cases.forEach(({ key, expected }) => {
      const { unmount } = render(<ModuleSidebar currentModuleKey={key} />);
      expect(screen.getByText(expected)).toBeInTheDocument();
      unmount();
    });
  });

  test("covers module sidebar admin and badge branches", () => {
    const { unmount: unmountNasWithoutAccess } = render(<ModuleSidebar currentModuleKey="nas_control" />);
    expect(screen.getByTitle("Accesso non abilitato")).toHaveTextContent("Utenti");
    unmountNasWithoutAccess();

    const { unmount: unmountNasWithAccess } = render(
      <ModuleSidebar currentModuleKey="nas_control" grantedSectionKeys={["accessi.users"]} reviewBadge={2} userBadge={3} />,
    );
    expect(screen.getByText("Utenti").closest("a")).toHaveAttribute("href", "/nas-control/users");
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("Review NAS").closest("a")).toHaveAttribute("href", "/nas-control/reviews");
    expect(screen.getByText("2")).toBeInTheDocument();
    unmountNasWithAccess();

    const { unmount: unmountNasWithAccessNoBadge } = render(
      <ModuleSidebar currentModuleKey="nas_control" grantedSectionKeys={["accessi.users"]} />,
    );
    expect(screen.getByText("Utenti").closest("a")).toHaveAttribute("href", "/nas-control/users");
    unmountNasWithAccessNoBadge();

    const { unmount: unmountCatastoAdmin } = render(<ModuleSidebar currentModuleKey="catasto" currentUserRole="admin" />);
    expect(screen.getByRole("link", { name: "Config. punti consegna" })).toHaveAttribute(
      "href",
      "/catasto/punti-consegna-configurazione",
    );
    unmountCatastoAdmin();

    const { unmount: unmountCatastoSuperAdmin } = render(<ModuleSidebar currentModuleKey="catasto" currentUserRole="super_admin" />);
    expect(screen.getByRole("link", { name: "Config. punti consegna" })).toBeInTheDocument();
    unmountCatastoSuperAdmin();

    const { unmount: unmountUtenzeAdmin } = render(<ModuleSidebar currentModuleKey="utenze" currentUserRole="admin" />);
    expect(screen.getByRole("link", { name: "Anomalie visure" })).toHaveAttribute("href", "/utenze/visure-routing-anomalies");
    expect(screen.getByRole("link", { name: "Config. ANPR" })).toHaveAttribute("href", "/anagrafica/anpr-config");
    unmountUtenzeAdmin();

    const { unmount: unmountUtenzeSuperAdmin } = render(<ModuleSidebar currentModuleKey="utenze" currentUserRole="super_admin" />);
    expect(screen.getByRole("link", { name: "Config. ANPR" })).toBeInTheDocument();
    unmountUtenzeSuperAdmin();

    const { unmount: unmountOrganigrammaManage } = render(
      <ModuleSidebar currentModuleKey="organigramma" grantedSectionKeys={["organigramma.read", "organigramma.manage"]} />,
    );
    expect(screen.getByRole("link", { name: "Eccezioni visibilità" })).toHaveAttribute("href", "/organigramma#override");
    unmountOrganigrammaManage();
  });
});
