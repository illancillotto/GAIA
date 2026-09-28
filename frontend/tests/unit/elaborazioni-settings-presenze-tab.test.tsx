import { createElement } from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { ElaborazioniSettingsEntry } from "@/components/elaborazioni/elaborazioni-settings-entry";

const redirect = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({
  redirect,
}));

vi.mock("@/components/elaborazioni/settings-workspace", () => ({
  ElaborazioniSettingsWorkspace: () => createElement("div", null, "Workspace credenziali"),
}));

vi.mock("@/components/presenze/presenze-credential-vault", () => ({
  PresenzeCredentialVault: () => createElement("div", null, "Vault INAZ"),
}));

describe("elaborazioni credential routing", () => {
  test("keeps the settings page as a thin entry wrapper", async () => {
    const { default: ElaborazioniSettingsPage } = await import("@/app/elaborazioni/settings/page");
    const element = ElaborazioniSettingsPage();

    expect(element.type).toBe(ElaborazioniSettingsEntry);
    render(element);
    expect(screen.getByLabelText("Credenziali Presenze INAZ")).toBeInTheDocument();
    expect(screen.getByText("Vault INAZ")).toBeInTheDocument();
  });

  test("redirects the legacy presenze settings page to the elaborazioni vault", async () => {
    const { default: PresenzeSettingsPage } = await import("@/app/presenze/settings/page");

    PresenzeSettingsPage();

    expect(redirect).toHaveBeenCalledWith("/elaborazioni/settings#credenziali-inaz");
  });
});
