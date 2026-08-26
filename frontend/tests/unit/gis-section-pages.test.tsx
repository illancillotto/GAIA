import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, test, vi } from "vitest";

import GisPlatformPage from "@/app/gis/page";
import GisAdministrationPage from "@/app/gis/amministrazione/page";
import GisToolsPage from "@/app/gis/strumenti/page";

const { redirectMock } = vi.hoisted(() => ({ redirectMock: vi.fn() }));

vi.mock("next/navigation", () => ({ redirect: redirectMock }));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ title, requiredModule, requiredRoles, children }: { title: string; requiredModule: string; requiredRoles?: string[]; children: ReactNode }) => (
    <section data-testid={title} data-module={requiredModule} data-roles={requiredRoles?.join(",") ?? ""}>{children}</section>
  ),
}));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: () => "token" }));
vi.mock("@/app/gis/amministrazione/administration-workspace", () => ({
  GisAdministrationWorkspace: ({ token }: { token: string }) => <div>Admin workspace {token}</div>,
}));
vi.mock("@/app/gis/strumenti/tools-workspace", () => ({
  GisToolsWorkspace: ({ token }: { token: string }) => <div>Tools workspace {token}</div>,
}));

describe("GIS section pages", () => {
  test("redirects the GIS module root to the catalog", () => {
    GisPlatformPage();
    expect(redirectMock).toHaveBeenCalledWith("/gis/catalogo");
  });

  test("protects tools with the GIS module", () => {
    render(<GisToolsPage />);
    expect(screen.getByTestId("Strumenti GIS")).toHaveAttribute("data-module", "gis");
    expect(screen.getByText("Tools workspace token").parentElement).toHaveClass("gis-touch-targets");
  });

  test("reserves administration to administrators", () => {
    render(<GisAdministrationPage />);
    expect(screen.getByTestId("Amministrazione GIS")).toHaveAttribute("data-module", "gis");
    expect(screen.getByTestId("Amministrazione GIS")).toHaveAttribute("data-roles", "admin,super_admin");
    expect(screen.getByText("Admin workspace token").parentElement).toHaveClass("gis-touch-targets");
  });
});
