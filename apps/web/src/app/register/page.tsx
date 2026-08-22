"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/apiClient";
import { useAuthStore } from "@/lib/store";

export default function RegisterPage() {
  const router = useRouter();
  const setSession = useAuthStore((s) => s.setSession);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.register({ name, email, password });
      const res = await api.login({ email, password });
      setSession({
        token: res.access_token,
        user: res.user,
        businessId: res.selected_business_id,
        businesses: res.businesses,
        needsOnboarding: res.needs_onboarding,
      });
      router.push("/onboarding");
    } catch (err) {
      setError(err instanceof ApiError ? String(err.message) : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-sm mx-auto mt-16">
      <h1 className="text-lg font-semibold mb-1">Create your account</h1>
      <p className="text-sm text-muted mb-6">Set up VyaparFlow for your shop.</p>
      <form onSubmit={handleSubmit} className="card space-y-4">
        <div>
          <label className="label">Your name</label>
          <input required value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <label className="label">Email</label>
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div>
          <label className="label">Password (min 8 characters)</label>
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        {error && <p className="text-sm text-warn">{error}</p>}
        <button type="submit" className="btn-primary w-full" disabled={loading}>
          {loading ? "Creating account..." : "Create account"}
        </button>
      </form>
      <p className="text-sm text-muted mt-4 text-center">
        Already have an account?{" "}
        <Link href="/login" className="text-accent underline">
          Log in
        </Link>
      </p>
    </div>
  );
}
