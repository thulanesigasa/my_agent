"use client";

import React, { useState } from "react";
import { CheckCircle2, Circle } from "lucide-react";

export interface TaskItem {
  id: string;
  agentId: string;
  title: string;
  completed: boolean;
}

const INITIAL_TASKS: TaskItem[] = [
  {
    id: "t1",
    agentId: "reports_agent",
    title: "Generate Q3 Weekly Performance Report",
    completed: true,
  },
  {
    id: "t2",
    agentId: "reports_agent",
    title: "Export Lead Analytics & Conversion PDF",
    completed: false,
  },
  {
    id: "t3",
    agentId: "email_agent",
    title: "Dispatch 250 Cold Outreach Emails",
    completed: true,
  },
  {
    id: "t4",
    agentId: "email_agent",
    title: "Process Inbox Responses & Draft Replies",
    completed: false,
  },
  {
    id: "t5",
    agentId: "project_manager",
    title: "Update Sprint Backlog & Ticket Deadlines",
    completed: false,
  },
  {
    id: "t6",
    agentId: "research_agent",
    title: "Scrape Target Prospect Profiles & Emails",
    completed: false,
  },
];

interface AgentTodoListProps {
  activeAgentId: string;
  activeAgentName: string;
}

export default function AgentTodoList({ activeAgentId, activeAgentName }: AgentTodoListProps) {
  const [tasks, setTasks] = useState<TaskItem[]>(INITIAL_TASKS);

  const filteredTasks = tasks.filter((t) => t.agentId === activeAgentId);
  const completedCount = filteredTasks.filter((t) => t.completed).length;
  const progressPercent = filteredTasks.length > 0 ? Math.round((completedCount / filteredTasks.length) * 100) : 0;

  const toggleTask = (id: string) => {
    setTasks((prev) =>
      prev.map((t) => (t.id === id ? { ...t, completed: !t.completed } : t))
    );
  };

  return (
    <div style={{
      width: "100%",
      height: "100%",
      maxHeight: "calc(100vh - 100px)",
      background: "transparent",
      border: "none",
      boxShadow: "none",
      padding: "8px 4px",
      display: "flex",
      flexDirection: "column",
      gap: 12,
    }}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        paddingBottom: 4,
      }}>
        <div>
          <h3 style={{ fontSize: 13, fontWeight: 700, color: "#0f172a", margin: 0 }}>
            Daily To-Do List
          </h3>
          <span style={{ fontSize: 11, color: "#64748b" }}>
            {activeAgentName} Tasks
          </span>
        </div>
      </div>

      {/* Centered Shorter Header Divider Line */}
      <div style={{
        width: "75%",
        margin: "0 auto 4px",
        height: 1,
        background: "rgba(226, 232, 240, 0.7)",
      }} />

      {/* Daily Progress Bar */}
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, fontWeight: 600, color: "#64748b" }}>
          <span>Agent Progress</span>
          <span>{progressPercent}%</span>
        </div>
        <div style={{ width: "100%", height: 5, borderRadius: 999, background: "rgba(226, 232, 240, 0.8)", overflow: "hidden" }}>
          <div style={{
            width: `${progressPercent}%`, height: "100%",
            borderRadius: 999,
            background: "linear-gradient(90deg, #ec4899, #f43f5e)",
            transition: "width 300ms ease-in-out",
          }} />
        </div>
      </div>

      {/* Task Items Stream (Minimalist Rows with Shorter Centered Separator Lines) */}
      <div style={{
        flex: 1, overflowY: "auto", display: "flex", flexDirection: "column",
        paddingRight: 2,
      }}>
        {filteredTasks.length === 0 ? (
          <div style={{ textAlign: "center", padding: "20px 0", color: "#94a3b8", fontSize: 11 }}>
            No daily tasks assigned to this agent yet.
          </div>
        ) : (
          filteredTasks.map((task, index) => {
            const isLast = index === filteredTasks.length - 1;
            return (
              <React.Fragment key={task.id}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "10px 4px",
                    opacity: task.completed ? 0.6 : 1,
                    transition: "all 150ms ease",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flex: 1 }}>
                    <button
                      onClick={() => toggleTask(task.id)}
                      style={{
                        background: "none", border: "none", cursor: "pointer",
                        padding: 0, color: task.completed ? "#ec4899" : "#94a3b8",
                        display: "flex", alignItems: "center",
                      }}
                    >
                      {task.completed ? <CheckCircle2 size={16} /> : <Circle size={16} />}
                    </button>
                    <span style={{
                      fontSize: 12,
                      fontWeight: 500,
                      color: task.completed ? "#64748b" : "#0f172a",
                      textDecoration: task.completed ? "line-through" : "none",
                    }}>
                      {task.title}
                    </span>
                  </div>
                </div>

                {!isLast && (
                  <div style={{
                    width: "75%",
                    margin: "2px auto",
                    height: 1,
                    background: "rgba(226, 232, 240, 0.6)",
                  }} />
                )}
              </React.Fragment>
            );
          })
        )}
      </div>
    </div>
  );
}
