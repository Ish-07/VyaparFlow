"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { api } from "@/lib/apiClient";
import { CommandBar } from "@/components/CommandBar";
import type { DashboardResponse, Insight, Product, Reminder, VoiceCommandResponse } from "@/lib/types";

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="card">
      <p className="label">{label}</p>
      <p className="text-xl font-semibold">{value}</p>
    </div>
  );
}

export default function DashboardPage() {
  const { ready } = useRequireAuth();
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [lowStock, setLowStock] = useState<Product[]>([]);
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [pending, setPending] = useState<VoiceCommandResponse[]>([]);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    const [d, p, r, cmds, ins] = await Promise.all([
      api.getDashboard(),
      api.listProducts({ low_stock_only: true }),
      api.listReminders("PENDING"),
      api.listVoiceCommands("NEEDS_CONFIRMATION"),
      api.listInsights(),
    ]);
    setDashboard(d);
    setLowStock(p);
    setReminders(r);
    setPending(cmds);
    setInsights(ins.slice(0, 3));
    setLoading(false);
  }, []);

  useEffect(() => {
    if (ready) refresh();
  }, [ready, refresh]);

  if (!ready) return null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold mb-1">Today</h1>
        <p className="text-sm text-muted">
          Type a command — it&apos;s parsed by an LLM, routed through a Supervisor Agent to the
          right specialist, and executed safely.
        </p>
      </div>

      <CommandBar onExecuted={refresh} />

      {pending.length > 0 && (
        <div className="card border-warn/40 bg-amber-50/40">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-semibold text-warn">
              {pending.length} command{pending.length === 1 ? "" : "s"} waiting on you
            </h2>
            <Link href="/commands" className="text-xs text-accent underline">
              Review all
            </Link>
          </div>
          <ul className="space-y-1 text-sm">
            {pending.slice(0, 3).map((c) => (
              <li key={c.id} className="text-muted">
                &ldquo;{c.transcript}&rdquo;
              </li>
            ))}
          </ul>
        </div>
      )}

      {loading && <p className="text-sm text-muted">Loading...</p>}

      {dashboard && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Metric label="Sales" value={`₹${dashboard.total_sales_amount}`} />
          <Metric label="Expenses" value={`₹${dashboard.total_expenses_amount}`} />
          <Metric label="Profit" value={`₹${dashboard.profit}`} />
          <Metric label="Customer dues" value={`₹${dashboard.total_customer_dues}`} />
        </div>
      )}

      <div className="grid sm:grid-cols-2 gap-4">
        {lowStock.length > 0 && (
          <div className="card">
            <h2 className="text-sm font-semibold mb-3">Low stock</h2>
            <ul className="space-y-1.5 text-sm">
              {lowStock.map((p) => (
                <li key={p.id} className="flex justify-between">
                  <span>{p.name}</span>
                  <span className="text-warn">{p.stock_quantity} left</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {reminders.length > 0 && (
          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold">Reminders</h2>
              <Link href="/reminders" className="text-xs text-accent underline">
                View all
              </Link>
            </div>
            <ul className="space-y-1.5 text-sm">
              {reminders.slice(0, 4).map((r) => (
                <li key={r.id}>{r.message}</li>
              ))}
            </ul>
          </div>
        )}

        {insights.length > 0 && (
          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold">Advisor insights</h2>
              <Link href="/insights" className="text-xs text-accent underline">
                View all
              </Link>
            </div>
            <ul className="space-y-1.5 text-sm">
              {insights.map((i) => (
                <li key={i.id}>{i.message}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
