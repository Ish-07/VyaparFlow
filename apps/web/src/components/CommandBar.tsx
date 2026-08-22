"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/apiClient";
import type { AgentTask, VoiceCommandResponse } from "@/lib/types";
import { AgentTimeline } from "./AgentTimeline";
import { ConfirmForm } from "./ConfirmForm";

function newIdempotencyKey() {
  return `web-${Date.now()}-${Math.floor(Math.random() * 100000)}`;
}

const STATUS_STYLES: Record<string, string> = {
  COMPLETED: "bg-accent/10 text-accent-dark border-accent/30",
  NEEDS_CONFIRMATION: "bg-amber-50 text-warn border-warn/30",
  FAILED: "bg-red-50 text-red-700 border-red-200",
};

export function CommandBar({ onExecuted }: { onExecuted?: () => void }) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<VoiceCommandResponse | null>(null);
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [showTimeline, setShowTimeline] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadTasks(commandId: string) {
    try {
      setTasks(await api.getVoiceCommandTasks(commandId));
    } catch {
      // Non-critical — the summary still works without the trace.
      setTasks([]);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setTasks([]);
    setShowTimeline(false);
    try {
      const res = await api.submitVoiceCommand({ text, idempotency_key: newIdempotencyKey() });
      setResult(res);
      await loadTasks(res.id);
      if (res.status === "COMPLETED") {
        setText("");
        onExecuted?.();
      }
    } catch (err) {
      setError(err instanceof ApiError ? String(err.message) : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  function handleConfirmed(updated: VoiceCommandResponse) {
    setResult(updated);
    loadTasks(updated.id);
    if (updated.status === "COMPLETED") {
      setText("");
      onExecuted?.();
    }
  }

  // Which agent actually parsed this — surfaces "LLM vs fallback" per the
  // real agent_tasks trace, not a guess.
  const parserTask = tasks.find((t) => t.tool_name === "parse_command");

  return (
    <div className="card">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          placeholder='Try: "sold 5 pickle bottles for 100 rupees each" or ask a question about your documents'
          value={text}
          onChange={(e) => setText(e.target.value)}
          className="flex-1"
        />
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? "Thinking..." : "Send"}
        </button>
      </form>

      {error && <p className="text-sm text-warn mt-3">{error}</p>}

      {result && (
        <div className={`mt-4 border rounded-md p-3 text-sm ${STATUS_STYLES[result.status] || "bg-paper"}`}>
          <div className="flex justify-between items-center mb-1">
            <span className="font-medium">{result.status.replace("_", " ")}</span>
            <div className="flex items-center gap-2 text-xs opacity-70">
              {result.intent && <span>{result.intent}</span>}
              {result.confidence !== null && <span>· {(result.confidence * 100).toFixed(0)}% confidence</span>}
              {parserTask && (
                <span title="Which parser produced this result">
                  · {parserTask.agent_name === "nvidia_nim" ? "LLM" : "fallback parser"}
                </span>
              )}
            </div>
          </div>
          {result.final_response && <p>{result.final_response}</p>}

          {result.status === "NEEDS_CONFIRMATION" && (
            <ConfirmForm command={result} onConfirmed={handleConfirmed} />
          )}

          {tasks.length > 0 && (
            <div className="mt-3 pt-3 border-t border-current/20">
              <button
                onClick={() => setShowTimeline((v) => !v)}
                className="text-xs underline decoration-dotted opacity-80"
              >
                {showTimeline ? "hide" : "show"} agent workflow ({tasks.length} step
                {tasks.length === 1 ? "" : "s"})
              </button>
              {showTimeline && (
                <div className="mt-3">
                  <AgentTimeline command={result} tasks={tasks} />
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
