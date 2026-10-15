import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { createElement } from "react";
import { cleanup, queryAllByText, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { MetricCard } from "@/components/ui/metric-card";

const labels = ["Particelle", "Utenze", "Importo 0648", "Importo 0985"];
const spec = readFileSync(resolve(process.cwd(), "tests/e2e/catasto-drilldown.spec.ts"), "utf8");

function scopeFor(label: string, source = spec) {
  const pattern = new RegExp(
    String.raw`await expect\(workspace(?:\.locator\("([^"]+)"\))?\.getByText\("${label}", \{ exact: true \}\)\)\.toBeVisible\(\);`,
    "g",
  );
  const matches = [...source.matchAll(pattern)];
  expect(matches).toHaveLength(1);
  return matches[0][1] ?? null;
}

function labelMatches(label: string, scope = scopeFor(label)) {
  const containers = scope ? [...document.querySelectorAll<HTMLElement>(scope)] : [document.body];
  return containers.flatMap((container) => queryAllByText(container, label, { exact: true }));
}

function renderLabel(label: string) {
  document.body.innerHTML = `<span>${label}</span><button>${label}</button>`;
  return render(createElement(MetricCard, { label, value: 0 }));
}

afterEach(() => {
  cleanup();
  document.body.innerHTML = "";
});

describe("Catasto KPI selector source and DOM contract, not native Playwright", () => {
  it.each(labels)("scopes %s to the real MetricCard label, excluding export and tab", (label) => {
    renderLabel(label);
    expect(scopeFor(label)).toBe(".metric-card");
    const matches = labelMatches(label);
    expect(matches).toHaveLength(1);
    expect(matches[0].tagName).toBe("P");
    expect(matches[0]).toBeVisible();
  });

  it.each(labels)("does not substitute export/tab text for a missing %s KPI", (label) => {
    const view = renderLabel(label);
    view.unmount();
    expect(queryAllByText(document.body, label, { exact: true })).toHaveLength(2);
    expect(labelMatches(label)).toHaveLength(0);
  });

  it.each(labels)("keeps hidden %s KPI labels detectable rather than accepting other text", (label) => {
    renderLabel(label);
    const card = document.querySelector<HTMLElement>(".metric-card")!;
    card.hidden = true;
    const matches = labelMatches(label);
    expect(matches).toHaveLength(1);
    expect(matches[0]).not.toBeVisible();
  });

  it.each(labels)("does not resolve duplicate %s KPI labels by position", (label) => {
    renderLabel(label);
    render(createElement(MetricCard, { label, value: 1 }));
    expect(labelMatches(label)).toHaveLength(2);
  });

  it("preserves exact text matching inside the KPI scope", () => {
    renderLabel("Particelle");
    render(createElement(MetricCard, { label: "Particelle totali", value: 1 }));
    expect(labelMatches("Particelle")).toHaveLength(1);
  });

  it("demonstrates the original unscoped Particelle collision in the DOM model", () => {
    renderLabel("Particelle");
    const original = spec.replaceAll('.locator(".metric-card")', "");
    expect(scopeFor("Particelle", original)).toBeNull();
    expect(labelMatches("Particelle", scopeFor("Particelle", original))).toHaveLength(3);
  });

  it("keeps both independent tab visibility assertions", () => {
    for (const name of ["Particelle", "Anomalie"]) {
      expect(spec).toContain(`await expect(workspace.getByRole("button", { name: "${name}" })).toBeVisible();`);
    }
  });
});
