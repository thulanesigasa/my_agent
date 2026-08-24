"use client";

import React, { useState, useEffect } from "react";
import {
  Mail, CheckCircle2, Eye, Clock, AlertCircle,
  ChevronDown, ChevronRight, Filter, SortDesc
} from "lucide-react";
import { getEmailLogs, EmailLog } from "@/lib/api";

const STATUS_CONFIG: Record<
  EmailLog["status"],
  { label: string; icon: React.ElementType; cls: string }
> = {
  Responded: {
    label: "Responded",
    icon: CheckCircle2,
    cls: "text-emerald-700 bg-emerald-50 border-emerald-200",
  },
  Opened: {
    label: "Opened",
    icon: Eye,
    cls: "text-blue-700 bg-blue-50 border-blue-200",
  },
  Sent: {
    label: "Sent",
    icon: Clock,
    cls: "text-slate-600 bg-slate-100 border-slate-200",
  },
  Bounced: {
    label: "Bounced",
    icon: AlertCircle,
    cls: "text-rose-700 bg-rose-50 border-rose-200",
  },
};

export const EmailLogsTable: React.FC = () => {
  const [logs, setLogs] = useState<EmailLog[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchLogs = async (f: string) => {
    setLoading(true);
    const data = await getEmailLogs(f);
    setLogs(data);
    setLoading(false);
  };

  useEffect(() => {
    fetchLogs(filter);
  }, [filter]);

  const filters = [
    { value: "all", label: "All" },
    { value: "responded", label: "Responded" },
    { value: "opened", label: "Opened" },
    { value: "sent", label: "Sent" },
  ];

  return (
    <div className="w-full bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-200">
            <Mail className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-800">Email Outreach Logs</h3>
            <p className="text-xs text-slate-400">
              {logs.length} record{logs.length !== 1 ? "s" : ""} • click a row to read thread
            </p>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center gap-1 bg-slate-100 rounded-xl p-1">
          {filters.map((f) => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                filter === f.value
                  ? "bg-white text-indigo-700 shadow-sm border border-slate-200"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50/60">
              <th className="text-left px-5 py-3 font-semibold text-slate-500 w-6"></th>
              <th className="text-left px-3 py-3 font-semibold text-slate-500">Recipient</th>
              <th className="text-left px-3 py-3 font-semibold text-slate-500">Company</th>
              <th className="text-left px-3 py-3 font-semibold text-slate-500 max-w-xs">Subject</th>
              <th className="text-left px-3 py-3 font-semibold text-slate-500">Date Sent</th>
              <th className="text-left px-3 py-3 font-semibold text-slate-500">Status</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="px-5 py-12 text-center text-slate-400">
                  Loading outreach logs...
                </td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-5 py-12 text-center text-slate-400">
                  No email logs match the selected filter.
                </td>
              </tr>
            ) : (
              logs.map((log) => {
                const isOpen = expanded === log.id;
                const { icon: StatusIcon, cls, label } = STATUS_CONFIG[log.status];
                return (
                  <React.Fragment key={log.id}>
                    <tr
                      onClick={() => setExpanded(isOpen ? null : log.id)}
                      className={`border-b border-slate-100 cursor-pointer transition-colors ${
                        isOpen ? "bg-indigo-50/40" : "hover:bg-slate-50"
                      }`}
                    >
                      <td className="px-5 py-3.5">
                        {isOpen ? (
                          <ChevronDown className="w-3.5 h-3.5 text-indigo-500" />
                        ) : (
                          <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                        )}
                      </td>
                      <td className="px-3 py-3.5 font-medium text-slate-800">
                        {log.recipient}
                      </td>
                      <td className="px-3 py-3.5 text-slate-600 font-semibold">
                        {log.company}
                      </td>
                      <td className="px-3 py-3.5 text-slate-600 max-w-xs truncate">
                        {log.subject}
                      </td>
                      <td className="px-3 py-3.5 text-slate-500 tabular-nums">
                        {log.dateSent}
                      </td>
                      <td className="px-3 py-3.5">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border font-semibold text-[11px] ${cls}`}
                        >
                          <StatusIcon className="w-3 h-3" />
                          {label}
                        </span>
                      </td>
                    </tr>

                    {/* Expanded Thread Row */}
                    {isOpen && (
                      <tr className="border-b border-indigo-100 bg-indigo-50/20">
                        <td colSpan={6} className="px-8 py-5">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-1.5">
                              <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wide">
                                Email Thread (Sent)
                              </p>
                              <div className="p-3.5 rounded-xl bg-white border border-slate-200 text-xs text-slate-700 leading-relaxed">
                                {log.thread || "No thread content available."}
                              </div>
                            </div>
                            <div className="space-y-1.5">
                              <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wide">
                                Client Reply
                              </p>
                              {log.reply ? (
                                <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 leading-relaxed">
                                  {log.reply}
                                </div>
                              ) : (
                                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-400 italic">
                                  No reply received yet.
                                </div>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
