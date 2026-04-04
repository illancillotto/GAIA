"use client";

import { useParams } from "next/navigation";

import { ElaborazioneBatchDetailWorkspace } from "@/components/elaborazioni/batch-detail-workspace";

export default function ElaborazioneBatchDetailPage() {
  const params = useParams<{ id: string }>();
  return <ElaborazioneBatchDetailWorkspace batchId={params.id} />;
}
