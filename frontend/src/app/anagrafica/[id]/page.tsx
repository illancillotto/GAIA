import { redirect } from "next/navigation";

export default async function AnagraficaSubjectRedirectPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  redirect(`/utenze/${id}`);
}

