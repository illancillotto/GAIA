import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, test, vi } from "vitest";

import SisterPage, { metadata } from "@/app/elaborazioni/sister/page";

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ breadcrumbItems, children, description, title }: {
    breadcrumbItems: Array<{ label: string; href?: string }>;
    children: ReactNode;
    description: string;
    title: string;
  }) => <main data-breadcrumb={JSON.stringify(breadcrumbItems)} data-description={description} data-title={title}>{children}</main>,
}));
vi.mock("@/components/elaborazioni/sister-workspace", () => ({
  SisterWorkspace: ({ initialView }: { initialView: string }) => <p data-view={initialView}>Workspace SISTER</p>,
}));

describe("SisterPage", () => {
  test.each([
    [undefined, "operations"],
    [Promise.resolve({ view: "unknown" }), "operations"],
    [Promise.resolve({ view: "health" }), "health"],
  ])("renders the unified workspace with the selected view", async (searchParams, expectedView) => {
    render(await SisterPage({ searchParams }));
    expect(screen.getByRole("main")).toHaveAttribute("data-title", "SISTER / Visure");
    expect(screen.getByRole("main")).toHaveAttribute(
      "data-breadcrumb",
      JSON.stringify([{ label: "Elaborazioni", href: "/elaborazioni" }, { label: "SISTER / Visure" }]),
    );
    expect(screen.getByText("Workspace SISTER")).toHaveAttribute("data-view", expectedView);
    expect(metadata.title).toContain("SISTER");
  });
});
