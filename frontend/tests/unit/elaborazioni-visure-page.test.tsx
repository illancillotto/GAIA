import { render, screen } from "@testing-library/react";
import type React from "react";
import { describe, expect, test, vi } from "vitest";

import ElaborazioniVisurePage from "@/app/elaborazioni/visure/page";

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({
    breadcrumb,
    children,
    description,
    title,
  }: {
    breadcrumb: string;
    children: React.ReactNode;
    description: string;
    title: string;
  }) => (
    <main data-breadcrumb={breadcrumb} data-description={description} data-title={title}>
      {children}
    </main>
  ),
}));

vi.mock("@/app/elaborazioni/visure/visure-workspace-client", () => ({
  ElaborazioniVisureWorkspaceClient: () => <div>Workspace visure client</div>,
}));

describe("ElaborazioniVisurePage", () => {
  test("renders the protected visure workspace shell", () => {
    render(<ElaborazioniVisurePage />);

    expect(screen.getByRole("main")).toHaveAttribute("data-title", "Visure");
    expect(screen.getByRole("main")).toHaveAttribute("data-breadcrumb", "Elaborazioni / Visure");
    expect(screen.getByRole("main")).toHaveAttribute(
      "data-description",
      "Ingresso operativo per visure singole e monitor dei lotti recenti.",
    );
    expect(screen.getByText("Workspace visure client")).toBeInTheDocument();
  });
});
