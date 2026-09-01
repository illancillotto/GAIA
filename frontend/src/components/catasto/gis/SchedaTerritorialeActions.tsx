"use client";

import { useSchedaTerritoriale } from "@/components/catasto/gis/use-scheda-territoriale";
import { hasUserModuleAccess } from "@/lib/module-access";
import type { CurrentUser } from "@/types/api";

type SchedaTerritorialeActionsProps = {
  token: string | null;
  particellaId: string | null;
  currentUser: Pick<CurrentUser, "enabled_modules" | "role"> | null;
  className?: string;
};

export default function SchedaTerritorialeActions({
  token,
  particellaId,
  currentUser,
  className = "",
}: SchedaTerritorialeActionsProps) {
  const scheda = useSchedaTerritoriale(token, particellaId);

  if (!currentUser || !hasUserModuleAccess(currentUser, "gis") || !particellaId) {
    return null;
  }

  const pending = ["queued", "processing"].includes(scheda.sheet?.status ?? "");
  const buttonLabel = scheda.sheet?.status === "queued"
    ? "Scheda in coda..."
    : scheda.sheet?.status === "processing"
      ? "Generazione scheda..."
      : "Genera scheda territoriale";

  return (
    <div className={className} data-testid="scheda-territoriale-actions">
      {scheda.error ? (
        <p role="alert" className="mb-2 rounded-xl bg-red-50 p-3 text-sm text-red-800">
          {scheda.error}
        </p>
      ) : null}
      {scheda.downloadUrl ? (
        <a
          href={scheda.downloadUrl}
          download
          className="block w-full rounded-xl bg-emerald-800 px-4 py-3 text-center text-sm font-bold text-white"
        >
          Scarica scheda territoriale PDF
        </a>
      ) : (
        <button
          type="button"
          disabled={!token || pending}
          onClick={scheda.generate}
          className="w-full rounded-xl bg-emerald-800 px-4 py-3 text-sm font-bold text-white disabled:bg-stone-200 disabled:text-stone-500"
        >
          {buttonLabel}
        </button>
      )}
    </div>
  );
}
