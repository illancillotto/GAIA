"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

export default function AnagraficaSubjectRedirectPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();

  useEffect(() => {
    router.replace(`/utenze/${params.id}`);
  }, [params.id, router]);

  return null;
}

