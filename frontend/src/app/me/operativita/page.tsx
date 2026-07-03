"use client";

import { Suspense } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import MePageContent from "../me-page-content";

export default function MeOperativitaPage() {
  return (
    <Suspense fallback={<ProtectedPage title="La mia attività" description="Caricamento…" breadcrumb="La mia attività" />}>
      <MePageContent initialTab="operativita" />
    </Suspense>
  );
}
