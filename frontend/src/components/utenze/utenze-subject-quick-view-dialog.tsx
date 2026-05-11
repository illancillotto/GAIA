"use client";

import Link from "next/link";

type Props = {
  subjectId: string;
  subjectLabel?: string | null;
  onClose: () => void;
};

export function UtenzeSubjectQuickViewDialog({ subjectId, subjectLabel, onClose }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4 py-6">
      <div className="flex h-full max-h-[94vh] w-full max-w-6xl flex-col rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between gap-4 border-b border-gray-100 px-6 py-4">
          <div className="min-w-0">
            <p className="section-title">Dettaglio soggetto</p>
            <p className="mt-1 truncate text-sm text-gray-500">{subjectLabel || subjectId}</p>
          </div>
          <div className="flex items-center gap-3">
            <Link className="btn-secondary" href={`/utenze/${subjectId}`} target="_blank">
              Apri pagina
            </Link>
            <button className="btn-secondary" type="button" onClick={onClose}>
              Chiudi
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-hidden p-4">
          <iframe
            key={subjectId}
            src={`/utenze/${subjectId}?embedded=1`}
            title={`Dettaglio ${subjectLabel || subjectId}`}
            className="h-full w-full rounded-xl border border-gray-200 bg-white"
          />
        </div>
      </div>
    </div>
  );
}
