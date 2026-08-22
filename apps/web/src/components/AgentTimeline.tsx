"use client";

import { useState } from "react";
import type { AgentTask, VoiceCommandResponse } from "@/lib/types";

const AGENT_LABELS: Record<string, string> = {
  rule_based: "Rule-based parser (fallback)",
  nvidia_nim: "LLM parser (NVIDIA NIM)",
  finance_agent: "Finance Agent",
  inventory_agent: "Inventory Agent",
  rag_agent: "RAG Agent",
  advisor_agent: "Advisor Agent",
  clarification_agent: "Clarification Agent",
};

function agentLabel(name: string) {
  return AGENT_LABELS[name] || name;
}

function StatusDot({ status }: { status: string }) {
  const color =
    status === "SUCCESS" || status === "COMPLETED"
      ? "bg-accent"
      : status === "FAILED"
        ? "bg-red-500"
        : "bg-warn";
  return <span className={`w-2 h-2 rounded-full ${color} shrink-0 mt-1.5`} />;
}

function JsonDetail({ label, data }: { label: string; data: Record<string, unknown> }) {
  const [open, setOpen] = useState(false);
  if (!data || Object.keys(data).length === 0) return null;
  return (
    <div className="mt-1">
      <button
        onClick={() => setOpen((v) => !v)}
        className="text-xs text-muted underline decoration-dotted"
      >
        {open ? "hide" : "show"} {label}
      </button>
      {open && (
        <pre className="mt-1 text-[11px] bg-paper border border-line rounded p-2 overflow-auto font-mono">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}

/**
 * Renders the real agent_tasks trace for a command as a step-by-step
 * timeline, bookended by two UI-only markers ("Command received" /
 * final outcome) that are directly derived from the command's own real
 * fields (transcript, status, final_response) — not invented data, just
 * the same real values framed as the first/last step of the flow.
 */
export function AgentTimeline({
  command,
  tasks,
}: {
  command: VoiceCommandResponse;
  tasks: AgentTask[];
}) {
  return (
    <ol className="space-y-3">
      <li className="flex gap-3">
        <StatusDot status="SUCCESS" />
        <div className="text-sm">
          <p className="font-medium">Command received</p>
          <p className="text-muted text-xs mt-0.5">&ldquo;{command.transcript}&rdquo;</p>
        </div>
      </li>

      {tasks.map((task) => (
        <li key={task.id} className="flex gap-3">
          <StatusDot status={task.status} />
          <div className="text-sm flex-1">
            <p className="font-medium">
              {agentLabel(task.agent_name)}
              {task.tool_name && <span className="text-muted font-normal"> → {task.tool_name}</span>}
            </p>
            <p className="text-xs text-muted">{task.status}</p>
            <JsonDetail label="input" data={task.input_json} />
            <JsonDetail label="result" data={task.output_json} />
          </div>
        </li>
      ))}

      <li className="flex gap-3">
        <StatusDot status={command.status} />
        <div className="text-sm">
          <p className="font-medium">
            {command.status === "COMPLETED"
              ? "Completed"
              : command.status === "NEEDS_CONFIRMATION"
                ? "Needs confirmation"
                : command.status === "FAILED"
                  ? "Failed"
                  : command.status}
          </p>
          {command.final_response && (
            <p className="text-muted text-xs mt-0.5">{command.final_response}</p>
          )}
        </div>
      </li>
    </ol>
  );
}
