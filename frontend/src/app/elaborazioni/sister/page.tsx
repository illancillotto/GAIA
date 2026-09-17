import { ProtectedPage } from "@/components/app/protected-page";
import { SisterWorkspace, type SisterWorkspaceView } from "@/components/elaborazioni/sister-workspace";

export const metadata = {
  title: "SISTER / Visure - GAIA",
  description: "Operatività delle visure e stato del portale SISTER in un unico workspace.",
};

const SISTER_BREADCRUMB = [
  { label: "Elaborazioni", href: "/elaborazioni" },
  { label: "SISTER / Visure" },
];

export default async function SisterPage({
  searchParams,
}: {
  searchParams?: Promise<{ view?: string }>;
}) {
  const resolvedSearchParams = await searchParams;
  const initialView: SisterWorkspaceView = resolvedSearchParams?.view === "health" ? "health" : "operations";

  return (
    <ProtectedPage
      title="SISTER / Visure"
      description="Visure singole e massive, sincronizzazione continua e stato operativo del portale SISTER."
      breadcrumbItems={SISTER_BREADCRUMB}
    >
      <SisterWorkspace initialView={initialView} />
    </ProtectedPage>
  );
}
