import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import {
  RecentBatchesOpenProvider,
  useRecentBatchesOpenHandler,
} from "@/components/elaborazioni/recent-batches-open-context";

function Probe() {
  const handler = useRecentBatchesOpenHandler();

  return (
    <button type="button" onClick={() => handler?.("batch-42")}>
      {handler ? "handler-ready" : "no-handler"}
    </button>
  );
}

describe("RecentBatchesOpenContext", () => {
  test("exposes onOpenBatch handler from provider", () => {
    const onOpenBatch = vi.fn();

    render(
      <RecentBatchesOpenProvider value={{ onOpenBatch }}>
        <Probe />
      </RecentBatchesOpenProvider>,
    );

    screen.getByRole("button", { name: "handler-ready" }).click();
    expect(onOpenBatch).toHaveBeenCalledWith("batch-42");
  });

  test("returns null outside provider", () => {
    render(<Probe />);
    expect(screen.getByRole("button", { name: "no-handler" })).toBeInTheDocument();
  });
});
