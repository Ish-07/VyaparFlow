"use client";

import { useEffect, useState, useCallback, Fragment } from "react";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { api } from "@/lib/apiClient";
import type { Customer, Expense, Transaction } from "@/lib/types";

const PAYMENT_FILTERS = ["", "PAID", "DUE", "PARTIAL"];

export default function TransactionsPage() {
  const { ready } = useRequireAuth();
  const [tab, setTab] = useState<"sales" | "expenses">("sales");
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [customers, setCustomers] = useState<Record<string, Customer>>({});
  const [paymentStatus, setPaymentStatus] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [txns, custs] = await Promise.all([
      api.listTransactions({ type: "SALE", payment_status: paymentStatus || undefined }),
      api.listCustomers(),
    ]);
    setTransactions(txns);
    setCustomers(Object.fromEntries(custs.map((c) => [c.id, c])));
  }, [paymentStatus]);

  useEffect(() => {
    if (ready && tab === "sales") refresh();
  }, [ready, tab, refresh]);

  useEffect(() => {
    if (ready && tab === "expenses") api.listExpenses().then(setExpenses);
  }, [ready, tab]);

  if (!ready) return null;

  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold">Transactions</h1>

      <div className="flex items-center justify-between">
        <div className="flex gap-1 border-b border-line">
          {(["sales", "expenses"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`text-sm px-3 py-2 border-b-2 -mb-px capitalize transition-colors ${
                tab === t
                  ? "border-accent text-ink font-medium"
                  : "border-transparent text-muted hover:text-ink"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
        {tab === "sales" && (
          <select value={paymentStatus} onChange={(e) => setPaymentStatus(e.target.value)} className="w-auto text-sm">
            {PAYMENT_FILTERS.map((s) => (
              <option key={s} value={s}>
                {s || "All payment statuses"}
              </option>
            ))}
          </select>
        )}
      </div>

      {tab === "sales" && (
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-paper text-muted text-xs">
              <tr>
                <th className="text-left px-4 py-2 font-medium">Amount</th>
                <th className="text-left px-4 py-2 font-medium">Payment</th>
                <th className="text-left px-4 py-2 font-medium">Customer</th>
                <th className="text-left px-4 py-2 font-medium">Items</th>
                <th className="text-left px-4 py-2 font-medium">Date</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((t) => (
                <Fragment key={t.id}>
                  <tr
                    onClick={() => setExpanded(expanded === t.id ? null : t.id)}
                    className="border-t border-line cursor-pointer hover:bg-paper"
                  >
                    <td className="px-4 py-2 font-medium">₹{t.amount}</td>
                    <td className="px-4 py-2">
                      <span
                        className={`badge ${
                          t.payment_status === "PAID"
                            ? "bg-accent/10 text-accent-dark"
                            : "bg-amber-50 text-warn"
                        }`}
                      >
                        {t.payment_status}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-muted">
                      {t.customer_id ? customers[t.customer_id]?.name || "—" : "—"}
                    </td>
                    <td className="px-4 py-2 text-muted text-xs">
                      {t.items.length} item{t.items.length === 1 ? "" : "s"}
                    </td>
                    <td className="px-4 py-2 text-muted text-xs">
                      {new Date(t.occurred_at).toLocaleString()}
                    </td>
                  </tr>
                  {expanded === t.id && (
                    <tr className="bg-paper">
                      <td colSpan={5} className="px-4 py-3">
                        <table className="w-full text-xs">
                          <thead className="text-muted">
                            <tr>
                              <th className="text-left font-medium pb-1">Product</th>
                              <th className="text-left font-medium pb-1">Qty</th>
                              <th className="text-left font-medium pb-1">Unit price</th>
                              <th className="text-left font-medium pb-1">Total</th>
                            </tr>
                          </thead>
                          <tbody>
                            {t.items.map((item, i) => (
                              <tr key={i}>
                                <td className="py-0.5 font-mono text-[11px]">
                                  {item.product_id.slice(0, 8)}...
                                </td>
                                <td className="py-0.5">{item.quantity}</td>
                                <td className="py-0.5">₹{item.unit_price}</td>
                                <td className="py-0.5">₹{item.total}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
              {transactions.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-muted text-sm">
                    No sales yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {tab === "expenses" && (
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-paper text-muted text-xs">
              <tr>
                <th className="text-left px-4 py-2 font-medium">Category</th>
                <th className="text-left px-4 py-2 font-medium">Amount</th>
                <th className="text-left px-4 py-2 font-medium">Note</th>
                <th className="text-left px-4 py-2 font-medium">Date</th>
              </tr>
            </thead>
            <tbody>
              {expenses.map((e) => (
                <tr key={e.id} className="border-t border-line">
                  <td className="px-4 py-2">{e.category}</td>
                  <td className="px-4 py-2 font-medium">₹{e.amount}</td>
                  <td className="px-4 py-2 text-muted">{e.note || "—"}</td>
                  <td className="px-4 py-2 text-muted text-xs">
                    {new Date(e.occurred_at).toLocaleString()}
                  </td>
                </tr>
              ))}
              {expenses.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-muted text-sm">
                    No expenses yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
