"use client";

import { type ReactNode, useEffect, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { RiordinoNotificationBell } from "@/components/riordino/notifications/notification-bell";
import { getStoredAccessToken } from "@/lib/auth";

type RiordinoModulePageProps = {
  title: string;
  description: string;
  breadcrumb?: string;
  topbarActions?: ReactNode;
  requiredSection?: string;
  requiredRoles?: string[];
  children: ReactNode;
};

export function RiordinoModulePage({ title, description, breadcrumb, topbarActions, requiredSection, requiredRoles, children }: RiordinoModulePageProps) {
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  return (
    <ProtectedPage
      title={title}
      description={description}
      breadcrumb={breadcrumb}
      requiredModule="riordino"
      requiredSection={requiredSection}
      requiredRoles={requiredRoles}
      topbarActions={
        <>
          {token ? <RiordinoNotificationBell token={token} /> : null}
          {topbarActions}
        </>
      }
    >
      {children}
    </ProtectedPage>
  );
}
