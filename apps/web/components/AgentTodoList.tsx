"use client";

import React, { useState } from "react";
import { CheckCircle2, Circle, ListTodo, Plus, Sparkles, Trash2 } from "lucide-react";

export interface TaskItem {
  id: string;
  agentId: string;
  title: string;
  completed: boolean;
  priority: "High" | "Medium" | "Low";
}

const INITIAL_TASKS: TaskItem[] = [
  {
    id: "t1",
    agentId: "reports_agent",
    title: "Generate Q3 Weekly Performance Report",
    completed: true,
    priority: "High",
  },
  {
    id: "t2",
    agentId: "reports_agent",
    title: "Export Lead Analytics & Conversion PDF",
    completed: false,
    priority: "Medium",
  },
  {
    id: "t3",
    agentId: "email_agent",
    title: "Dispatch 250 Cold Outreach Emails",
    completed: true,
    priority: "High",
  },
  {
    id: "t4",
    agentId: "email_agent",
    title: "Process Inbox Responses & Draft Replies",
    completed: false,
    priority: "High",
  },
  {
    id: "t5",
    agentId: "project_manager",
    title: "Update Sprint Backlog & Ticket Deadlines",
    completed: false,
    priority: "Medium",
  },
  {
    id: "t6",
    agentId: "research_agent",
    title: "Scrape Target Prospect Profiles & Emails",
    completed: false,
    priority: "Low",
  },
];

interface AgentTodoListProps {
  activeAgentId: string;
  activeAgentName: string;
}

export default function AgentTodoList({ activeAgentId, activeAgentName }: AgentTodoListProps) {
  const [tasks, setTasks] = useState<TaskItem[]>(INITIAL_TASKS);
  const [newTaskTitle, setNewTaskTitle] = useState("");

  const filteredTasks = tasks.filter((t) => t.agentId === activeAgentId);
  const completedCount = filteredTasks.filter((t) => t.completed).length;
  const progressPercent = filteredTasks.length > 0 ? Math.round((completedCount / filteredTasks.length) * 100) : 0;

  const toggleTask = (id: string) => {
    setTasks((prev) =>
      prev.map((t) => (t.id === id ? { ...t, completed: !t.completed } : t))
    );
  };

  const handleAddTask = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTaskTitle.trim()) return;

    const newTask: TaskItem = {
      id: `task_${Date.now()}`,
      agentId: activeAgentId,
      title: newTaskTitle.trim(),
      completed: false,
      priority: "Medium",
    };

    setTasks((prev) => [newTask, ...prev]);
    setNewTaskTitle("");
  };

  const deleteTask = (id: string) => {
    setTasks((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <div style={{
      width: "100%",
      height: "100%",
      maxHeight: "calc(100vh - 100px)",
      background: "linear-gradient(135deg, rgba(255, 255, 255, 0.75), rgba(255, 255, 255, 0.45))",
      backdropFilter: "blur(20px)",
      WebkitBackdropFilter: "blur(20px)",
      border: "1px solid rgba(255, 255, 255, 0.7)",
      borderRadius: 20,
      padding: "20px",
      boxShadow: "inset 0 1px 1px rgba(255, 255, 255, 0.9), 0 12px 32px rgba(15, 23, 42, 0.06)",
      display: "flex",
      flexDirection: "column",
      gap: 16,
    }}>
      {/* Glossy Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 10,
            background: "linear-gradient(135deg, #ec4899, #f43f5e)",
            color: "#ffffff",
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 4px 12px rgba(236, 72, 153, 0.3)",
          }}>
            <ListTodo size={18} />
          </div>
          <div>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: "#0f172a", margin: 0 }}>
              Daily To-Do List
            </h3>
            <span style={{ fontSize: 11, color: "#64748b" }}>
              {activeAgentName} Tasks
            </span>
          </div>
        </div>

        <div style={{
          padding: "4px 10px", borderRadius: 999,
          background: "rgba(236, 72, 153, 0.1)",
          border: "1px solid rgba(236, 72, 153, 0.2)",
          color: "#ec4899", fontSize: 11, fontWeight: 700,
          display: "flex", alignItems: "center", gap: 4,
        }}>
          <Sparkles size={12} />
          <span>{completedCount}/{filteredTasks.length} Done</span>
        </div>
      </div>

      {/* Daily Progress Bar */}
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, fontWeight: 600, color: "#64748b" }}>
          <span>Daily Progress</span>
          <span>{progressPercent}%</span>
        </div>
        <div style={{ width: "100%", height: 6, borderRadius: 999, background: "rgba(226, 232, 240, 0.8)", overflow: "hidden" }}>
          <div style={{
            width: `${progressPercent}%`, height: "100%",
            borderRadius: 999,
            background: "linear-gradient(90deg, #ec4899, #f43f5e)",
            transition: "width 300ms ease-in-out",
          }} />
        </div>
      </div>

      {/* Add Task Input Form */}
      <form onSubmit={handleAddTask} style={{ display: "flex", gap: 8 }}>
        <input
          value={newTaskTitle}
          onChange={(e) => setNewTaskTitle(e.target.value)}
          placeholder={`Add task for ${activeAgentName}...`}
          style={{
            flex: 1,
            padding: "8px 14px",
            borderRadius: 10,
            border: "1px solid rgba(226, 232, 240, 0.9)",
            background: "rgba(255, 255, 255, 0.8)",
            fontSize: 12,
            color: "#0f172a",
            outline: "none",
          }}
        />
        <button
          type="submit"
          style={{
            padding: "8px 12px",
            borderRadius: 10,
            border: "none",
            background: "#0f172a",
            color: "#ffffff",
            fontSize: 12,
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 4,
          }}
        >
          <Plus size={14} />
          <span>Add</span>
        </button>
      </form>

      {/* Task Items Stream */}
      <div style={{
        flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 8,
        paddingRight: 4,
      }}>
        {filteredTasks.length === 0 ? (
          <div style={{ textAlign: "center", padding: "24px 0", color: "#94a3b8", fontSize: 12 }}>
            No tasks queued for this agent today.
          </div>
        ) : (
          filteredTasks.map((task) => (
            <div
              key={task.id}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "10px 12px",
                borderRadius: 12,
                background: task.completed ? "rgba(241, 245, 249, 0.6)" : "#ffffff",
                border: "1px solid rgba(226, 232, 240, 0.8)",
                boxShadow: "0 2px 8px rgba(0, 0, 0, 0.02)",
                opacity: task.completed ? 0.7 : 1,
                transition: "all 150ms ease",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10, flex: 1, marginRight: 8 }}>
                <button
                  onClick={() => toggleTask(task.id)}
                  style={{
                    background: "none", border: "none", cursor: "pointer",
                    padding: 0, color: task.completed ? "#ec4899" : "#94a3b8",
                    display: "flex", alignItems: "center",
                  }}
                >
                  {task.completed ? <CheckCircle2 size={18} /> : <Circle size={18} />}
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

              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                {/* Priority Badge */}
                <span style={{
                  fontSize: 9, fontWeight: 700, padding: "2px 6px", borderRadius: 4,
                  background: task.priority === "High" ? "rgba(239, 68, 68, 0.1)" : task.priority === "Medium" ? "rgba(245, 158, 11, 0.1)" : "rgba(148, 163, 184, 0.1)",
                  color: task.priority === "High" ? "#dc2626" : task.priority === "Medium" ? "#d97706" : "#64748b",
                }}>
                  {task.priority}
                </span>
                <button
                  onClick={() => deleteTask(task.id)}
                  style={{
                    background: "none", border: "none", cursor: "pointer",
                    padding: 2, color: "#cbd5e1", display: "flex", alignItems: "center",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.color = "#ef4444")}
                  onMouseLeave={(e) => (e.currentTarget.style.color = "#cbd5e1")}
                >
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
