"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { UtenzeModulePage } from "@/components/utenze/utenze-module-page";

export default function UtenzeSubjectsRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/utenze/import#utenze-soggetti");
  }, [router]);

  return (
    <UtenzeModulePage title="Utenti" description="Reindirizzamento al centro import." breadcrumb="Utenti">
      {() => (
        <div className="flex min-h-[40vh] items-center justify-center rounded-[28px] border border-[#d9dfd6] bg-white p-8 text-sm text-gray-500 shadow-panel">
          Reindirizzamento al centro import…
        </div>
      )}
    </UtenzeModulePage>
  );
}
