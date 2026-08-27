import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceMiniStat,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";


describe("module workspace hero", () => {
  it("renders compact and regular heroes with optional regions", () => {
    const { rerender } = render(
      <ModuleWorkspaceHero badge="Badge" title="long_title_without_breaks" description="Description" />,
    );
    expect(screen.getByText("long_title_without_breaks")).toHaveClass("[overflow-wrap:anywhere]");
    expect(screen.queryByText("Action")).not.toBeInTheDocument();

    rerender(
      <ModuleWorkspaceHero
        compact
        badge="Badge"
        title="Title"
        description="Description"
        actions={<span>Action</span>}
      >
        <span>Children</span>
      </ModuleWorkspaceHero>,
    );
    expect(screen.getByText("Action").parentElement).toHaveClass("min-w-0", "gap-2");
    expect(screen.getByText("Children")).toBeInTheDocument();

    rerender(
      <ModuleWorkspaceHero badge="Badge" title="Title" description="Description" actions={<span>Regular action</span>}>
        <span>Regular children</span>
      </ModuleWorkspaceHero>,
    );
    expect(screen.getByText("Regular action").parentElement).toHaveClass("gap-3");
    expect(screen.getByText("Regular children").parentElement).toHaveClass("mt-6");
  });

  it("renders every mini-stat and notice tone in both density modes", () => {
    const { rerender } = render(
      <ModuleWorkspaceMiniStat eyebrow="State" value={3} description="Operation_without_breaks" />,
    );
    expect(screen.getByText("Operation_without_breaks")).toHaveClass("[overflow-wrap:anywhere]");

    rerender(<ModuleWorkspaceMiniStat compact tone="success" eyebrow="State" value="ok" description="Success" />);
    expect(screen.getByText("ok").parentElement).toHaveClass("bg-emerald-50/80", "p-3");

    rerender(<ModuleWorkspaceMiniStat tone="warning" eyebrow="State" value="warn" description="Warning" />);
    expect(screen.getByText("warn").parentElement).toHaveClass("bg-amber-50/80");

    const tones = ["neutral", "danger", "success", "warning", "info"] as const;
    for (const tone of tones) {
      rerender(
        <ModuleWorkspaceNoticeCard
          compact={tone === "info"}
          tone={tone}
          title={`Notice ${tone}`}
          description={`Description_${tone}`}
        />,
      );
      expect(screen.getByText(`Description_${tone}`)).toHaveClass("[overflow-wrap:anywhere]");
    }
  });

  it("renders KPI rows and every tile variant", () => {
    const { rerender } = render(
      <ModuleWorkspaceKpiRow>
        <span>KPI child</span>
      </ModuleWorkspaceKpiRow>,
    );
    expect(screen.getByText("KPI child").parentElement).toHaveClass("gap-2");

    rerender(
      <ModuleWorkspaceKpiRow compact>
        <span>Compact KPI</span>
      </ModuleWorkspaceKpiRow>,
    );
    expect(screen.getByText("Compact KPI").parentElement).toHaveClass("gap-1.5");

    const variants = ["default", "emerald", "amber"] as const;
    for (const variant of variants) {
      rerender(
        <ModuleWorkspaceKpiTile
          compact={variant === "amber"}
          variant={variant}
          label={`Label ${variant}`}
          value={`Value ${variant}`}
          hint={`Hint ${variant}`}
        />,
      );
      expect(screen.getByText(`Value ${variant}`)).toBeInTheDocument();
    }
  });
});
