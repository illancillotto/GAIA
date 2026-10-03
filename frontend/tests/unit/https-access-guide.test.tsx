import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import RootLayout, { metadata } from "@/app/layout";
import { HttpsAccessGuide } from "@/components/security/https-access-guide";

const mocks = vi.hoisted(() => ({ pathname: "/" as string | null }));
vi.mock("next/navigation", () => ({ usePathname: () => mocks.pathname }));
vi.mock("@/features/wiki/WikiWidget", () => ({ WikiWidget: () => <aside>Wiki legacy</aside> }));

beforeEach(() => { mocks.pathname = "/"; });
afterEach(cleanup);

test.each(["/", "/login"])("shows the guide without authentication at %s", (pathname) => {
  mocks.pathname = pathname;
  const { container } = render(<HttpsAccessGuide />);
  const summary = screen.getByText("Accedere a GAIA in HTTPS · Windows, macOS e Linux");
  const details = container.querySelector("details")!;
  expect(details.open).toBe(false);
  fireEvent.click(summary);
  expect(details.open).toBe(true);
  expect(screen.getByRole("heading", { name: "Windows" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "macOS" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Linux" })).toBeInTheDocument();
  expect(container.querySelectorAll("article ol li")).toHaveLength(9);
  expect(screen.getByText(/EXE amd64/)).toBeInTheDocument();
  expect(screen.getByText(/Installa-CA-macOS.command/)).toBeInTheDocument();
  expect(screen.getByText(/bash installa-ca-linux.sh --verify/)).toBeInTheDocument();
  fireEvent.click(summary);
  expect(details.open).toBe(false);
});

test.each(["/wiki/mcp", "/me", "/auth/reset-password/token", null])("does not alter other routes (%s)", (pathname) => {
  mocks.pathname = pathname;
  const { container } = render(<HttpsAccessGuide />);
  expect(container).toBeEmptyDOMElement();
});

test("keeps unapproved installers unavailable and explains safe login", () => {
  const { container } = render(<HttpsAccessGuide />);
  expect(screen.getByRole("heading", { name: "Attivazione HTTPS in preparazione" })).toBeInTheDocument();
  expect(screen.getByText(/pacchetti con la CA Kiosk sono sospesi/)).toBeInTheDocument();
  expect(screen.getByText(/solo dopo la conferma del CED/)).toBeInTheDocument();
  expect(screen.getByText(/non scegliere «Procedi comunque»/)).toBeInTheDocument();
  expect(screen.getByText(/sessioni HTTP e HTTPS sono separate/)).toBeInTheDocument();
  expect(screen.getByText(/installare la CA non configura il DNS/)).toBeInTheDocument();
  expect(container.querySelector("a, input, form, button")).toBeNull();
  expect(container.textContent).not.toContain("84420F2555");
});

test("root layout retains page content, Italian language and legacy Wiki widget", () => {
  const markup = renderToStaticMarkup(<RootLayout><main>Contenuto home</main></RootLayout>);
  expect(markup).toContain('lang="it"');
  expect(markup).toContain("Contenuto home");
  expect(markup).toContain("Guida accesso HTTPS");
  expect(markup).toContain("Wiki legacy");
  expect(metadata.title).toBe("GAIA | Gestione Apparati Informativi");
});

test("layout guide preserves children on routes without HTTPS help", () => {
  mocks.pathname = "/wiki/mcp";
  render(<HttpsAccessGuide><main>Contenuto applicativo</main></HttpsAccessGuide>);
  expect(screen.getByRole("main")).toHaveTextContent("Contenuto applicativo");
  expect(screen.queryByRole("region", { name: "Guida accesso HTTPS" })).not.toBeInTheDocument();
});
