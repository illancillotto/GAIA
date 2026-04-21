"use client";

import type { ReactNode } from "react";

import { CatastoPhase1Nav } from "@/components/catasto/phase1-nav";

export default function CatastoLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <CatastoPhase1Nav />
      {children}
    </>
  );
}
