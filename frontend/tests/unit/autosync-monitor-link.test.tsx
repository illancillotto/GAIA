import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { AutoSyncMonitorLink } from "@/components/elaborazioni/autosync-monitor-link";

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: string; href: string }) => <a href={href} {...props}>{children}</a>,
}));

describe("AutoSyncMonitorLink", () => {
  test("links directly to the AutoSync activity monitor", () => {
    render(<AutoSyncMonitorLink />);

    const link = screen.getByRole("link", { name: "Apri monitor attività" });
    expect(link).toHaveAttribute("href", "/elaborazioni/autosync");
    expect(link).toHaveClass("btn-primary");
  });
});
