"use client";
import React, { useEffect, useState } from "react";
import { getOutreachMetrics, OutreachMetrics } from "@/lib/api";

export const AnalyticsDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<OutreachMetrics | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    getOutreachMetrics().then(setMetrics).catch((e) => setError(e.message));
  }, []);
  if (error) return <p role="alert" className="text-sm text-red-700">Metrics unavailable: {error}</p>;
  if (!metrics) return <p className="text-sm">Loading recorded activity…</p>;
  const cards = [
    ["Confirmed outreach sends", metrics.totalEmailsSent],
    ["Responses", metrics.replyTrackingAvailable ? metrics.totalResponsesReceived : "Not tracked yet"],
    ["Response rate", metrics.replyTrackingAvailable ? `${metrics.responseRatePercent}%` : "Not tracked yet"],
    ["Recorded leads", metrics.activeLeadsInPipeline],
  ];
  return <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
    {cards.map(([label, value]) => <div key={label} className="border border-slate-200 p-5 rounded-xl bg-white">
      <p className="text-xs text-slate-500">{label}</p><p className="text-xl font-semibold mt-2">{value}</p>
    </div>)}
  </section>;
};
