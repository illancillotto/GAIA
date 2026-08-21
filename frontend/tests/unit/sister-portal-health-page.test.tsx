import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, test, vi } from "vitest";

import SisterPortalHealthPage, { metadata } from "@/app/elaborazioni/portal-health/page";


vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children, title }: { children: ReactNode; title: string }) => (
    <section><h1>{title}</h1>{children}</section>
  ),
}));
vi.mock("@/components/elaborazioni/sister-portal-health-workspace", () => ({
  SisterPortalHealthWorkspace: () => <p>workspace</p>,
}));


describe("SisterPortalHealthPage", () => {
  test("renders the protected portal health workspace", () => {
    render(<SisterPortalHealthPage />);
    expect(screen.getByRole("heading", { name: "Stato portale SISTER" })).toBeInTheDocument();
    expect(screen.getByText("workspace")).toBeInTheDocument();
    expect(metadata.title).toContain("SISTER");
  });
});
