import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { AppShellProvider, useAppShellContext } from "@/components/layout/app-shell-context";

function Probe() {
  const { currentUser, grantedSectionKeys } = useAppShellContext();

  return (
    <div>
      <span data-testid="username">{currentUser?.username ?? "none"}</span>
      <span data-testid="sections">{grantedSectionKeys.join(",")}</span>
    </div>
  );
}

describe("AppShellContext", () => {
  test("provides current user and granted sections to consumers", () => {
    render(
      <AppShellProvider
        currentUser={{ id: 1, username: "admin", role: "admin", email: "admin@test" }}
        grantedSectionKeys={["catasto", "wiki"]}
      >
        <Probe />
      </AppShellProvider>,
    );

    expect(screen.getByTestId("username")).toHaveTextContent("admin");
    expect(screen.getByTestId("sections")).toHaveTextContent("catasto,wiki");
  });

  test("returns default empty context outside provider", () => {
    render(<Probe />);
    expect(screen.getByTestId("username")).toHaveTextContent("none");
    expect(screen.getByTestId("sections")).toHaveTextContent("");
  });
});
