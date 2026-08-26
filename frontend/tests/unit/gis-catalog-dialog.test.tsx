import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, test, vi } from "vitest";

import {
  CatalogDialog,
  ConfirmationDialog,
} from "@/app/gis/catalogo/catalog-dialog";

function DialogHarness() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        Apri dialog
      </button>
      {open ? (
        <CatalogDialog
          titleId="test-dialog-title"
          panelClassName="test-panel"
          onClose={() => setOpen(false)}
        >
          <h2 id="test-dialog-title">Dialog di prova</h2>
          <button type="button" data-dialog-initial-focus>
            Primo comando
          </button>
          <button type="button">Ultimo comando</button>
        </CatalogDialog>
      ) : null}
    </>
  );
}

function RemovedTriggerHarness({ fallbackTabIndex }: { fallbackTabIndex?: number }) {
  const [open, setOpen] = useState(false);
  const [showTrigger, setShowTrigger] = useState(true);
  return (
    <main data-dialog-focus-fallback tabIndex={fallbackTabIndex}>
      {showTrigger ? (
        <button key="trigger" type="button" onClick={() => setOpen(true)}>
          Apri e rimuovi trigger
        </button>
      ) : null}
      {open ? (
        <CatalogDialog
          titleId="removed-trigger-title"
          panelClassName="test-panel"
          onClose={() => setOpen(false)}
        >
          <h2 id="removed-trigger-title">Conferma operazione</h2>
          <button key="complete" type="button" data-dialog-initial-focus onClick={() => {
            setShowTrigger(false);
            setOpen(false);
          }}>
            Completa
          </button>
        </CatalogDialog>
      ) : null}
    </main>
  );
}

function BareDialogHarness() {
  return (
    <CatalogDialog titleId="bare-title" panelClassName="test-panel" onClose={() => undefined}>
      <h2 id="bare-title">Dialog senza focus iniziale</h2>
    </CatalogDialog>
  );
}

function NoFallbackHarness() {
  const [open, setOpen] = useState(false);
  const [showTrigger, setShowTrigger] = useState(true);
  return (
    <div>
      {showTrigger ? (
        <button key="trigger" type="button" onClick={() => setOpen(true)}>
          Apri senza fallback
        </button>
      ) : null}
      {open ? (
        <CatalogDialog titleId="no-fallback-title" panelClassName="test-panel" onClose={() => setOpen(false)}>
          <h2 id="no-fallback-title">Dialog senza fallback</h2>
          <button key="complete" type="button" data-dialog-initial-focus onClick={() => {
            setShowTrigger(false);
            setOpen(false);
          }}>
            Completa senza fallback
          </button>
        </CatalogDialog>
      ) : null}
    </div>
  );
}

describe("GIS catalog dialogs", () => {
  test("traps keyboard focus, closes with Escape and restores the trigger", () => {
    render(<DialogHarness />);
    const trigger = screen.getByRole("button", { name: "Apri dialog" });
    trigger.focus();
    fireEvent.click(trigger);

    const first = screen.getByRole("button", { name: "Primo comando" });
    const last = screen.getByRole("button", { name: "Ultimo comando" });
    expect(first).toHaveFocus();

    fireEvent.keyDown(document, { key: "ArrowDown" });
    expect(first).toHaveFocus();
    trigger.focus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(first).toHaveFocus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(first).toHaveFocus();

    last.focus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(first).toHaveFocus();

    last.focus();
    fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
    expect(last).toHaveFocus();

    first.focus();
    fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
    expect(last).toHaveFocus();

    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  test("renders safe and destructive confirmations and blocks closing while busy", () => {
    const onCancel = vi.fn();
    const onConfirm = vi.fn();
    const { rerender } = render(
      <ConfirmationDialog
        title="Pubblicare?"
        description="Controlla i dati."
        consequences={["Crea un layer in sola lettura."]}
        confirmLabel="Conferma pubblicazione"
        busy={false}
        error={null}
        tone="primary"
        onCancel={onCancel}
        onConfirm={onConfirm}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Conferma pubblicazione" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Annulla" }));
    expect(onCancel).toHaveBeenCalledTimes(1);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onCancel).toHaveBeenCalledTimes(2);

    rerender(
      <ConfirmationDialog
        title="Revocare?"
        description="Il permesso sarà rimosso."
        consequences={["L'accesso cambia subito."]}
        confirmLabel="Conferma revoca"
        busy
        error="Operazione non completata."
        tone="destructive"
        onCancel={onCancel}
        onConfirm={onConfirm}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Operazione non completata.",
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "Operazione in corso",
    );
    expect(screen.getByRole("button", { name: "Attendi..." })).toBeDisabled();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(screen.getByRole("dialog")).toHaveFocus();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onCancel).toHaveBeenCalledTimes(2);
  });

  test("locks page scrolling and restores focus to a stable fallback when the trigger disappears", async () => {
    render(<RemovedTriggerHarness />);
    const trigger = screen.getByRole("button", { name: "Apri e rimuovi trigger" });
    trigger.focus();
    fireEvent.click(trigger);
    expect(document.body).toHaveStyle({ overflow: "hidden" });

    fireEvent.click(screen.getByRole("button", { name: "Completa" }));

    expect(document.body.style.overflow).toBe("");
    await waitFor(() => expect(screen.getByRole("main")).toHaveFocus());
  });

  test("preserves an existing fallback tab index while restoring focus", async () => {
    render(<RemovedTriggerHarness fallbackTabIndex={-1} />);
    const trigger = screen.getByRole("button", { name: "Apri e rimuovi trigger" });
    trigger.focus();
    fireEvent.click(trigger);
    fireEvent.click(screen.getByRole("button", { name: "Completa" }));
    const fallback = screen.getByRole("main");
    await waitFor(() => expect(fallback).toHaveFocus());
    expect(fallback).toHaveAttribute("tabindex", "-1");
  });

  test("focuses the dialog panel when no initial control is declared", () => {
    render(<BareDialogHarness />);
    expect(screen.getByRole("dialog")).toHaveFocus();
  });

  test("closes safely when neither the trigger nor a stable fallback remains", async () => {
    render(<NoFallbackHarness />);
    const trigger = screen.getByRole("button", { name: "Apri senza fallback" });
    trigger.focus();
    fireEvent.click(trigger);
    const querySelector = vi
      .spyOn(document, "querySelector")
      .mockImplementation((selector) =>
        selector === "[data-dialog-focus-fallback], main"
          ? null
          : Document.prototype.querySelector.call(document, selector),
      );
    fireEvent.click(screen.getByRole("button", { name: "Completa senza fallback" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(querySelector).toHaveBeenCalledWith("[data-dialog-focus-fallback], main");
  });
});
