import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { FilterPillGroup } from "@/components/network/filter-pill-group";
import { NetworkStatusBadge } from "@/components/network/network-status-badge";
import { NetworkTrackToggle } from "@/components/network/network-track-toggle";

describe("NetworkStatusBadge", () => {
  test("maps known statuses and replaces underscores", () => {
    render(<NetworkStatusBadge status="online" />);
    expect(screen.getByText("online")).toBeInTheDocument();

    render(<NetworkStatusBadge status="in_progress" />);
    expect(screen.getByText("in progress")).toBeInTheDocument();
  });
});

describe("FilterPillGroup", () => {
  test("highlights active option and calls onChange", () => {
    const onChange = vi.fn();
    render(
      <FilterPillGroup
        options={[
          { value: "all", label: "Tutti" },
          { value: "online", label: "Online" },
        ]}
        value="all"
        onChange={onChange}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Online" }));
    expect(onChange).toHaveBeenCalledWith("online");
    expect(screen.getByRole("button", { name: "Tutti" })).toHaveClass("border-emerald-200");
  });
});

describe("NetworkTrackToggle", () => {
  test("renders tracked and busy states", () => {
    const onClick = vi.fn();
    const { rerender } = render(<NetworkTrackToggle tracked={false} onClick={onClick} label="Traccia rete" />);

    fireEvent.click(screen.getByRole("button", { name: "Traccia rete" }));
    expect(onClick).toHaveBeenCalledTimes(1);

    rerender(<NetworkTrackToggle tracked busy onClick={onClick} compact disabled />);
    expect(screen.getByRole("button")).toBeDisabled();
    expect(screen.getByText("...")).toBeInTheDocument();
  });

  test("uses default tracked label when label is empty", () => {
    render(<NetworkTrackToggle tracked onClick={vi.fn()} label="" />);
    expect(screen.getByText("Tracciato")).toBeInTheDocument();
  });

  test("uses default untracked label", () => {
    render(<NetworkTrackToggle tracked={false} onClick={vi.fn()} />);
    expect(screen.getByText("Traccia")).toBeInTheDocument();
  });
});
