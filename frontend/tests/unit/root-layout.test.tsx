import { renderToStaticMarkup } from "react-dom/server";
import { expect, it, vi } from "vitest";
import type { ReactNode } from "react";
import RootLayout, { metadata } from "@/app/layout";

vi.mock("@/features/wiki/WikiWidget", () => ({ WikiWidget: () => <div>Wiki assistente</div> }));
vi.mock("@/components/security/https-access-guide", () => ({ HttpsAccessGuide: ({ children }: { children: ReactNode }) => <>{children}</> }));
vi.mock("@/components/elaborazioni/home-sync-alerts", () => ({ HomeSyncAlerts: () => <aside>Monitor home</aside> }));

it("monta il monitor home insieme al contenuto e agli strumenti globali", () => {
  const html = renderToStaticMarkup(<RootLayout><main>Home GAIA</main></RootLayout>);
  expect(html).toContain('<html lang="it">');
  expect(html).toContain("Home GAIA");
  expect(html).toContain("Wiki assistente");
  expect(html).toContain("Monitor home");
  expect(metadata.title).toContain("GAIA");
});
