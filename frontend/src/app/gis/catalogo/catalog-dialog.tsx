"use client";

import { useEffect, useRef, type ReactNode } from "react";

const focusableSelector = [
  "button:not([disabled])",
  "a[href]",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(",");

export function CatalogDialog({
  titleId,
  panelClassName,
  onClose,
  children,
}: {
  titleId: string;
  panelClassName: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const dialogRef = useRef<HTMLElement>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    const previousFocus = document.activeElement as HTMLElement;
    const dialog = dialogRef.current as HTMLElement;
    const previousBodyOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    (dialog.querySelector<HTMLElement>("[data-dialog-initial-focus]") ?? dialog).focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab") return;

      const focusableElements = Array.from(
        dialog.querySelectorAll<HTMLElement>(focusableSelector),
      );
      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];
      if (!firstElement || !lastElement) {
        event.preventDefault();
        dialog.focus();
        return;
      }
      if (!dialog.contains(document.activeElement)) {
        event.preventDefault();
        firstElement.focus();
        return;
      }
      const boundaryElement = event.shiftKey ? firstElement : lastElement;
      if (document.activeElement !== boundaryElement) return;

      event.preventDefault();
      (event.shiftKey ? lastElement : firstElement).focus();
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousBodyOverflow;
      const restoreFocus = () => {
        if (previousFocus.isConnected) {
          previousFocus.focus();
          return;
        }
        const fallback = document.querySelector<HTMLElement>("[data-dialog-focus-fallback], main");
        if (!fallback) return;
        if (!fallback.hasAttribute("tabindex")) fallback.tabIndex = -1;
        fallback.focus();
      };
      restoreFocus();
    };
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto overscroll-contain bg-[#17231d]/70 p-3 sm:items-center sm:p-4">
      <section
        ref={dialogRef}
        tabIndex={-1}
        aria-modal="true"
        aria-labelledby={titleId}
        className={`${panelClassName} max-h-[calc(100dvh-1.5rem)] overflow-y-auto overscroll-contain`}
        role="dialog"
      >
        {children}
      </section>
    </div>
  );
}

type ConfirmationDialogProps = {
  title: string;
  description: string;
  consequences: string[];
  confirmLabel: string;
  busy: boolean;
  error: string | null;
  tone: "primary" | "destructive";
  onCancel: () => void;
  onConfirm: () => void;
};

function ConfirmationHeader({
  titleId,
  title,
  description,
}: Pick<ConfirmationDialogProps, "title" | "description"> & { titleId: string }) {
  return (
    <div className="border-b border-[#e1e9e2] bg-[#f4f8f4] p-5 sm:p-6">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#557260]">
        Controllo prima di procedere
      </p>
      <h2 id={titleId} className="mt-2 text-2xl font-semibold text-[#17231d]">
        {title}
      </h2>
      <p className="mt-3 text-sm leading-6 text-gray-700">{description}</p>
    </div>
  );
}

function ConfirmationConsequences({
  consequences,
  error,
  busy,
}: Pick<ConfirmationDialogProps, "consequences" | "error" | "busy">) {
  return (
    <>
      <p className="text-sm font-semibold text-gray-950">Cosa succederà</p>
      <ul className="mt-3 grid gap-2 text-sm leading-6 text-gray-700">
        {consequences.map((consequence) => (
          <li key={consequence} className="rounded-xl bg-[#f6f8f6] px-3 py-2">
            {consequence}
          </li>
        ))}
      </ul>
      {error ? (
        <p className="mt-4 rounded-xl bg-red-50 px-3 py-2 text-sm font-medium text-red-700" role="alert">
          {error}
        </p>
      ) : null}
      {busy ? (
        <p className="mt-4 text-sm font-medium text-[#1D4E35]" role="status" aria-live="polite">
          Operazione in corso...
        </p>
      ) : null}
    </>
  );
}

function ConfirmationActions({
  confirmLabel,
  busy,
  tone,
  onCancel,
  onConfirm,
}: Pick<ConfirmationDialogProps, "confirmLabel" | "busy" | "tone" | "onCancel" | "onConfirm">) {
  return (
    <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
      <button
        className="btn-secondary"
        type="button"
        data-dialog-initial-focus
        disabled={busy}
        onClick={onCancel}
      >
        Annulla
      </button>
      <button
        className={
          tone === "destructive"
            ? "rounded-xl bg-[#9f2d2d] px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#842424]"
            : "btn-primary"
        }
        type="button"
        disabled={busy}
        onClick={onConfirm}
      >
        {busy ? "Attendi..." : confirmLabel}
      </button>
    </div>
  );
}

export function ConfirmationDialog(props: ConfirmationDialogProps) {
  const { title, description, consequences, busy, error, onCancel } = props;
  const titleId = "gis-confirmation-title";
  const closeDialog = () => {
    if (!busy) onCancel();
  };

  return (
    <CatalogDialog
      titleId={titleId}
      panelClassName="w-full max-w-xl overflow-hidden rounded-[26px] border border-[#d7e2d8] bg-white shadow-2xl"
      onClose={closeDialog}
    >
      <ConfirmationHeader titleId={titleId} title={title} description={description} />
      <div className="p-5 sm:p-6">
        <ConfirmationConsequences consequences={consequences} error={error} busy={busy} />
        <ConfirmationActions {...props} />
      </div>
    </CatalogDialog>
  );
}
