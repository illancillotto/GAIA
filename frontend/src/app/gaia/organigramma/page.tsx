import { redirect } from "next/navigation";

export default function GaiaOrganigrammaRedirectPage() {
  redirect("/presenze/organigramma");
  return null;
}
