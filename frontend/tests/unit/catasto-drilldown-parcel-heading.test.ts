import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { createElement } from "react";
import { cleanup, queryAllByText, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { UtenzePanel } from "@/app/catasto/particelle/[id]/particella-related-sections";

const heading = "Utilizzatore / pagatore annualità";
const spec = readFileSync(resolve(process.cwd(), "tests/e2e/catasto-drilldown.spec.ts"), "utf8");

function renderPanel() {
  return render(createElement(UtenzePanel, {
    anno: 2026,
    capacitasLinkError: null,
    columns: [],
    isLoading: false,
    subjectLookupError: null,
    utenze: [],
    onAnnoChange: vi.fn(),
  }));
}

afterEach(() => {
  cleanup();
  document.body.innerHTML = "";
});

describe("Catasto parcel heading source/DOM contract, not native Playwright", () => {
  it("keeps a visibility assertion for the current annual-user section", () => {
    expect(spec.split(`await expect(workspace.getByText("${heading}")).toBeVisible();`)).toHaveLength(2);
    expect(spec).not.toContain('workspace.getByText("Ruoli tributo")');
    renderPanel();
    const matches = queryAllByText(document.body, heading);
    expect(matches).toHaveLength(1);
    expect(matches[0]).toBeVisible();
    expect(matches[0].closest("article")).toHaveTextContent("cat_utenze_irrigue");
    expect(matches[0].closest("article")).toHaveTextContent("Anno campagna");
  });

  it("demonstrates the old label misses the actual panel", () => {
    renderPanel();
    expect(queryAllByText(document.body, "Ruoli tributo")).toHaveLength(0);
    expect(queryAllByText(document.body, heading)).toHaveLength(1);
  });

  it("does not replace a missing current section with the obsolete title", () => {
    const view = renderPanel();
    view.unmount();
    document.body.innerHTML = "<p>Ruoli tributo</p>";
    expect(queryAllByText(document.body, heading)).toHaveLength(0);
  });

  it("does not accept a hidden annual-user heading as visible", () => {
    renderPanel();
    document.querySelector("article")!.hidden = true;
    const matches = queryAllByText(document.body, heading);
    expect(matches).toHaveLength(1);
    expect(matches[0]).not.toBeVisible();
  });

  it("retains duplicate matches rather than masking strict ambiguity", () => {
    renderPanel();
    renderPanel();
    expect(queryAllByText(document.body, heading)).toHaveLength(2);
  });
});
