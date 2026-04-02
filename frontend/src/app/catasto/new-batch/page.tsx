import { redirect } from "next/navigation";

export default function CatastoNewBatchRedirectPage() {
  redirect("/catasto/new?mode=batch");
}
