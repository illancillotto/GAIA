"use client";

import { useParams } from "next/navigation";
import type { ReactNode } from "react";

import SchedaTerritorialeActions from "@/components/catasto/gis/SchedaTerritorialeActions";
import { useSessionBootstrap } from "@/lib/use-session-bootstrap";

export default function ParticellaDetailLayout({ children }: { children: ReactNode }) {
  const params = useParams<{ id: string }>();
  const session = useSessionBootstrap();
  const particellaId = typeof params.id === "string" && params.id ? params.id : null;

  return (
    <>
      {children}
      <SchedaTerritorialeActions
        token={session.token}
        particellaId={particellaId}
        currentUser={session.currentUser}
        className="fixed bottom-6 right-6 z-50 w-[min(22rem,calc(100%-3rem))] rounded-2xl bg-white/95 p-3 shadow-2xl backdrop-blur"
      />
    </>
  );
}
