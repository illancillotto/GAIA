import { redirect } from "next/navigation";

export default function CatastoDocumentsRedirectPage() {
  redirect("/catasto/archive?view=documents");
}
