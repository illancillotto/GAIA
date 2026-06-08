"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function InazCapisettorePage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/inaz/organigramma");
  }, [router]);

  return null;
}
