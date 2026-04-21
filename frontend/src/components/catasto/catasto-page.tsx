"use client";

import { PropsWithChildren } from "react";

import { ProtectedPage, type ProtectedPageProps } from "@/components/app/protected-page";

type CatastoPageProps = PropsWithChildren<Omit<ProtectedPageProps, "children">>;

export function CatastoPage({ children, ...props }: CatastoPageProps) {
  return <ProtectedPage {...props}>{children}</ProtectedPage>;
}
