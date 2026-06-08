"use client";

import Link from "next/link";

type Props = {
  subjectId: string;
  subjectLabel?: string | null;
  onClose: () => void;
};

export function UtenzeSubjectQuickViewDialog({ subjectId, subjectLabel, onClose }: Props) {
  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/45 px-3 py-5 backdrop-blur-sm xl:px-5">
      <div className="flex h-full max-h-[95vh] w-full max-w-[min(1600px,98vw)] flex-col overflow-hidden rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
        <div className="flex items-center justify-between gap-4 border-b border-gray-100 bg-white px-6 py-4">
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
        <div className="flex-1 overflow-hidden bg-[#f4f7f5] p-4 xl:px-5 xl:py-5">
          <iframe
            key={subjectId}
            src={`/utenze/${subjectId}?embedded=1`}
            title={`Dettaglio ${subjectLabel || subjectId}`}
            className="h-full w-full rounded-2xl border border-gray-200 bg-white shadow-sm"
          />
        </div>
      </div>
    </div>
  );
}
