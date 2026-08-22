"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "./store";

/** Redirects to /login (no token) or /onboarding (token but no business
 * scoped yet), mirroring the backend's own needs_onboarding / multi-business
 * rules. Returns `ready=true` once it's safe for the page to render. */
export function useRequireAuth() {
  const router = useRouter();
  const { token, businessId } = useAuthStore();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!token) {
      router.replace("/login");
      return;
    }
    if (!businessId) {
      router.replace("/onboarding");
      return;
    }
    setReady(true);
  }, [token, businessId, router]);

  return { ready };
}
