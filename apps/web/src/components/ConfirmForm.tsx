"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/apiClient";
import type { VoiceCommandResponse } from "@/lib/types";

export function ConfirmForm({
  command,
  onConfirmed,
}: {
  command: VoiceCommandResponse;
  onConfirmed: (updated: VoiceCommandResponse) => void;
}) {
  const [productId, setProductId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [unitPrice, setUnitPrice] = useState("");
  const [negStock, setNegStock] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleConfirm() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.confirmVoiceCommand(command.id, {
        product_id: productId || undefined,
        quantity: quantity ? Number(quantity) : undefined,
        unit_price: unitPrice ? Number(unitPrice) : undefined,
        confirm_negative_stock: negStock,
      });
      onConfirmed(res);
    } catch (err) {
      setError(err instanceof ApiError ? String(err.message) : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="border-t border-line pt-3 mt-3 space-y-2">
      <p className="text-xs text-muted">
        The AI understood this as best it could, but flagged it for confirmation - see above for
        why. Fill in what&apos;s needed (leave blank to keep the originally detected value), then
        confirm. Confirming will execute a real business action (stock/transaction change).
      </p>
      <div className="grid grid-cols-2 gap-2">
        <input
          placeholder="product_id (if not found)"
          value={productId}
          onChange={(e) => setProductId(e.target.value)}
          className="text-xs"
        />
        <input
          placeholder="quantity override"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          className="text-xs"
        />
        <input
          placeholder="unit_price override"
          value={unitPrice}
          onChange={(e) => setUnitPrice(e.target.value)}
          className="text-xs"
        />
        <label className="flex items-center gap-1.5 text-xs">
          <input
            type="checkbox"
            className="w-auto"
            checked={negStock}
            onChange={(e) => setNegStock(e.target.checked)}
          />
          Allow negative stock
        </label>
      </div>
      {error && <p className="text-xs text-warn">{error}</p>}
      <button onClick={handleConfirm} disabled={loading} className="btn-secondary text-xs">
        {loading ? "Confirming..." : "Confirm & execute"}
      </button>
    </div>
  );
}
