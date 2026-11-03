import { redirect } from "next/navigation";

// The tenant sign-in screen lives at "/"; keep /login working for old links.
export default function LoginRedirectPage() {
  redirect("/");
}
