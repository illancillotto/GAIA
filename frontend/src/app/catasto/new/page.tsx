import { redirect } from "next/navigation";

type CatastoNewRequestPageProps = {
  searchParams?: Promise<{
    mode?: string;
  }>;
};

export default async function CatastoNewRequestPage({ searchParams }: CatastoNewRequestPageProps) {
  const resolvedSearchParams = await searchParams;
  redirect(resolvedSearchParams?.mode === "batch" ? "/elaborazioni/new-batch" : "/elaborazioni/new-single");
}
