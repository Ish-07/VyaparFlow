"use client";

import { useEffect, useState, useCallback } from "react";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { api } from "@/lib/apiClient";
import type { AgentTask, VoiceCommandResponse } from "@/lib/types";
import { AgentTimeline } from "@/components/AgentTimeline";
import { ConfirmForm } from "@/components/ConfirmForm";

const STATUS_STYLES: Record<string, string> = {
  COMPLETED: "bg-accent/10 text-accent-dark",
  NEEDS_CONFIRMATION: "bg-amber-50 text-warn",
  FAILED: "bg-red-50 text-red-700",
  PENDING: "bg-line/40 text-muted",
  UNDERSTANDING: "bg-line/40 text-muted",
  EXECUTING: "bg-line/40 text-muted",
};

function StatusBadge({ status }: { status: string }) {
  return <span className={`badge ${STATUS_STYLES[status] || "bg-line/40 text-muted"}`}>{status.replace("_", " ")}</span>;
}

export default function CommandsPage() {
  const { ready } = useRequireAuth();
  const [commands, setCommands] = useState<VoiceCommandResponse[]>([]);
  const [filter, setFilter] = useState<string>("");
  const [selected, setSelected] = useState<VoiceCommandResponse | null>(null);
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [loadingTasks, setLoadingTasks] = useState(false);

  const refresh = useCallback(async () => {
    setCommands(await api.listVoiceCommands(filter || undefined));
  }, [filter]);

  useEffect(() => {
    if (ready) refresh();
  }, [ready, refresh]);

  async function openCommand(cmd: VoiceCommandResponse) {
    setSelected(cmd);
    setLoadingTasks(true);
    try {
      setTasks(await api.getVoiceCommandTasks(cmd.id));
    } catch {
      setTasks([]);
    } finally {
      setLoadingTasks(false);
    }
  }

  function handleConfirmed(updated: VoiceCommandResponse) {
    setSelected(updated);
    setCommands((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
    openCommand(updated);
  }

  if (!ready) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Commands</h1>
          <p className="text-sm text-muted mt-0.5">
            Every command you&apos;ve sent, and exactly how the AI handled it — parser used,
            agents involved, and the outcome.
          </p>
        </div>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="w-auto text-sm"
        >
          <option value="">All statuses</option>
          <option value="COMPLETED">Completed</option>
          <option value="NEEDS_CONFIRMATION">Needs confirmation</option>
          <option value="FAILED">Failed</option>
        </select>
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-paper text-muted text-xs">
              <tr>
                <th className="text-left px-4 py-2 font-medium">Command</th>
                <th className="text-left px-4 py-2 font-medium">Intent</th>
                <th className="text-left px-4 py-2 font-medium">Status</th>
                <th className="text-left px-4 py-2 font-medium">When</th>
              </tr>
            </thead>
            <tbody>
              {commands.map((c) => (
                <tr
                  key={c.id}
                  onClick={() => openCommand(c)}
                  className={`border-t border-line cursor-pointer hover:bg-paper ${
                    selected?.id === c.id ? "bg-accent/5" : ""
                  }`}
                >
                  <td className="px-4 py-2 max-w-[240px] truncate" title={c.transcript || ""}>
                    {c.transcript}
                  </td>
                  <td className="px-4 py-2 text-muted">{c.intent || "—"}</td>
                  <td className="px-4 py-2">
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="px-4 py-2 text-muted text-xs">
                    {new Date(c.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
              {commands.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-muted text-sm">
                    No commands yet — try one from the Dashboard.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="card">
          {!selected && (
            <p className="text-sm text-muted">Select a command on the left to see its full agent workflow.</p>
          )}
          {selected && (
            <div className="space-y-3">
              <div>
                <p className="text-xs text-muted">&ldquo;{selected.transcript}&rdquo;</p>
                <div className="flex items-center gap-2 mt-1 text-xs">
                  <StatusBadge status={selected.status} />
                  {selected.intent && <span className="text-muted">{selected.intent}</span>}
                  {selected.confidence !== null && (
                    <span className="text-muted">{(selected.confidence * 100).toFixed(0)}% confidence</span>
                  )}
                </div>
              </div>

              {selected.status === "NEEDS_CONFIRMATION" && (
                <ConfirmForm command={selected} onConfirmed={handleConfirmed} />
              )}

              <div className="pt-2 border-t border-line">
                <h3 className="text-xs font-semibold text-muted mb-2">Agent workflow</h3>
                {loadingTasks ? (
                  <p className="text-sm text-muted">Loading...</p>
                ) : (
                  <AgentTimeline command={selected} tasks={tasks} />
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
