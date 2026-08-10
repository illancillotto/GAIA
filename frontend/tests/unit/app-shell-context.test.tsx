import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { AppShellProvider, useAppShellContext } from "@/components/layout/app-shell-context";

function Probe() {
  const { currentUser, grantedSectionKeys, reviewBadge, userBadge, openMobileSidebar, onLogout } = useAppShellContext();

  return (
    <div>
      <span data-testid="username">{currentUser?.username ?? "none"}</span>
      <span data-testid="sections">{grantedSectionKeys.join(",")}</span>
      <span data-testid="review-badge">{reviewBadge}</span>
      <span data-testid="user-badge">{userBadge}</span>
      <button type="button" onClick={openMobileSidebar}>
        open probe
      </button>
      <button type="button" onClick={onLogout}>
        logout probe
      </button>
    </div>
  );
}

describe("AppShellContext", () => {
  test("provides current user and granted sections to consumers", () => {
    const onLogout = vi.fn();
    const openMobileSidebar = vi.fn();

    render(
      <AppShellProvider
        currentUser={{ id: 1, username: "admin", role: "admin", email: "admin@test" }}
        grantedSectionKeys={["catasto", "wiki"]}
        reviewBadge={4}
        userBadge={9}
        openMobileSidebar={openMobileSidebar}
        onLogout={onLogout}
      >
        <Probe />
      </AppShellProvider>,
    );

    expect(screen.getByTestId("username")).toHaveTextContent("admin");
    expect(screen.getByTestId("sections")).toHaveTextContent("catasto,wiki");
    expect(screen.getByTestId("review-badge")).toHaveTextContent("4");
    expect(screen.getByTestId("user-badge")).toHaveTextContent("9");
    screen.getByRole("button", { name: "open probe" }).click();
    screen.getByRole("button", { name: "logout probe" }).click();
    expect(openMobileSidebar).toHaveBeenCalledTimes(1);
    expect(onLogout).toHaveBeenCalledTimes(1);
  });

  test("returns default empty context outside provider", () => {
    render(<Probe />);
    expect(screen.getByTestId("username")).toHaveTextContent("none");
    expect(screen.getByTestId("sections")).toHaveTextContent("");
    expect(screen.getByTestId("review-badge")).toHaveTextContent("0");
    expect(screen.getByTestId("user-badge")).toHaveTextContent("0");
    screen.getByRole("button", { name: "open probe" }).click();
    screen.getByRole("button", { name: "logout probe" }).click();
  });
});
