import { CatastoArchiveWorkspace } from "@/components/catasto/archive-workspace";

type CatastoArchivePageProps = {
  searchParams?: Promise<{
    view?: string;
  }>;
};

export default async function CatastoArchivePage({ searchParams }: CatastoArchivePageProps) {
  const resolvedSearchParams = await searchParams;
  const initialView = resolvedSearchParams?.view === "batches" ? "batches" : "documents";

  return <CatastoArchiveWorkspace initialView={initialView} />;
}
