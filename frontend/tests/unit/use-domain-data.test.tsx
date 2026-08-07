import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { useDomainData } from "@/hooks/use-domain-data";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  getNasUsers: vi.fn(),
  getNasGroups: vi.fn(),
  getShares: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  getNasUsers: mocks.getNasUsers,
  getNasGroups: mocks.getNasGroups,
  getShares: mocks.getShares,
}));

function Probe() {
  const { users, groups, shares, error } = useDomainData();

  return (
    <div>
      <span data-testid="users">{users.length}</span>
      <span data-testid="groups">{groups.length}</span>
      <span data-testid="shares">{shares.length}</span>
      <span data-testid="error">{error ?? ""}</span>
    </div>
  );
}

describe("useDomainData", () => {
  beforeEach(() => {
    mocks.getStoredAccessToken.mockReset();
    mocks.getNasUsers.mockReset();
    mocks.getNasGroups.mockReset();
    mocks.getShares.mockReset();
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getNasUsers.mockResolvedValue([{ id: 1 }]);
    mocks.getNasGroups.mockResolvedValue([{ id: 2 }, { id: 3 }]);
    mocks.getShares.mockResolvedValue([]);
  });

  test("loads users, groups, and shares when token exists", async () => {
    render(<Probe />);

    await waitFor(() => {
      expect(screen.getByTestId("users")).toHaveTextContent("1");
      expect(screen.getByTestId("groups")).toHaveTextContent("2");
      expect(screen.getByTestId("shares")).toHaveTextContent("0");
    });
  });

  test("skips loading when token is missing", async () => {
    mocks.getStoredAccessToken.mockReturnValue(null);

    render(<Probe />);

    await waitFor(() => {
      expect(mocks.getNasUsers).not.toHaveBeenCalled();
    });
    expect(screen.getByTestId("users")).toHaveTextContent("0");
  });

  test("stores error message when loading fails", async () => {
    mocks.getNasUsers.mockRejectedValue(new Error("Dominio non disponibile"));

    render(<Probe />);

    await waitFor(() => {
      expect(screen.getByTestId("error")).toHaveTextContent("Dominio non disponibile");
    });
  });

  test("stores generic error for non-Error rejections", async () => {
    mocks.getShares.mockRejectedValue("broken");

    render(<Probe />);

    await waitFor(() => {
      expect(screen.getByTestId("error")).toHaveTextContent("Errore caricamento dati dominio");
    });
  });
});
