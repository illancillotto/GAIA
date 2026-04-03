import { redirect } from "next/navigation";

import { CatastoArchiveWorkspace } from "@/components/catasto/archive-workspace";

type CatastoArchivePageProps = {
  searchParams?: Promise<{
    view?: string;
  }>;
};

export default async function CatastoArchivePage({ searchParams }: CatastoArchivePageProps) {
  const resolvedSearchParams = await searchParams;
  if (resolvedSearchParams?.view === "batches") {
    redirect("/elaborazioni/batches");
  }

  const initialView = "documents";

  return <CatastoArchiveWorkspace initialView={initialView} />;
}
