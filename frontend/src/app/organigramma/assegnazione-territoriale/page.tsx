import { redirect } from "next/navigation";

export default function AssegnazioneTerritorialeRedirectPage() {
  redirect("/presenze/assegnazione-territoriale");
  return null;
}
