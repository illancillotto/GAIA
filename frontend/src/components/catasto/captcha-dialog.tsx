"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

type CaptchaDialogProps = {
  open: boolean;
  imageUrl: string | null;
  requestLabel: string | null;
  busy?: boolean;
  onSolve: (value: string) => Promise<void>;
  onSkip: () => Promise<void>;
};

export function CaptchaDialog({
  open,
  imageUrl,
  requestLabel,
  busy = false,
  onSolve,
  onSkip,
}: CaptchaDialogProps) {
  const [value, setValue] = useState("");

  useEffect(() => {
    if (open) {
      setValue("");
    }
  }, [open, imageUrl]);

  if (!open || !imageUrl) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/45 px-4">
      <div className="w-full max-w-xl rounded-2xl border border-gray-200 bg-white p-6 shadow-2xl">
        <div className="mb-4">
          <p className="section-title">CAPTCHA richiesto</p>
          <p className="section-copy">{requestLabel ?? "Inserisci il codice mostrato per far ripartire la visura."}</p>
        </div>

        <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
          <Image
            alt="CAPTCHA Catasto"
            className="mx-auto max-h-[220px] rounded-md border border-gray-200 bg-white"
            height={220}
            src={imageUrl}
            unoptimized
            width={420}
          />
        </div>

        <div className="mt-4 space-y-3">
          <input
            className="form-control"
            disabled={busy}
            maxLength={64}
            onChange={(event) => setValue(event.target.value.toUpperCase())}
            placeholder="Inserisci il CAPTCHA"
            value={value}
          />
          <div className="flex items-center justify-end gap-3">
            <button
              className="btn-secondary"
              disabled={busy}
              onClick={() => void onSkip()}
              type="button"
            >
              Salta
            </button>
            <button
              className="btn-primary"
              disabled={busy || value.trim().length === 0}
              onClick={() => void onSolve(value.trim())}
              type="button"
            >
              Invia
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
