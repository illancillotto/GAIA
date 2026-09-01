import { render, screen } from "@testing-library/react";
import type React from "react";
import { describe, expect, test, vi } from "vitest";

import ElaborazioniAutoSyncPage from "@/app/elaborazioni/autosync/page";

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({
    breadcrumbItems,
    children,
    description,
    title,
  }: {
    breadcrumbItems: Array<{ label: string; href?: string }>;
    children: React.ReactNode;
    description: string;
    title: string;
  }) => (
    <main data-breadcrumb={JSON.stringify(breadcrumbItems)} data-description={description} data-title={title}>
      {children}
    </main>
  ),
}));

vi.mock("@/components/elaborazioni/request-workspace", () => ({
  ElaborazioneRequestWorkspace: ({ initialMode }: { initialMode?: string }) => <div data-initial-mode={initialMode}>Monitor AutoSync</div>,
}));

describe("ElaborazioniAutoSyncPage", () => {
  test("renders the dedicated AutoSync monitor in the protected Elaborazioni shell", () => {
    render(<ElaborazioniAutoSyncPage />);

    expect(screen.getByRole("main")).toHaveAttribute("data-title", "Monitor AutoSync");
    expect(screen.getByRole("main")).toHaveAttribute(
      "data-breadcrumb",
      JSON.stringify([{ label: "Elaborazioni", href: "/elaborazioni" }, { label: "Monitor AutoSync" }]),
    );
    expect(screen.getByRole("main")).toHaveAttribute(
      "data-description",
      "Monitor operativo, stato e configurazione della sincronizzazione continua delle visure a ruolo.",
    );
    expect(screen.getByText("Monitor AutoSync")).toHaveAttribute("data-initial-mode", "autosync");
  });
});
