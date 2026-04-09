"use client";

type RiordinoConfirmDialogProps = {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: "primary" | "danger";
  busy?: boolean;
  onCancel: () => void;
  onConfirm: () => void | Promise<void>;
};

export function RiordinoConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Conferma",
  cancelLabel = "Annulla",
  tone = "primary",
  busy = false,
  onCancel,
  onConfirm,
}: RiordinoConfirmDialogProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-950/35 px-4">
      <div className="w-full max-w-lg rounded-3xl bg-white p-6 shadow-2xl">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-gray-400">Conferma azione</p>
        <h3 className="mt-2 text-lg font-semibold text-gray-900">{title}</h3>
        <p className="mt-3 text-sm leading-6 text-gray-600">{description}</p>
        <div className="mt-6 flex flex-wrap justify-end gap-2">
          <button className="btn-secondary" disabled={busy} onClick={onCancel} type="button">
            {cancelLabel}
          </button>
          <button
            className={tone === "danger" ? "rounded-full bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60" : "btn-primary"}
            disabled={busy}
            onClick={() => void onConfirm()}
            type="button"
          >
            {busy ? "Attendere..." : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
