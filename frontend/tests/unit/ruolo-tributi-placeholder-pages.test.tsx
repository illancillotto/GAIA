import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import RuoloTributiImportPagamentiPage from "@/app/ruolo/tributi/import-pagamenti/page";
import RuoloTributiSollecitiPage from "@/app/ruolo/tributi/solleciti/page";

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({
    children,
    title,
  }: {
    children: React.ReactNode;
    title: string;
  }) => (
    <div>
      <h1>{title}</h1>
      {children}
    </div>
  ),
}));

describe("Ruolo tributi placeholder pages", () => {
  test("renders payment import placeholder", () => {
    render(<RuoloTributiImportPagamentiPage />);

    expect(screen.getByRole("heading", { name: "Import Pagamenti Tributi" })).toBeInTheDocument();
    expect(screen.getByText("Tracciato Excel CapaciTas in attesa")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Torna ai tributi" })).toHaveAttribute("href", "/ruolo/tributi");
  });

  test("renders reminders placeholder", () => {
    render(<RuoloTributiSollecitiPage />);

    expect(screen.getByRole("heading", { name: "Solleciti Tributi" })).toBeInTheDocument();
    expect(screen.getByText("Generazione solleciti da implementare")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Torna ai tributi" })).toHaveAttribute("href", "/ruolo/tributi");
  });
});
