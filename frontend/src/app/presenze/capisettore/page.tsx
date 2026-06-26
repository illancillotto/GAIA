"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function PresenzeCapisettorePage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/presenze/organigramma");
  }, [router]);

  return null;
}
