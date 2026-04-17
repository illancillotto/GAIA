"use client";

import { useEffect, useState, type ReactNode } from "react";
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
  const [isEmbedded, setIsEmbedded] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const params = new URLSearchParams(window.location.search);
    setIsEmbedded(params.get("embedded") === "1");
  }, []);

  if (isEmbedded) {
    return <main className="min-h-full bg-white p-4">{children}</main>;
  }

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
