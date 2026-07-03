import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, test, vi } from "vitest";

import { RuoloModulePage } from "@/components/ruolo/module-page";

const protectedPageSpy = vi.fn();

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({
    children,
    title,
    description,
    requiredModule,
  }: {
    children: ReactNode;
    title: string;
    description: string;
    requiredModule?: string;
  }) => {
    protectedPageSpy({ title, description, requiredModule });
    return (
      <div data-testid="protected-page">
        <h1>{title}</h1>
        {children}
      </div>
    );
  },
}));

describe("RuoloModulePage", () => {
  test("keeps using ProtectedPage even when the route is embedded", () => {
    window.history.replaceState({}, "", "/ruolo/avvisi?embedded=1");

    render(
      <RuoloModulePage title="Avvisi Ruolo" description="Elenco avvisi">
        <div>contenuto ruolo</div>
      </RuoloModulePage>,
    );

    expect(screen.getByTestId("protected-page")).toBeInTheDocument();
    expect(screen.getByText("contenuto ruolo")).toBeInTheDocument();
    expect(protectedPageSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "Avvisi Ruolo",
        description: "Elenco avvisi",
        requiredModule: "ruolo",
      }),
    );
  });
});
