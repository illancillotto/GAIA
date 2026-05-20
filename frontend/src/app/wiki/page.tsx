import { WikiPage } from "@/features/wiki/WikiPage";

export const metadata = {
  title: "Wiki — GAIA",
  description: "Documentazione e assistente GAIA",
};

export default function WikiRoute() {
  return <WikiPage />;
}
