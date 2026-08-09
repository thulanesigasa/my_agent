"use client";

import React, { useEffect, useState } from "react";
import { Mail, Reply, TrendingUp, Users, BarChart3, Zap } from "lucide-react";
import { getOutreachMetrics, OutreachMetrics } from "@/lib/api";

export const AnalyticsDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<OutreachMetrics>({
    totalEmailsSent: 0,
    totalResponsesReceived: 0,
    responseRatePercent: 0,
    activeLeadsInPipeline: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getOutreachMetrics().then((data) => {
      setMetrics(data);
      setLoading(false);
    });
  }, []);

  const cards = [
    {
      title: "Total Emails Sent",
      value: loading ? "—" : metrics.totalEmailsSent.toLocaleString(),
      sub: "All outreach via Gmail API",
      icon: Mail,
      accent: "bg-blue-50 border-blue-200 text-blue-600",
      bar: "bg-blue-500",
      pct: 100,
    },
    {
      title: "Total Responses Received",
      value: loading ? "—" : metrics.totalResponsesReceived.toLocaleString(),
      sub: "Replies tracked in-thread",
      icon: Reply,
      accent: "bg-emerald-50 border-emerald-200 text-emerald-600",
      bar: "bg-emerald-500",
      pct: Math.min(
        100,
        metrics.totalEmailsSent
          ? (metrics.totalResponsesReceived / metrics.totalEmailsSent) * 100
          : 0
      ),
    },
    {
      title: "Response Rate",
      value: loading ? "—" : `${metrics.responseRatePercent.toFixed(1)}%`,
      sub: "vs. industry avg 21%",
      icon: TrendingUp,
      accent: "bg-purple-50 border-purple-200 text-purple-600",
      bar: "bg-purple-500",
      pct: metrics.responseRatePercent,
    },
    {
      title: "Active Leads in Pipeline",
      value: loading ? "—" : metrics.activeLeadsInPipeline.toLocaleString(),
      sub: "Pending follow-up actions",
      icon: Users,
      accent: "bg-amber-50 border-amber-200 text-amber-600",
      bar: "bg-amber-500",
      pct: 60,
    },
  ];

  return (
    <section className="space-y-5">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-200">
          <BarChart3 className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-slate-800 leading-tight">
            Email Outreach Analytics
          </h3>
          <p className="text-xs text-slate-400">
            Live stats from the LangGraph autonomous outreach engine
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {cards.map((c, i) => {
          const Icon = c.icon;
          return (
            <div
              key={i}
              className="p-5 rounded-2xl border border-slate-200 bg-white shadow-sm space-y-4 hover:shadow-md transition-shadow"
            >
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold text-slate-500">{c.title}</p>
                <div className={`p-2 rounded-xl border ${c.accent}`}>
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 tabular-nums">{c.value}</p>
                <p className="text-[11px] text-slate-400 mt-0.5">{c.sub}</p>
              </div>
              {/* Mini progress bar */}
              <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
                <div
                  className={`h-full rounded-full ${c.bar} transition-all duration-700`}
                  style={{ width: `${c.pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Inline Bar Chart — Response Rate vs Pipeline */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="p-5 rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-4 h-4 text-purple-500" />
            <p className="text-xs font-semibold text-slate-700">Status Breakdown</p>
          </div>
          {[
            { label: "Responded", count: 91, color: "bg-emerald-500", pct: 32 },
            { label: "Opened", count: 76, color: "bg-blue-500", pct: 27 },
            { label: "Sent (No Open)", count: 104, color: "bg-slate-300", pct: 37 },
            { label: "Bounced", count: 13, color: "bg-rose-400", pct: 4 },
          ].map((row) => (
            <div key={row.label} className="space-y-1 mb-3">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-600 font-medium">{row.label}</span>
                <span className="tabular-nums text-slate-400">{row.count}</span>
              </div>
              <div className="h-1.5 rounded-full bg-slate-100">
                <div
                  className={`h-full rounded-full ${row.color}`}
                  style={{ width: `${row.pct}%` }}
                />
              </div>
            </div>
          ))}
        </div>

        <div className="p-5 rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-4 h-4 text-emerald-500" />
            <p className="text-xs font-semibold text-slate-700">Weekly Send Volume</p>
          </div>
          <div className="flex items-end gap-2 h-20">
            {[30, 42, 38, 55, 48, 62, 71].map((h, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full rounded-t-md bg-indigo-400 hover:bg-indigo-500 transition-colors"
                  style={{ height: `${(h / 71) * 80}px` }}
                />
                <span className="text-[9px] text-slate-400">
                  {["M", "T", "W", "T", "F", "S", "S"][i]}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
