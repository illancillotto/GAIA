"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AnagraficaImportRedirectPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/utenze/import");
  }, [router]);

  return null;
}

