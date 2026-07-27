"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function PresenzeImportPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/elaborazioni/presenze-sync");
  }, [router]);

  return null;
}
