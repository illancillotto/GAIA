"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AnagraficaRedirectPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/utenze");
  }, [router]);

  return null;
}

