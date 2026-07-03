import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { NetworkModulePage } from "@/components/network/network-module-page";
import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { AnagraficaModulePage } from "@/components/utenze/anagrafica-module-page";

const replaceMock = vi.fn();
const mockGetStoredAccessToken = vi.fn();
const routerMock = { replace: replaceMock };

vi.mock("next/link", () => ({
  default: ({ href, children, className }: { href: string; children: ReactNode; className?: string }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => routerMock,
}));

vi.mock("@/components/layout/app-shell", () => ({
  AppShell: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));

vi.mock("@/components/layout/topbar", () => ({
  Topbar: ({ pageTitle }: { pageTitle: string }) => <div>{pageTitle}</div>,
}));

vi.mock("@/lib/auth", () => ({
  clearStoredAccessToken: vi.fn(),
  getStoredAccessToken: () => mockGetStoredAccessToken(),
}));

vi.mock("@/lib/api", () => ({
  getCurrentUser: vi.fn(),
  getMyPermissions: vi.fn(),
  isAuthError: vi.fn(() => false),
}));

describe("module page auth redirect", () => {
  beforeEach(() => {
    replaceMock.mockReset();
    mockGetStoredAccessToken.mockReset();
    mockGetStoredAccessToken.mockReturnValue(null);
  });

  test.each([
    ["rete", NetworkModulePage],
    ["operazioni", OperazioniModulePage],
    ["utenze", AnagraficaModulePage],
  ])("redirects anonymous users on %s module pages", async (_label, Component) => {
    render(
      <Component title="Modulo GAIA" description="descrizione">
        {() => <div>contenuto privato</div>}
      </Component>,
    );

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/login");
    });

    expect(screen.getByText("Accesso richiesto")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Vai al login" })).toHaveAttribute("href", "/login");
    expect(screen.queryByText("contenuto privato")).not.toBeInTheDocument();
  });
});
