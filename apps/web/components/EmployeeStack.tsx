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
      border: "none",
      boxShadow: "none",
      padding: "8px 4px",
      display: "flex",
      flexDirection: "column",
      gap: 4,
    }}>
      {/* Roster Header */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        paddingBottom: 4,
      }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>
          AI Employees
        </span>
      </div>

      {/* Centered Shorter Header Divider Line */}
      <div style={{
        width: "75%",
        margin: "0 auto 4px",
        height: 1,
        background: "rgba(226, 232, 240, 0.7)",
      }} />

      {/* Employee List (Minimalist Rows with Shorter Centered Separator Lines) */}
      <div style={{ display: "flex", flexDirection: "column" }}>
        {AGENT_EMPLOYEES.map((agent, index) => {
          const isActive = agent.id === activeAgentId;
          const isLast = index === AGENT_EMPLOYEES.length - 1;

          return (
            <React.Fragment key={agent.id}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "8px 4px",
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
        })}
      </div>
    </div>
  );
}
