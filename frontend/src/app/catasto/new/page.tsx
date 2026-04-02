import { CatastoRequestWorkspace } from "@/components/catasto/request-workspace";

type CatastoNewRequestPageProps = {
  searchParams?: Promise<{
    mode?: string;
  }>;
};

export default async function CatastoNewRequestPage({ searchParams }: CatastoNewRequestPageProps) {
  const resolvedSearchParams = await searchParams;
  const mode = resolvedSearchParams?.mode === "batch" ? "batch" : "single";

  return <CatastoRequestWorkspace initialMode={mode} />;
}
