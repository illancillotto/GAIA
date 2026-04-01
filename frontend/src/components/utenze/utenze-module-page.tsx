"use client";

import type { ReactNode } from "react";

import { AnagraficaModulePage } from "@/components/utenze/anagrafica-module-page";
import type { CurrentUser } from "@/types/api";

type UtenzeModulePageProps = {
  title: string;
  description: string;
  breadcrumb?: string;
  actions?: ReactNode;
  children: (context: { token: string; currentUser: CurrentUser; grantedSectionKeys: string[] }) => ReactNode;
};

export function UtenzeModulePage(props: UtenzeModulePageProps) {
  return <AnagraficaModulePage {...props} />;
}

