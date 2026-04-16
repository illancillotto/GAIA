"use client";

import { type ReactNode } from "react";

import { ProtectedPage } from "@/components/app/protected-page";

type RuoloModulePageProps = {
  title: string;
  description: string;
  breadcrumb?: string;
  topbarActions?: ReactNode;
  requiredSection?: string;
  requiredRoles?: string[];
  children: ReactNode;
};

export function RuoloModulePage({
  title,
  description,
  breadcrumb,
  topbarActions,
  requiredSection,
  requiredRoles,
  children,
}: RuoloModulePageProps) {
  return (
    <ProtectedPage
      title={title}
      description={description}
      breadcrumb={breadcrumb}
      requiredModule="ruolo"
      requiredSection={requiredSection}
      requiredRoles={requiredRoles}
      topbarActions={topbarActions}
    >
      {children}
    </ProtectedPage>
  );
}
