"use client";
import React, { useContext } from "react";
import { TabContext } from "@/components/app-shell";
import { LeadsDashboard } from "./dashboard/leads";
import { ReportsDashboard } from "./dashboard/reports";
import { GmailSettings } from "./dashboard/gmail-settings";
import { ActivityPanel } from "./dashboard/activity";
import { AnalyticsDashboard } from "./dashboard/analytics";
import { FollowupsDashboard } from "./dashboard/followups";
import { EmailLogsTable } from "./dashboard/email-logs";
import { ApprovalQueueDashboard } from "./dashboard/approval_queue";
import { MemoryViewer } from "./dashboard/memory-viewer";

export function Dashboard() {
  const { tab } = useContext(TabContext);
  return (
    <div className="mx-auto max-w-7xl p-4 sm:p-6 space-y-6 text-slate-800">
      <h1 className="font-semibold text-lg">Email Outreach Command Centre</h1>
      {tab === "overview" && <><AnalyticsDashboard /><ActivityPanel /><EmailLogsTable /></>}
      {tab === "leads" && <LeadsDashboard />}
      {tab === "reports" && <ReportsDashboard />}
      {tab === "logs" && <><FollowupsDashboard /><EmailLogsTable /></>}
      {tab === "approvals" && <ApprovalQueueDashboard />}
      {tab === "memory" && <MemoryViewer />}
      {tab === "settings" && <GmailSettings />}
    </div>
  );
}
