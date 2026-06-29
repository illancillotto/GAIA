import { render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { usePresenceHeartbeat } from "@/lib/use-presence-heartbeat";

const mocks = vi.hoisted(() => ({
  sendPresenceHeartbeat: vi.fn(),
  getStoredAccessToken: vi.fn(),
  usePathname: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: mocks.usePathname,
}));

vi.mock("@/lib/api", () => ({
  sendPresenceHeartbeat: mocks.sendPresenceHeartbeat,
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

function Probe() {
  usePresenceHeartbeat({ enabled: true });
  return null;
}

describe("usePresenceHeartbeat", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mocks.sendPresenceHeartbeat.mockReset();
    mocks.getStoredAccessToken.mockReset();
    mocks.usePathname.mockReset();
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.sendPresenceHeartbeat.mockResolvedValue({ ok: true, last_seen_at: "2026-06-29T10:00:00Z" });
    mocks.usePathname.mockReturnValue("/gaia/users/attivita");
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "visible",
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test("sends heartbeat immediately and on interval with resolved route metadata", async () => {
    render(<Probe />);

    await vi.advanceTimersByTimeAsync(1);

    expect(mocks.sendPresenceHeartbeat).toHaveBeenCalledWith("token", {
      path: "/gaia/users/attivita",
      route_label: "Utenti GAIA / Attivita utenti",
      module_key: "gaia",
      visible: true,
    });

    await vi.advanceTimersByTimeAsync(60_000);

    expect(mocks.sendPresenceHeartbeat).toHaveBeenCalledTimes(2);
  });
});
