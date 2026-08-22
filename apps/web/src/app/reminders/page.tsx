"use client";

import { useEffect, useState, useCallback } from "react";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { api, ApiError } from "@/lib/apiClient";
import type { Reminder } from "@/lib/types";

const TABS: { value: string; label: string }[] = [
  { value: "PENDING", label: "Pending" },
  { value: "SENT", label: "Sent" },
  { value: "DISMISSED", label: "Dismissed" },
];

export default function RemindersPage() {
  const { ready } = useRequireAuth();
  const [status, setStatus] = useState("PENDING");
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setReminders(await api.listReminders(status));
    setLoading(false);
  }, [status]);

  useEffect(() => {
    if (ready) refresh();
  }, [ready, refresh]);

  async function dismiss(id: string) {
    setError(null);
    try {
      await api.updateReminderStatus(id, "DISMISSED");
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? String(err.message) : "Something went wrong.");
    }
  }

  async function runLowStockCheck() {
    setChecking(true);
    setError(null);
    try {
      await api.checkLowStock();
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? String(err.message) : "Something went wrong.");
    } finally {
      setChecking(false);
    }
  }

  if (!ready) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Reminders</h1>
          <p className="text-sm text-muted mt-0.5">
            Low-stock alerts are created automatically when a sale or stock change crosses a
            product&apos;s reorder level.
          </p>
        </div>
        <button onClick={runLowStockCheck} disabled={checking} className="btn-secondary text-sm">
          {checking ? "Checking..." : "Run low-stock check now"}
        </button>
      </div>

      <div className="flex gap-1 border-b border-line">
        {TABS.map((t) => (
          <button
            key={t.value}
            onClick={() => setStatus(t.value)}
            className={`text-sm px-3 py-2 border-b-2 -mb-px transition-colors ${
              status === t.value
                ? "border-accent text-ink font-medium"
                : "border-transparent text-muted hover:text-ink"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && <p className="text-sm text-warn">{error}</p>}
      {loading && <p className="text-sm text-muted">Loading...</p>}

      <div className="space-y-3">
        {reminders.map((r) => (
          <div key={r.id} className="card flex items-start justify-between gap-4">
            <div>
              <span className="badge bg-line/50 text-muted mb-1 inline-block">{r.type.replace("_", " ")}</span>
              <p className="text-sm">{r.message}</p>
              <p className="text-xs text-muted mt-1">Due {new Date(r.due_at).toLocaleString()}</p>
            </div>
            {r.status === "PENDING" && (
              <button onClick={() => dismiss(r.id)} className="btn-secondary text-xs shrink-0">
                Dismiss
              </button>
            )}
          </div>
        ))}
        {!loading && reminders.length === 0 && (
          <div className="card text-center text-sm text-muted py-10">
            No {status.toLowerCase()} reminders.
          </div>
        )}
      </div>
    </div>
  );
}
