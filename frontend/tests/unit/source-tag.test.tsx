import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { SourceTag } from "@/components/ui/source-tag";

describe("SourceTag", () => {
  test("renders compact source string by default", () => {
    render(<SourceTag source="group:team-a:read:allow" />);
    expect(screen.getByText("group:team-a:read:allow")).toBeInTheDocument();
  });

  test("renders expanded multi-source tokens with highlight", () => {
    const source = "group:team-a:read:allow, group:team-b:write:allow";
    render(<SourceTag source={source} expanded />);

    expect(screen.getByText("group:team-a:read:allow")).toBeInTheDocument();
    expect(screen.getByText("group:team-b:write:allow")).toHaveClass("border-amber-200");
  });

  test("keeps compact view when expanded but source is not multi-source", () => {
    const { container } = render(<SourceTag source="user:alice:write:allow" expanded />);
    expect(screen.getByText("user:alice:write:allow")).toBeInTheDocument();
    expect(container.querySelector("div.inline-flex.max-w-full.flex-col")).toBeNull();
  });
});
