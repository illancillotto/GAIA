import { redirect } from "next/navigation";

export default function CatastoBatchesRedirectPage() {
  redirect("/catasto/archive?view=batches");
}
