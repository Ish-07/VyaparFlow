"use client";

import { useEffect, useState } from "react";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { api } from "@/lib/apiClient";
import type { AuditLog } from "@/lib/types";

const ENTITY_FILTERS = ["", "product", "transaction", "expense", "business"];

export default function AuditLogsPage() {
  const { ready } = useRequireAuth();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [entityType, setEntityType] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (ready) {
      setLoading(true);
      api.listAuditLogs(entityType ? { entity_type: entityType } : undefined).then((data) => {
        setLogs(data);
        setLoading(false);
      });
    }
  }, [ready, entityType]);

  if (!ready) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Audit log</h1>
          <p className="text-sm text-muted mt-0.5">
            An append-only record of every business-critical action, and who performed it —
            written by the backend service itself, not the AI, at the moment each action executes.
          </p>
        </div>
        <select value={entityType} onChange={(e) => setEntityType(e.target.value)} className="w-auto text-sm">
          {ENTITY_FILTERS.map((t) => (
            <option key={t} value={t}>
              {t ? t : "All entity types"}
            </option>
          ))}
        </select>
      </div>

      {loading && <p className="text-sm text-muted">Loading...</p>}

      <div className="card p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-paper text-muted text-xs">
            <tr>
              <th className="text-left px-4 py-2 font-medium">Action</th>
              <th className="text-left px-4 py-2 font-medium">Entity</th>
              <th className="text-left px-4 py-2 font-medium">Actor</th>
              <th className="text-left px-4 py-2 font-medium">Details</th>
              <th className="text-left px-4 py-2 font-medium">When</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id} className="border-t border-line align-top">
                <td className="px-4 py-2 font-medium">{log.action}</td>
                <td className="px-4 py-2 text-muted">
                  {log.entity_type}
                  {log.entity_id && (
                    <span className="text-xs block font-mono text-muted/70">
                      {log.entity_id.slice(0, 8)}...
                    </span>
                  )}
                </td>
                <td className="px-4 py-2 text-muted">
                  {log.actor_type}
                  {log.actor_id && (
                    <span className="text-xs block font-mono text-muted/70">
                      {log.actor_id.slice(0, 8)}...
                    </span>
                  )}
                </td>
                <td className="px-4 py-2 text-xs text-muted max-w-[280px]">
                  {Object.keys(log.metadata_json).length > 0
                    ? Object.entries(log.metadata_json)
                        .map(([k, v]) => `${k}: ${v}`)
                        .join(", ")
                    : "—"}
                </td>
                <td className="px-4 py-2 text-muted text-xs whitespace-nowrap">
                  {new Date(log.created_at).toLocaleString()}
                </td>
              </tr>
            ))}
            {!loading && logs.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-muted text-sm">
                  No audit entries yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
