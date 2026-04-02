import { redirect } from "next/navigation";

export default function CatastoNewSingleRedirectPage() {
  redirect("/catasto/new?mode=single");
}
