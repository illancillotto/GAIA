import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { useGisSelection } from "@/hooks/useGisSelection";

const mocks = vi.hoisted(() => ({
  catastoGisSelect: vi.fn(),
}));

vi.mock("@/lib/api/catasto", () => ({
  catastoGisSelect: mocks.catastoGisSelect,
}));

function Probe({ token }: { token: string | null }) {
  const { result, isLoading, error, runSelection, clearSelection } = useGisSelection(token);

  return (
    <div>
      <span data-testid="loading">{String(isLoading)}</span>
      <span data-testid="error">{error ?? ""}</span>
      <span data-testid="count">{result?.n_particelle ?? 0}</span>
      <button type="button" onClick={() => void runSelection({ type: "Point", coordinates: [0, 0] })}>
        Run
      </button>
      <button type="button" onClick={clearSelection}>
        Clear
      </button>
    </div>
  );
}

describe("useGisSelection", () => {
  beforeEach(() => {
    mocks.catastoGisSelect.mockReset();
    mocks.catastoGisSelect.mockResolvedValue({
      n_particelle: 1,
      superficie_ha: 0.5,
      per_foglio: [],
      per_distretto: [],
      particelle: [],
      truncated: false,
    });
  });

  test("sets error when token is missing", async () => {
    render(<Probe token={null} />);

    await act(async () => {
      screen.getByRole("button", { name: "Run" }).click();
    });

    expect(screen.getByTestId("error")).toHaveTextContent("Sessione non disponibile");
    expect(mocks.catastoGisSelect).not.toHaveBeenCalled();
  });

  test("loads selection result and clears state", async () => {
    render(<Probe token="token" />);

    await act(async () => {
      screen.getByRole("button", { name: "Run" }).click();
    });

    await waitFor(() => {
      expect(screen.getByTestId("count")).toHaveTextContent("1");
    });
    expect(mocks.catastoGisSelect).toHaveBeenCalledWith(
      "token",
      { type: "Point", coordinates: [0, 0] },
      undefined,
    );

    await act(async () => {
      screen.getByRole("button", { name: "Clear" }).click();
    });

    expect(screen.getByTestId("count")).toHaveTextContent("0");
    expect(screen.getByTestId("error")).toHaveTextContent("");
  });

  test("stores API error message", async () => {
    mocks.catastoGisSelect.mockRejectedValue(new Error("Selezione fallita"));

    render(<Probe token="token" />);

    await act(async () => {
      screen.getByRole("button", { name: "Run" }).click();
    });

    await waitFor(() => {
      expect(screen.getByTestId("error")).toHaveTextContent("Selezione fallita");
    });
  });

  test("stores generic error for non-Error rejections", async () => {
    mocks.catastoGisSelect.mockRejectedValue("broken");

    render(<Probe token="token" />);

    await act(async () => {
      screen.getByRole("button", { name: "Run" }).click();
    });

    await waitFor(() => {
      expect(screen.getByTestId("error")).toHaveTextContent("Errore selezione spaziale");
    });
  });
});
