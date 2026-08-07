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
      action_label: null,
      visible: true,
    });

    await vi.advanceTimersByTimeAsync(60_000);

    expect(mocks.sendPresenceHeartbeat).toHaveBeenCalledTimes(2);
  });

  test("normalizes empty pathname to home metadata", async () => {
    mocks.usePathname.mockReturnValue("");

    render(<Probe />);
    await vi.advanceTimersByTimeAsync(1);

    expect(mocks.sendPresenceHeartbeat).toHaveBeenCalledWith(
      "token",
      expect.objectContaining({
        path: "/",
        route_label: "Home",
        module_key: "home",
      }),
    );
  });

  test("skips heartbeat when disabled or token is missing", async () => {
    function DisabledProbe() {
      usePresenceHeartbeat({ enabled: false });
      return null;
    }

    render(<DisabledProbe />);
    await vi.advanceTimersByTimeAsync(1);
    expect(mocks.sendPresenceHeartbeat).not.toHaveBeenCalled();

    mocks.getStoredAccessToken.mockReturnValue(null);
    render(<Probe />);
    await vi.advanceTimersByTimeAsync(1);
    expect(mocks.sendPresenceHeartbeat).not.toHaveBeenCalled();
  });

  test("does not heartbeat on hidden tabs and reacts to visibility and action events", async () => {
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "hidden",
    });

    render(<Probe />);
    await vi.advanceTimersByTimeAsync(1);
    expect(mocks.sendPresenceHeartbeat).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(60_000);
    expect(mocks.sendPresenceHeartbeat).toHaveBeenCalledTimes(1);

    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "visible",
    });
    document.dispatchEvent(new Event("visibilitychange"));
    await vi.advanceTimersByTimeAsync(1);
    expect(mocks.sendPresenceHeartbeat).toHaveBeenCalledTimes(2);

    window.dispatchEvent(new Event("gaia-presence-action-changed"));
    await vi.advanceTimersByTimeAsync(1);
    expect(mocks.sendPresenceHeartbeat).toHaveBeenCalledTimes(3);
  });

  test("swallows heartbeat errors outside test environment", async () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    mocks.sendPresenceHeartbeat.mockRejectedValueOnce(new Error("network down"));
    vi.stubEnv("NODE_ENV", "development");

    render(<Probe />);
    await vi.advanceTimersByTimeAsync(1);

    expect(warnSpy).toHaveBeenCalledWith("Presence heartbeat failed", expect.any(Error));
    warnSpy.mockRestore();
    vi.unstubAllEnvs();
  });

  test("swallows heartbeat errors silently in test environment", async () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    mocks.sendPresenceHeartbeat.mockRejectedValueOnce(new Error("network down"));
    vi.stubEnv("NODE_ENV", "test");

    render(<Probe />);
    await vi.advanceTimersByTimeAsync(1);

    expect(warnSpy).not.toHaveBeenCalled();
    warnSpy.mockRestore();
    vi.unstubAllEnvs();
  });
});
