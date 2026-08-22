"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/apiClient";
import { useAuthStore } from "@/lib/store";

export default function OnboardingPage() {
  const router = useRouter();
  const { token, businesses, setSession, setBusinessScope } = useAuthStore();
  const [name, setName] = useState("");
  const [currency, setCurrency] = useState("INR");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) router.replace("/login");
  }, [token, router]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.createBusiness({ name, currency });
      // Re-login to get a token auto-scoped to the (now single) business,
      // matching the backend's own selection rule.
      const stored = useAuthStore.getState();
      // We don't have the password here, so re-select via the businesses
      // list refresh instead of a fresh login.
      const list = await api.listBusinesses();
      if (list.length === 1) {
        const selected = await api.selectBusiness(list[0].id);
        setSession({
          token: selected.access_token,
          user: stored.user!,
          businessId: selected.selected_business_id,
          businesses: selected.businesses,
          needsOnboarding: false,
        });
        router.push("/");
      } else {
        setSession({
          token: stored.token!,
          user: stored.user!,
          businessId: null,
          businesses: list.map((b) => ({ business_id: b.id, business_name: b.name, role: b.role })),
          needsOnboarding: false,
        });
      }
    } catch (err) {
      setError(err instanceof ApiError ? String(err.message) : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSelect(businessId: string) {
    setError(null);
    try {
      const res = await api.selectBusiness(businessId);
      setBusinessScope(res.access_token, res.selected_business_id!);
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError ? String(err.message) : "Something went wrong.");
    }
  }

  return (
    <div className="max-w-md mx-auto mt-16 space-y-6">
      {businesses.length > 0 && (
        <div className="card">
          <h2 className="text-sm font-semibold mb-3">Choose a business</h2>
          <div className="space-y-2">
            {businesses.map((b) => (
              <button
                key={b.business_id}
                onClick={() => handleSelect(b.business_id)}
                className="w-full text-left px-3 py-2 rounded-md border border-line hover:border-accent hover:bg-accent/5 text-sm flex justify-between"
              >
                <span>{b.business_name}</span>
                <span className="text-muted">{b.role}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <h2 className="text-sm font-semibold mb-1">Add a new business</h2>
        <p className="text-xs text-muted mb-4">
          {businesses.length === 0
            ? "You don't have a business set up yet — create one to get started."
            : "Or set up another business."}
        </p>
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="label">Business name</label>
            <input required value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <label className="label">Currency</label>
            <input value={currency} onChange={(e) => setCurrency(e.target.value)} />
          </div>
          {error && <p className="text-sm text-warn">{error}</p>}
          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? "Creating..." : "Create business"}
          </button>
        </form>
      </div>
    </div>
  );
}
