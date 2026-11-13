"use client";

import { ActivityPanel } from "./dashboard/activity";

interface AgentTodoListProps {
  activeAgentId: string;
  activeAgentName: string;
}

export default function AgentTodoList({ activeAgentId, activeAgentName }: AgentTodoListProps) {
  return (
    <div data-agent={activeAgentId} className="w-full h-full min-h-0 overflow-y-auto text-slate-800">
      <p className="text-xs text-slate-500 mb-3">
        Selected: {activeAgentName || "No agent"}. Per-agent task assignments are not connected yet.
      </p>
      <ActivityPanel />
    </div>
  );
}
