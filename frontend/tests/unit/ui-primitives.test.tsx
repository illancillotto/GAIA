import { fireEvent, render, screen } from "@testing-library/react";
import type { SVGProps } from "react";
import { describe, expect, test, vi } from "vitest";

import { AlertBanner } from "@/components/ui/alert-banner";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingRow } from "@/components/ui/loading-row";
import { MetricCard } from "@/components/ui/metric-card";
import { PermissionBadge } from "@/components/ui/permission-badge";
import { StatusPill } from "@/components/ui/status-pill";
import { SyncButton } from "@/components/ui/sync-button";

function StubIcon(props: SVGProps<SVGSVGElement>) {
  return <svg data-testid="stub-icon" {...props} />;
}

describe("StatusPill", () => {
  test("renders backend connected label", () => {
    render(<StatusPill />);
    expect(screen.getByText("Backend connesso")).toBeInTheDocument();
  });
});

describe("LoadingRow", () => {
  test("renders default column count", () => {
    const { container } = render(
      <table>
        <tbody>
          <LoadingRow />
        </tbody>
      </table>,
    );

    expect(container.querySelectorAll("td")).toHaveLength(5);
  });

  test("renders custom column count", () => {
    const { container } = render(
      <table>
        <tbody>
          <LoadingRow columns={3} />
        </tbody>
      </table>,
    );

    expect(container.querySelectorAll("td")).toHaveLength(3);
  });
});

describe("EmptyState", () => {
  test("renders icon, title, and description", () => {
    render(<EmptyState icon={StubIcon} title="Nessun dato" description="Prova a cambiare filtro." />);

    expect(screen.getByTestId("stub-icon")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Nessun dato" })).toBeInTheDocument();
    expect(screen.getByText("Prova a cambiare filtro.")).toBeInTheDocument();
  });
});

describe("MetricCard", () => {
  test("renders label, value, and optional sub text", () => {
    render(<MetricCard label="Totale" value={42} sub="Ultimo aggiornamento oggi" variant="success" />);

    expect(screen.getByText("Totale")).toBeInTheDocument();
    expect(screen.getByText("42")).toHaveClass("text-green-700");
    expect(screen.getByText("Ultimo aggiornamento oggi")).toBeInTheDocument();
  });

  test("omits sub text when not provided", () => {
    render(<MetricCard label="Totale" value="—" />);
    expect(screen.queryByText("Ultimo aggiornamento oggi")).not.toBeInTheDocument();
  });
});

describe("Avatar", () => {
  test("derives initials from label", () => {
    render(<Avatar label="Mario Rossi" size="lg" />);
    expect(screen.getByText("MR")).toBeInTheDocument();
  });

  test("renders all avatar sizes", () => {
    const { rerender } = render(<Avatar label="Ada Lovelace" size="sm" />);
    expect(screen.getByText("AL")).toHaveClass("h-7");

    rerender(<Avatar label="Ada Lovelace" size="md" />);
    expect(screen.getByText("AL")).toHaveClass("h-9");
  });

  test("handles single-character names", () => {
    render(<Avatar label="Z" />);
    expect(screen.getByText("Z")).toBeInTheDocument();
  });

  test("falls back to question mark for empty label", () => {
    render(<Avatar label="   " />);
    expect(screen.getByText("?")).toBeInTheDocument();
  });
});

describe("Badge", () => {
  test("applies variant styles", () => {
    render(<Badge variant="danger">Errore</Badge>);
    expect(screen.getByText("Errore")).toHaveClass("bg-red-50");
  });
});

describe("AlertBanner", () => {
  test("renders optional icon, title, action, and children", () => {
    render(
      <AlertBanner
        icon={<span data-testid="icon">!</span>}
        title="Attenzione"
        action={<button type="button">Azione</button>}
        variant="danger"
      >
        Messaggio di errore
      </AlertBanner>,
    );

    expect(screen.getByTestId("icon")).toBeInTheDocument();
    expect(screen.getByText("Attenzione")).toBeInTheDocument();
    expect(screen.getByText("Messaggio di errore")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Azione" })).toBeInTheDocument();
  });

  test("renders without optional slots", () => {
    render(<AlertBanner variant="info">Solo messaggio</AlertBanner>);
    expect(screen.getByText("Solo messaggio")).toBeInTheDocument();
  });
});

describe("SyncButton", () => {
  test("calls onClick and shows loading label", () => {
    const onClick = vi.fn();
    const { rerender } = render(<SyncButton onClick={onClick} label="Sync" />);

    fireEvent.click(screen.getByRole("button", { name: "Sync" }));
    expect(onClick).toHaveBeenCalledTimes(1);

    rerender(<SyncButton loading label="Sync" />);
    expect(screen.getByRole("button", { name: "Sincronizzazione..." })).toBeDisabled();
  });

  test("disables button when disabled", () => {
    render(<SyncButton disabled />);
    expect(screen.getByRole("button", { name: "Sincronizza ora" })).toBeDisabled();
  });
});

describe("PermissionBadge", () => {
  test("maps permission levels to labels", () => {
    const { rerender } = render(<PermissionBadge level="rw" />);
    expect(screen.getByText("R+W")).toBeInTheDocument();

    rerender(<PermissionBadge level="read" />);
    expect(screen.getByText("Lettura")).toBeInTheDocument();

    rerender(<PermissionBadge level="deny" />);
    expect(screen.getByText("Negato")).toBeInTheDocument();

    rerender(<PermissionBadge level="none" />);
    expect(screen.getByText("Nessun accesso")).toBeInTheDocument();
  });
});
