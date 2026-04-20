"use client";

import { PropsWithChildren } from "react";

import { ProtectedPage, type ProtectedPageProps } from "@/components/app/protected-page";
import { CatastoPhase1Nav } from "@/components/catasto/phase1-nav";

type CatastoPageProps = PropsWithChildren<Omit<ProtectedPageProps, "children">>;

export function CatastoPage({ children, ...props }: CatastoPageProps) {
  return (
    <ProtectedPage {...props}>
      <CatastoPhase1Nav />
      {children}
    </ProtectedPage>
  );
}
