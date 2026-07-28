import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import RuoloRaccomandatePage from "@/app/ruolo/raccomandate/page";

vi.mock("@/components/ruolo/module-page", () => ({
  RuoloModulePage: ({ title, description, breadcrumb, requiredSection, children }: {
    title: string;
    description: string;
    breadcrumb?: string;
    requiredSection?: string;
    children: React.ReactNode;
  }) => (
    <main data-breadcrumb={breadcrumb} data-required-section={requiredSection}>
      <h1>{title}</h1>
      <p>{description}</p>
      {children}
    </main>
  ),
}));

vi.mock("@/components/ruolo/registered-mails-console", () => ({
  RegisteredMailsConsole: () => <section>Console raccomandate mock</section>,
}));

describe("RuoloRaccomandatePage", () => {
  test("renders registered mails as a standalone ruolo page", () => {
    render(<RuoloRaccomandatePage />);

    expect(screen.getByRole("heading", { name: "Raccomandate Poste Online" })).toBeInTheDocument();
    expect(screen.getByText("Console raccomandate mock")).toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveAttribute("data-breadcrumb", "Raccomandate");
    expect(screen.getByRole("main")).toHaveAttribute("data-required-section", "ruolo.tributi.view");
  });
});
