import { act, fireEvent, render, screen } from "@testing-library/react";
import type { ComponentProps, SVGProps } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { NavItem } from "@/components/layout/nav-item";

const state = vi.hoisted(() => ({ pathname: "/target" }));

vi.mock("next/navigation", () => ({ usePathname: () => state.pathname }));
vi.mock("next/link", () => ({
  default: ({ onClick, ...props }: ComponentProps<"a">) => (
    <a {...props} onClick={(event) => {
      onClick?.(event);
      event.preventDefault();
    }} />
  ),
}));

function TestIcon(props: SVGProps<SVGSVGElement>) {
  return <svg {...props} data-testid="icon" />;
}

beforeEach(() => {
  vi.useFakeTimers();
  state.pathname = "/target";
  window.history.replaceState(null, "", "/target");
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
});

afterEach(() => {
  vi.runOnlyPendingTimers();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("navigation path and hash matching", () => {
  test.each([
    ["/target", "/target", [], "exact", true],
    ["/target/detail", "/target", [], "exact", false],
    ["/target", "/target", [], "prefix", true],
    ["/target/detail", "/target", [], "prefix", true],
    ["/target-other", "/target", [], "prefix", false],
    ["/legacy", "/target", ["/legacy#old"], "exact", true],
    ["/legacy/detail", "/target", ["/other", "/legacy#old"], "prefix", true],
    ["/legacy", "/target", ["/legacy"], "prefix", true],
    ["/else", "/target", ["/other"], "prefix", false],
    ["/target", "/target?query=1", [], "exact", false],
  ] as const)("matches %s with %s", (pathname, href, aliases, match, active) => {
    state.pathname = pathname;
    render(<NavItem href={href} aliases={[...aliases]} match={match} icon={TestIcon} label="Target" />);
    const link = screen.getByRole("link");
    expect(link.classList.contains("bg-[#EAF3E8]")).toBe(active);
    expect(link).toHaveAttribute("href", href);
    expect(screen.getByTestId("icon")).toHaveClass("h-4");
  });

  test("requires href hash before inactive hash and responds to both events", () => {
    window.history.replaceState(null, "", "/target#required");
    const { unmount } = render(<NavItem href="/target#required" inactiveWhenHash="#required" icon={TestIcon} label="Target" />);
    const link = screen.getByRole("link");
    expect(link).toHaveClass("bg-[#EAF3E8]");
    window.history.replaceState(null, "", "/target#other");
    fireEvent(window, new HashChangeEvent("hashchange"));
    expect(link).not.toHaveClass("bg-[#EAF3E8]");
    window.history.replaceState(null, "", "/target#required");
    fireEvent(window, new PopStateEvent("popstate"));
    expect(link).toHaveClass("bg-[#EAF3E8]");
    fireEvent.click(link);
    act(() => vi.runOnlyPendingTimers());
    const remove = vi.spyOn(window, "removeEventListener");
    unmount();
    expect(remove).toHaveBeenCalledWith("hashchange", expect.any(Function));
    expect(remove).toHaveBeenCalledWith("popstate", expect.any(Function));
  });

  test("inactive hash applies only on matching path", () => {
    window.history.replaceState(null, "", "/target#inactive");
    const { rerender } = render(<NavItem href="/target" inactiveWhenHash="#inactive" icon={TestIcon} label="Target" />);
    expect(screen.getByRole("link")).not.toHaveClass("bg-[#EAF3E8]");
    window.history.replaceState(null, "", "/target#other");
    fireEvent(window, new HashChangeEvent("hashchange"));
    expect(screen.getByRole("link")).toHaveClass("bg-[#EAF3E8]");
    state.pathname = "/else";
    rerender(<NavItem href="/target" inactiveWhenHash="#inactive" icon={TestIcon} label="Target" />);
    expect(screen.getByRole("link")).not.toHaveClass("bg-[#EAF3E8]");
  });

  test("required hash never activates another path", () => {
    state.pathname = "/else";
    window.history.replaceState(null, "", "/else#required");
    render(<NavItem href="/target#required" icon={TestIcon} label="Target" />);
    expect(screen.getByRole("link")).not.toHaveClass("bg-[#EAF3E8]");
  });
});

describe("navigation rendering and click contract", () => {
  test("preserves active and disabled precedence through rerenders", () => {
    const props = { href: "/target", icon: TestIcon, label: "Target", badge: 2 };
    const { rerender } = render(<NavItem {...props} disabled />);
    expect(screen.getByTitle("Accesso non abilitato")).toHaveClass("cursor-not-allowed");
    expect(screen.getByTitle("Accesso non abilitato")).not.toHaveClass("bg-[#EAF3E8]");
    rerender(<NavItem {...props} />);
    expect(screen.getByRole("link")).toHaveClass("bg-[#EAF3E8]");
    expect(screen.queryByTitle("Accesso non abilitato")).not.toBeInTheDocument();
    state.pathname = "/else";
    rerender(<NavItem {...props} badgeVariant="danger" />);
    expect(screen.getByRole("link")).toHaveClass("text-gray-500");
    expect(screen.getByText("2")).toHaveClass("bg-red-50");
    expect(screen.getAllByTestId("icon")).toHaveLength(1);
  });

  test("clears same query hash without changing search or scheduling fallback", () => {
    window.history.replaceState(null, "", "/target?value=1#old");
    render(<NavItem href="/target?value=1" icon={TestIcon} label="Target" />);
    fireEvent.click(screen.getByRole("link"));
    expect(window.location.search).toBe("?value=1");
    expect(window.location.hash).toBe("");
    expect(vi.getTimerCount()).toBe(0);
  });

  test("preserves history scroll and popstate effect order", () => {
    window.history.replaceState(null, "", "/target#old");
    render(<NavItem href="/target" icon={TestIcon} label="Target" />);
    const push = window.history.pushState.bind(window.history);
    const effects: string[] = [];
    vi.spyOn(window.history, "pushState").mockImplementation((...args) => {
      effects.push("history");
      push(...args);
    });
    vi.mocked(window.scrollTo).mockImplementation(() => { effects.push("scroll"); });
    const listener = () => { effects.push("popstate"); };
    window.addEventListener("popstate", listener);
    fireEvent.click(screen.getByRole("link"));
    expect(effects).toEqual(["history", "scroll", "popstate"]);
    window.removeEventListener("popstate", listener);
  });

  test.each(["danger", "warning"] as const)("renders zero badge with %s style and disabled content", (badgeVariant) => {
    const { rerender } = render(<NavItem href="/target" icon={TestIcon} label="Target" badge={0} badgeVariant={badgeVariant} />);
    expect(screen.getByText("0")).toHaveClass(badgeVariant === "danger" ? "bg-red-50" : "bg-amber-50");
    rerender(<NavItem href="/target" icon={TestIcon} label="Target" disabled badge={0} />);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByTitle("Accesso non abilitato")).toHaveAttribute("aria-disabled", "true");
  });

  test.each([false, true])("clears only same path hash even if scroll throws=%s", (throws) => {
    if (throws) vi.mocked(window.scrollTo).mockImplementation(() => { throw new Error("unsupported"); });
    window.history.replaceState(null, "", "/target#old");
    render(<NavItem href="/target" icon={TestIcon} label="Target" />);
    const listener = vi.fn();
    window.addEventListener("popstate", listener);
    fireEvent.click(screen.getByRole("link"));
    expect(window.location.hash).toBe("");
    expect(window.scrollTo).toHaveBeenCalledWith({ top: 0, left: 0 });
    expect(listener).toHaveBeenCalledOnce();
    window.removeEventListener("popstate", listener);
  });

  test.each([
    { metaKey: true }, { ctrlKey: true }, { shiftKey: true }, { altKey: true }, { button: 1 },
  ])("does not intercept modified clicks %j", (options) => {
    window.history.replaceState(null, "", "/target#old");
    render(<NavItem href="/target" icon={TestIcon} label="Target" />);
    fireEvent.click(screen.getByRole("link"), options);
    expect(window.location.hash).toBe("#old");
    expect(window.scrollTo).not.toHaveBeenCalled();
    act(() => vi.runOnlyPendingTimers());
  });

  test("does not intercept already prevented click", () => {
    window.history.replaceState(null, "", "/target#old");
    render(<NavItem href="/target" icon={TestIcon} label="Target" />);
    const link = screen.getByRole("link");
    link.addEventListener("click", (event) => event.preventDefault());
    fireEvent.click(link);
    expect(window.location.hash).toBe("#old");
    expect(window.scrollTo).not.toHaveBeenCalled();
    act(() => vi.runOnlyPendingTimers());
  });

  test.each(["/else#old", "/target?different=1#old", "/target"])("leaves navigation at %s to Link", (location) => {
    window.history.replaceState(null, "", location);
    render(<NavItem href="/target" icon={TestIcon} label="Target" />);
    fireEvent.click(screen.getByRole("link"));
    expect(window.scrollTo).not.toHaveBeenCalled();
    act(() => vi.runOnlyPendingTimers());
  });
});
