"use client";
import React, { useContext } from "react";
import { TabContext } from "@/components/app-shell";
import { ActivityPanel } from "./dashboard/activity";
import { AnalyticsDashboard } from "./dashboard/analytics";
import { EmailLogsTable } from "./dashboard/email-logs";
import { ApprovalQueueDashboard } from "./dashboard/approval_queue";
import { MemoryViewer } from "./dashboard/memory-viewer";

export function Dashboard() {
  const { tab } = useContext(TabContext);
  return (
    <div className="p-6 space-y-6 text-slate-800">
      <h1 className="font-semibold text-lg">Email Outreach Command Centre</h1>
      {tab === "overview" && <><AnalyticsDashboard /><ActivityPanel /><EmailLogsTable /></>}
      {tab === "logs" && <EmailLogsTable />}
      {tab === "approvals" && <ApprovalQueueDashboard />}
      {tab === "memory" && <MemoryViewer />}
      {tab === "settings" && <p className="text-sm">Configure credentials in your local .env file and restart the application. Settings are not saved through this dashboard.</p>}
    </div>
  );
}
