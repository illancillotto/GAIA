import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { AppShell } from "@/components/layout/app-shell";

const mocks = vi.hoisted(() => ({
  usePresenceHeartbeat: vi.fn(),
}));

vi.mock("@/components/layout/sidebar", () => ({
  Sidebar: ({ currentUser }: { currentUser: { username: string } }) => <aside>Sidebar {currentUser.username}</aside>,
}));

vi.mock("@/lib/use-presence-heartbeat", () => ({
  usePresenceHeartbeat: mocks.usePresenceHeartbeat,
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
});
