"use client";

import { useEffect, useState, useCallback, Fragment } from "react";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { api, ApiError } from "@/lib/apiClient";
import type { Product } from "@/lib/types";

function AdjustStockRow({ product, onDone }: { product: Product; onDone: () => void }) {
  const [change, setChange] = useState("");
  const [confirmNeg, setConfirmNeg] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit() {
    if (!change) return;
    setError(null);
    setLoading(true);
    try {
      await api.adjustStock(product.id, {
        quantity_change: Number(change),
        reference_type: "manual",
        confirm_negative_stock: confirmNeg,
      });
      setChange("");
      setConfirmNeg(false);
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? String(err.message) : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <tr className="border-t border-line bg-paper/60">
      <td colSpan={4} className="px-4 py-2">
        <div className="flex items-center gap-2 flex-wrap">
          <input
            type="number"
            placeholder="+10 to add, -5 to deduct"
            value={change}
            onChange={(e) => setChange(e.target.value)}
            className="w-48 text-xs"
          />
          <label className="flex items-center gap-1 text-xs text-muted">
            <input
              type="checkbox"
              className="w-auto"
              checked={confirmNeg}
              onChange={(e) => setConfirmNeg(e.target.checked)}
            />
            Allow negative stock
          </label>
          <button onClick={submit} disabled={loading} className="btn-secondary text-xs">
            {loading ? "Saving..." : "Apply"}
          </button>
          {error && <span className="text-xs text-warn">{error}</span>}
        </div>
      </td>
    </tr>
  );
}

export default function ProductsPage() {
  const { ready } = useRequireAuth();
  const [products, setProducts] = useState<Product[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [adjustingId, setAdjustingId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [stock, setStock] = useState("0");
  const [reorder, setReorder] = useState("0");
  const [price, setPrice] = useState("0");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setProducts(await api.listProducts());
  }, []);

  useEffect(() => {
    if (ready) refresh();
  }, [ready, refresh]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.createProduct({
        name,
        stock_quantity: Number(stock),
        reorder_level: Number(reorder),
        selling_price: Number(price),
      });
      setName("");
      setStock("0");
      setReorder("0");
      setPrice("0");
      setShowForm(false);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? String(err.message) : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  if (!ready) return null;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-lg font-semibold">Products</h1>
        <button className="btn-secondary text-sm" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "Add product"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="card grid sm:grid-cols-4 gap-3 items-end">
          <div className="sm:col-span-1">
            <label className="label">Name</label>
            <input required value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <label className="label">Stock qty</label>
            <input type="number" value={stock} onChange={(e) => setStock(e.target.value)} />
          </div>
          <div>
            <label className="label">Reorder level</label>
            <input type="number" value={reorder} onChange={(e) => setReorder(e.target.value)} />
          </div>
          <div>
            <label className="label">Selling price</label>
            <input type="number" value={price} onChange={(e) => setPrice(e.target.value)} />
          </div>
          <div className="sm:col-span-4">
            {error && <p className="text-sm text-warn mb-2">{error}</p>}
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? "Saving..." : "Save product"}
            </button>
          </div>
        </form>
      )}

      <div className="card p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-paper text-muted text-xs">
            <tr>
              <th className="text-left px-4 py-2 font-medium">Name</th>
              <th className="text-left px-4 py-2 font-medium">Stock</th>
              <th className="text-left px-4 py-2 font-medium">Price</th>
              <th className="text-left px-4 py-2 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {products.map((p) => (
              <>
                <tr key={p.id} className="border-t border-line">
                  <td className="px-4 py-2">{p.name}</td>
                  <td className="px-4 py-2">{p.stock_quantity}</td>
                  <td className="px-4 py-2">₹{p.selling_price}</td>
                  <td className="px-4 py-2 text-right">
                    {p.is_low_stock && (
                      <span className="text-xs text-warn bg-warn/10 px-2 py-0.5 rounded-full mr-2">
                        Low stock
                      </span>
                    )}
                    <button
                      onClick={() => setAdjustingId(adjustingId === p.id ? null : p.id)}
                      className="text-xs text-accent underline"
                    >
                      {adjustingId === p.id ? "Close" : "Adjust stock"}
                    </button>
                  </td>
                </tr>
                {adjustingId === p.id && (
                  <AdjustStockRow
                    key={`${p.id}-adjust`}
                    product={p}
                    onDone={() => {
                      setAdjustingId(null);
                      refresh();
                    }}
                  />
                )}
              </>
            ))}
            {products.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-muted text-sm">
                  No products yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
