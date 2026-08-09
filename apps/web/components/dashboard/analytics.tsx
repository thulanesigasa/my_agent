"use client";

import React, { useEffect, useState } from "react";
import { MessageSquare, Mail, AlertTriangle, Zap, Activity } from "lucide-react";
import { getAnalytics, AnalyticsMetrics } from "@/lib/api";

export const AnalyticsDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<AnalyticsMetrics>({
    messagesProcessed: 1420,
    emailsDrafted: 384,
    apiFallbacks: 12,
    avgLatencyMs: 420,
  });

  useEffect(() => {
    getAnalytics().then((data) => setMetrics(data));
  }, []);

  const cards = [
    {
      title: "Messages Processed",
      value: metrics.messagesProcessed.toLocaleString(),
      change: "+14.2% this week",
      icon: MessageSquare,
      color: "text-blue-600 bg-blue-50 border-blue-200",
    },
    {
      title: "Emails Drafted & Reviewed",
      value: metrics.emailsDrafted.toLocaleString(),
      change: "+8.5% this week",
      icon: Mail,
      color: "text-purple-600 bg-purple-50 border-purple-200",
    },
    {
      title: "API Fallbacks Triggered",
      value: metrics.apiFallbacks.toString(),
      change: "Low (Auto Recovered)",
      icon: AlertTriangle,
      color: "text-amber-600 bg-amber-50 border-amber-200",
    },
    {
      title: "Avg Response Latency",
      value: `${metrics.avgLatencyMs} ms`,
      change: "Optimal (< 500ms)",
      icon: Zap,
      color: "text-emerald-600 bg-emerald-50 border-emerald-200",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-xl bg-blue-50 text-blue-600 border border-blue-200">
          <Activity className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-base font-semibold text-slate-800">
            System Performance Analytics
          </h3>
          <p className="text-xs text-slate-500">
            Live telemetry and throughput statistics for the LangGraph agent state machine
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((c, i) => {
          const Icon = c.icon;
          return (
            <div
              key={i}
              className="p-5 rounded-2xl border border-slate-200 bg-white shadow-sm space-y-3"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-500">{c.title}</span>
                <div className={`p-2 rounded-xl border ${c.color}`}>
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800">{c.value}</p>
                <p className="text-[11px] text-slate-400 mt-1">{c.change}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
