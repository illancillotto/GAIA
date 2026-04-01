"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AnagraficaSubjectsRedirectPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/utenze/subjects");
  }, [router]);

  return null;
}

