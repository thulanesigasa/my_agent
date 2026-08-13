"use client";

import React from "react";
import { BarChart3, Mail, FolderKanban, Globe, Moon, Zap, Users } from "lucide-react";

export interface AgentEmployee {
  id: string;
  name: string;
  role: string;
  icon: React.ElementType;
}

export const AGENT_EMPLOYEES: AgentEmployee[] = [
  {
    id: "reports_agent",
    name: "Reports Agent",
    role: "Responsible for Reports & Analytics",
    icon: BarChart3,
  },
  {
    id: "email_agent",
    name: "Email Agent",
    role: "Responsible for Sending Mail & Communications",
    icon: Mail,
  },
  {
    id: "project_manager",
    name: "Project Manager Agent",
    role: "Responsible for Project Management & Sprints",
    icon: FolderKanban,
  },
  {
    id: "research_agent",
    name: "Research Agent",
    role: "Responsible for Data Scraping & Web Research",
    icon: Globe,
  },
];

interface EmployeeStackProps {
  activeAgentId: string;
  onSelectAgent: (id: string) => void;
}

export default function EmployeeStack({ activeAgentId, onSelectAgent }: EmployeeStackProps) {
  return (
    <div style={{
      width: "100%",
      background: "rgba(255, 255, 255, 0.85)",
      backdropFilter: "blur(12px)",
      border: "1px solid rgba(226, 232, 240, 0.8)",
      borderRadius: 16,
      padding: "16px",
      boxShadow: "0 4px 20px rgba(0, 0, 0, 0.03)",
      display: "flex",
      flexDirection: "column",
      gap: 12,
    }}>
      {/* Roster Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{
            width: 28, height: 28, borderRadius: 8,
            background: "rgba(15, 23, 42, 0.08)",
            display: "flex", alignItems: "center", justifyContent: "center",
            color: "#0f172a",
          }}>
            <Users size={16} />
          </div>
          <span style={{ fontSize: 14, fontWeight: 700, color: "#0f172a" }}>
            AI Employee Roster
          </span>
        </div>
        <span style={{ fontSize: 11, fontWeight: 600, color: "#64748b" }}>
          4 Agents
        </span>
      </div>

      {/* Employee List */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {AGENT_EMPLOYEES.map((agent) => {
          const isActive = agent.id === activeAgentId;
          const Icon = agent.icon;

          return (
            <div
              key={agent.id}
              onClick={() => onSelectAgent(agent.id)}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "10px 12px",
                borderRadius: 12,
                cursor: "pointer",
                background: isActive ? "#ffffff" : "rgba(248, 250, 252, 0.7)",
                border: isActive ? "1px solid rgba(236, 72, 153, 0.4)" : "1px solid rgba(241, 245, 249, 0.8)",
                boxShadow: isActive ? "0 4px 12px rgba(236, 72, 153, 0.12)" : "none",
                transition: "all 150ms ease",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{
                  width: 32, height: 32, borderRadius: 8,
                  background: isActive ? "#ec4899" : "#0f172a",
                  color: "#ffffff",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  transition: "background 150ms ease",
                }}>
                  <Icon size={16} />
                </div>

                <div style={{ display: "flex", flexDirection: "column" }}>
                  <span style={{ fontSize: 12, fontWeight: 700, color: "#0f172a" }}>
                    {agent.name}
                  </span>
                  <span style={{ fontSize: 10, color: "#64748b", maxWidth: 150, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {agent.role}
                  </span>
                </div>
              </div>

              {/* Status Badge */}
              {isActive ? (
                <div style={{
                  display: "flex", alignItems: "center", gap: 5,
                  padding: "3px 8px", borderRadius: 999,
                  background: "rgba(16, 185, 129, 0.1)",
                  border: "1px solid rgba(16, 185, 129, 0.3)",
                  color: "#059669", fontSize: 10, fontWeight: 700,
                }}>
                  <Zap size={11} />
                  <span>Active</span>
                </div>
              ) : (
                <div style={{
                  display: "flex", alignItems: "center", gap: 5,
                  padding: "3px 8px", borderRadius: 999,
                  background: "rgba(148, 163, 184, 0.1)",
                  border: "1px solid rgba(148, 163, 184, 0.2)",
                  color: "#64748b", fontSize: 10, fontWeight: 600,
                }}>
                  <Moon size={11} />
                  <span>Asleep</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
