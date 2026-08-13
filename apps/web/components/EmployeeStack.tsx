"use client";

import React from "react";

export interface AgentEmployee {
  id: string;
  name: string;
}

export const AGENT_EMPLOYEES: AgentEmployee[] = [
  { id: "reports_agent", name: "Reports Agent" },
  { id: "email_agent", name: "Email Agent" },
  { id: "project_manager", name: "Project Manager Agent" },
  { id: "research_agent", name: "Research Agent" },
];

interface EmployeeStackProps {
  activeAgentId?: string;
  onSelectAgent?: (id: string) => void;
}

export default function EmployeeStack({ activeAgentId = "reports_agent" }: EmployeeStackProps) {
  return (
    <div style={{
      width: "100%",
      background: "transparent",
      border: "1px solid rgba(226, 232, 240, 0.5)",
      borderRadius: 16,
      padding: "12px 14px",
      display: "flex",
      flexDirection: "column",
      gap: 4,
    }}>
      {/* Roster Header */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        paddingBottom: 6, marginBottom: 2,
        borderBottom: "1px solid rgba(226, 232, 240, 0.7)",
      }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>
          AI Employees
        </span>
      </div>

      {/* Employee List (Minimalist Rows with Divider Lines) */}
      <div style={{ display: "flex", flexDirection: "column" }}>
        {AGENT_EMPLOYEES.map((agent, index) => {
          const isActive = agent.id === activeAgentId;
          const isLast = index === AGENT_EMPLOYEES.length - 1;

          return (
            <div
              key={agent.id}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "8px 4px",
                borderBottom: isLast ? "none" : "1px solid rgba(226, 232, 240, 0.6)",
              }}
            >
              <span style={{
                fontSize: 12,
                fontWeight: isActive ? 700 : 500,
                color: isActive ? "#0f172a" : "#475569",
              }}>
                {agent.name}
              </span>

              {/* Status Dot: Pink Dot (Active) | Gray Dot (Sleeping) */}
              <span style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: isActive ? "#ec4899" : "#94a3b8",
                boxShadow: isActive ? "0 0 8px rgba(236, 72, 153, 0.6)" : "none",
              }} />
            </div>
          );
        })}
      </div>
    </div>
  );
}
