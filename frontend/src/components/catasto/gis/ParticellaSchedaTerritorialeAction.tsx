"use client";

import SchedaTerritorialeActions from "@/components/catasto/gis/SchedaTerritorialeActions";
import { useAppShellContext } from "@/components/layout/app-shell-context";
import { getStoredAccessToken } from "@/lib/auth";

export default function ParticellaSchedaTerritorialeAction({
  particellaId,
}: {
  particellaId: string;
}) {
  const { currentUser } = useAppShellContext();

  return (
    <SchedaTerritorialeActions
      token={getStoredAccessToken()}
      particellaId={particellaId}
      currentUser={currentUser}
      className="fixed bottom-6 right-6 z-[71] w-[min(22rem,calc(100%-3rem))] rounded-2xl bg-white/95 p-3 shadow-2xl backdrop-blur"
    />
  );
}
