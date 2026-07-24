import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { AppShell } from "@/components/layout/app-shell";
import { ModuleSidebar } from "@/components/layout/module-sidebar";

const mocks = vi.hoisted(() => ({
  usePresenceHeartbeat: vi.fn(),
}));

vi.mock("@/components/layout/sidebar", () => ({
  Sidebar: ({ currentUser }: { currentUser: { username: string } }) => <aside>Sidebar {currentUser.username}</aside>,
}));

vi.mock("@/lib/use-presence-heartbeat", () => ({
  usePresenceHeartbeat: mocks.usePresenceHeartbeat,
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/presenze/regole",
}));

describe("AppShell", () => {
  test("renders shell and enables presence heartbeat for authenticated users", () => {
    render(
      <AppShell currentUser={{ username: "admin" } as never}>
        <div>contenuto</div>
      </AppShell>,
    );

    expect(mocks.usePresenceHeartbeat).toHaveBeenCalledWith({ enabled: true });
    expect(screen.getByText("Sidebar admin")).toBeInTheDocument();
    expect(screen.getByText("contenuto")).toBeInTheDocument();
  });

  test("renders children without sidebar when no user is available", () => {
    render(
      <AppShell currentUser={null}>
        <div>guest</div>
      </AppShell>,
    );

    expect(mocks.usePresenceHeartbeat).toHaveBeenCalledWith({ enabled: false });
    expect(screen.queryByText(/Sidebar/)).not.toBeInTheDocument();
    expect(screen.getByText("guest")).toBeInTheDocument();
  });

  test("renders Presenze rules navigation entry", () => {
    render(<ModuleSidebar currentModuleKey="presenze" />);

    expect(screen.getByRole("link", { name: "Regole" })).toHaveAttribute("href", "/presenze/regole");
    expect(screen.getByRole("link", { name: "Squadre" })).toHaveAttribute("href", "/presenze/squadre");
  });

  test("renders Ruolo registered mail navigation entry", () => {
    render(<ModuleSidebar currentModuleKey="ruolo" />);

    expect(screen.getByRole("link", { name: "Tributi" })).toHaveAttribute("href", "/ruolo/tributi");
    expect(screen.getByRole("link", { name: "Raccomandate" })).toHaveAttribute(
      "href",
      "/ruolo/tributi#raccomandate-poste",
    );
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
