"use client";

import { useEffect, useState, useCallback } from "react";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { api, ApiError } from "@/lib/apiClient";
import type { Customer } from "@/lib/types";

export default function CustomersPage() {
  const { ready } = useRequireAuth();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const refresh = useCallback(async () => {
    setCustomers(await api.listCustomers());
  }, []);

  useEffect(() => {
    if (ready) refresh();
  }, [ready, refresh]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setCreating(true);
    try {
      await api.createCustomer({ name, phone: phone || undefined });
      setName("");
      setPhone("");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? String(err.message) : "Something went wrong.");
    } finally {
      setCreating(false);
    }
  }

  if (!ready) return null;

  const totalDues = customers.reduce((sum, c) => sum + Number(c.balance_due), 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Customers</h1>
        {customers.length > 0 && (
          <span className="text-sm text-muted">Total dues: ₹{totalDues.toFixed(2)}</span>
        )}
      </div>

      <div className="card">
        <h2 className="text-sm font-semibold mb-3">Add a customer</h2>
        <form onSubmit={handleCreate} className="flex gap-2 items-end flex-wrap">
          <div className="flex-1 min-w-[160px]">
            <label className="label">Name</label>
            <input required value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="flex-1 min-w-[160px]">
            <label className="label">Phone (optional)</label>
            <input value={phone} onChange={(e) => setPhone(e.target.value)} />
          </div>
          <button type="submit" className="btn-primary" disabled={creating}>
            {creating ? "Adding..." : "Add customer"}
          </button>
        </form>
        {error && <p className="text-sm text-warn mt-2">{error}</p>}
      </div>

      <div className="card p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-paper text-muted text-xs">
            <tr>
              <th className="text-left px-4 py-2 font-medium">Name</th>
              <th className="text-left px-4 py-2 font-medium">Phone</th>
              <th className="text-left px-4 py-2 font-medium">Balance due</th>
              <th className="text-left px-4 py-2 font-medium">Last purchase</th>
            </tr>
          </thead>
          <tbody>
            {customers.map((c) => (
              <tr key={c.id} className="border-t border-line">
                <td className="px-4 py-2">{c.name}</td>
                <td className="px-4 py-2 text-muted">{c.phone || "—"}</td>
                <td className={`px-4 py-2 ${Number(c.balance_due) > 0 ? "text-warn font-medium" : ""}`}>
                  ₹{c.balance_due}
                </td>
                <td className="px-4 py-2 text-muted text-xs">
                  {c.last_purchase_at ? new Date(c.last_purchase_at).toLocaleDateString() : "—"}
                </td>
              </tr>
            ))}
            {customers.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-muted text-sm">
                  No customers yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
