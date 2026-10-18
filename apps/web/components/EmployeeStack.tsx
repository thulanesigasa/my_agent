"use client";

import React from "react";

export interface AgentEmployee {
  id: string;
  name: string;
}

export const AGENT_EMPLOYEES: AgentEmployee[] = [
  { id: "reports_agent", name: "reports_agent" },
  { id: "email_agent", name: "email_agent" },
  { id: "project_manager", name: "project_manager" },
  { id: "research_agent", name: "research_agent" },
];

interface EmployeeStackProps {
  activeAgentId?: string;
  onSelectAgent?: (id: string) => void;
}

export default function EmployeeStack({ activeAgentId = "reports_agent", onSelectAgent }: EmployeeStackProps) {
  return (
    <div style={{
      width: "100%",
      background: "transparent",
      border: "none",
      boxShadow: "none",
      padding: "clamp(4px, 0.8vh, 8px) clamp(4px, 1vw, 10px)",
      display: "flex",
      flexDirection: "column",
      gap: "clamp(2px, 0.5vh, 4px)",
      flexShrink: 1,
      minHeight: 0,
      overflow: "hidden",
    }}>
      {/* Roster Header */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        paddingBottom: "clamp(2px, 0.4vh, 4px)",
      }}>
        <span style={{ fontSize: "clamp(11px, 1.4vh, 13px)", fontWeight: 700, color: "#0f172a" }}>
          AI Employees
        </span>
      </div>

      {/* Centered Shorter Header Divider Line */}
      <div style={{
        width: "75%",
        margin: "0 auto clamp(2px, 0.4vh, 4px)",
        height: 1,
        background: "rgba(226, 232, 240, 0.7)",
      }} />

      {/* Employee List (In-Place Agent Switcher) */}
      <div style={{ display: "flex", flexDirection: "column" }}>
        {AGENT_EMPLOYEES.map((agent, index) => {
          const isActive = agent.id === activeAgentId;
          const isLast = index === AGENT_EMPLOYEES.length - 1;

          return (
            <React.Fragment key={agent.id}>
              <div
                onClick={() => onSelectAgent && onSelectAgent(agent.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "clamp(4px, 0.8vh, 7px) 4px",
                  cursor: "pointer",
                  borderRadius: 6,
                  background: isActive ? "rgba(236, 72, 153, 0.05)" : "transparent",
                  transition: "all 150ms ease",
                }}
              >
                <span style={{
                  fontSize: "clamp(10px, 1.3vh, 12px)",
                  fontWeight: isActive ? 700 : 500,
                  color: isActive ? "#0f172a" : "#475569",
                }}>
                  {agent.name}
                </span>

                {/* Status Dot: Pink Dot (Active) | Gray Dot (Sleeping) */}
                <span style={{
                  width: "clamp(6px, 1vh, 8px)",
                  height: "clamp(6px, 1vh, 8px)",
                  borderRadius: "50%",
                  background: isActive ? "#ec4899" : "#94a3b8",
                  boxShadow: isActive ? "0 0 6px rgba(236, 72, 153, 0.6)" : "none",
                }} />
              </div>

              {!isLast && (
                <div style={{
                  width: "75%",
                  margin: "1px auto",
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
