"use client";

import { useParams } from "next/navigation";

import { CatastoDocumentDetailWorkspace } from "@/components/catasto/document-detail-workspace";

export default function CatastoDocumentDetailPage() {
  const params = useParams<{ id: string }>();
  return <CatastoDocumentDetailWorkspace documentId={params.id} />;
}
