import { createElement, useEffect } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import {
  ElaborazioniCredentialTabs,
  selectCredentialTab,
  useElaborazioniCredentialTab,
  type ElaborazioniCredentialTab,
} from "@/components/elaborazioni/elaborazioni-credential-tabs";

const redirect = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({
  redirect,
}));

vi.mock("@/components/presenze/presenze-credential-vault", () => ({
  PresenzeCredentialVault: () => createElement("div", null, "Vault INAZ"),
}));

function TabHarness() {
  const [activeTab, setActiveTab] = useElaborazioniCredentialTab();
  return <ElaborazioniCredentialTabs activeTab={activeTab} embedded={false} onChange={setActiveTab} />;
}

function HashHarness({ onReady }: { onReady: (tab: ElaborazioniCredentialTab) => void }) {
  const [activeTab] = useElaborazioniCredentialTab();
  useEffect(() => {
    onReady(activeTab);
  }, [activeTab, onReady]);
  return <span>{activeTab}</span>;
}

describe("Presenze INAZ credential tab", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", "/elaborazioni/settings");
  });

  test("shows the INAZ vault from the same tab strip as the other providers", () => {
    render(<TabHarness />);

    expect(screen.getByRole("button", { name: "SISTER" })).toHaveClass("bg-[#1D4E35]");
    expect(screen.queryByText("Vault INAZ")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Presenze INAZ" }));

    expect(screen.getByRole("button", { name: "Presenze INAZ" })).toHaveClass("bg-[#1D4E35]");
    expect(screen.getByText("Vault INAZ")).toBeInTheDocument();
    expect(window.location.hash).toBe("#credenziali-inaz");

    fireEvent.click(screen.getByRole("button", { name: "Capacitas" }));
    expect(screen.queryByText("Vault INAZ")).not.toBeInTheDocument();
    expect(window.location.hash).toBe("");
  });

  test("renders the compact tab strip and opens Presenze INAZ from the hash", async () => {
    window.history.replaceState(null, "", "/elaborazioni/settings#credenziali-inaz");
    const seen: ElaborazioniCredentialTab[] = [];
    render(
      <>
        <ElaborazioniCredentialTabs activeTab="presenze" embedded onChange={vi.fn()} />
        <HashHarness onReady={(tab) => seen.push(tab)} />
      </>,
    );

    expect(await screen.findByText("presenze")).toBeInTheDocument();
    expect(seen).toContain("presenze");
    expect(screen.getByText("Vault INAZ")).toBeInTheDocument();
  });

  test("updates the selected tab without leaving a hash for the other providers", () => {
    const onChange = vi.fn();
    selectCredentialTab("whitecompany", onChange);
    expect(onChange).toHaveBeenCalledWith("whitecompany");
    expect(window.location.hash).toBe("");
  });

  test("keeps the settings page on the elaborazioni workspace", async () => {
    const { default: ElaborazioniSettingsPage } = await import("@/app/elaborazioni/settings/page");
    const { ElaborazioniSettingsWorkspace } = await import("@/components/elaborazioni/settings-workspace");

    expect(ElaborazioniSettingsPage().type).toBe(ElaborazioniSettingsWorkspace);
  });

  test("redirects the legacy presenze settings page to the INAZ tab", async () => {
    const { default: PresenzeSettingsPage } = await import("@/app/presenze/settings/page");

    PresenzeSettingsPage();

    expect(redirect).toHaveBeenCalledWith("/elaborazioni/settings#credenziali-inaz");
  });
});
