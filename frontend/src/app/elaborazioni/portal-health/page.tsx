import { redirect } from "next/navigation";

export default function SisterPortalHealthPage() {
  redirect("/elaborazioni/sister?view=health");
}
