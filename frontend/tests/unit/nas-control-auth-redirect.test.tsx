import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import AccessiPage from "@/app/nas-control/page";

const replaceMock = vi.fn();
const mockGetStoredAccessToken = vi.fn();
const routerMock = { replace: replaceMock, push: vi.fn() };

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

vi.mock("@/components/layout/module-workspace-hero", () => ({
  ModuleWorkspaceHero: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  ModuleWorkspaceKpiRow: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  ModuleWorkspaceKpiTile: ({ label, value }: { label: string; value: ReactNode }) => <div>{label}: {value}</div>,
  ModuleWorkspaceNoticeCard: ({ title }: { title: string }) => <div>{title}</div>,
}));

vi.mock("@/components/ui/alert-banner", () => ({
  AlertBanner: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));

vi.mock("@/components/ui/sync-button", () => ({
  SyncButton: ({ label }: { label: string }) => <button type="button">{label}</button>,
}));

vi.mock("@/components/ui/icons", () => ({
  AlertTriangleIcon: () => null,
  ChevronRightIcon: () => null,
  FolderIcon: () => null,
  SearchIcon: () => null,
  UserIcon: () => null,
}));

vi.mock("@/lib/auth", () => ({
  clearStoredAccessToken: vi.fn(),
  getStoredAccessToken: () => mockGetStoredAccessToken(),
}));

vi.mock("@/lib/api", () => ({
  getCurrentUser: vi.fn(),
  getDashboardSummary: vi.fn(),
  getEffectivePermissions: vi.fn(),
  getMyPermissions: vi.fn(),
  getNasUsersForUsersSection: vi.fn(),
  getShares: vi.fn(),
  isAuthError: vi.fn(() => false),
}));

describe("NAS Control auth redirect", () => {
  beforeEach(() => {
    replaceMock.mockReset();
    mockGetStoredAccessToken.mockReset();
    mockGetStoredAccessToken.mockReturnValue(null);
  });

  test("renders access-required fallback for anonymous users instead of staying in session verification", async () => {
    render(<AccessiPage />);

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/login");
    });

    expect(screen.getByText("Accesso richiesto")).toBeInTheDocument();
    expect(screen.getByText("Accesso richiesto. Effettua il login.")).toBeInTheDocument();
    expect(screen.queryByText("Verifica sessione")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Vai al login" })).toHaveAttribute("href", "/login");
  });
});
