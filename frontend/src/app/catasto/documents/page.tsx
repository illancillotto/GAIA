"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function CatastoDocumentsRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/catasto/archive?view=documents");
  }, [router]);

  return null;
}
