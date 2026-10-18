"use client";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type Task = { id: string; thread_id: string; status: string; error?: string; created_at: string };
export function ActivityPanel() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    apiRequest("/api/activity").then((data) => setTasks(data.tasks.slice(-10).reverse()))
      .catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, []);
  return <section className="border border-slate-200 rounded-xl p-5 bg-white">
    <h2 className="font-semibold text-sm mb-3">Recent workflow tasks</h2>
    {error ? <p role="alert" className="text-sm text-red-700">Activity unavailable: {error}</p> :
      loading ? <p className="text-sm">Loading activity…</p> : tasks.length === 0 ? <p className="text-sm text-slate-500">No workflow tasks recorded.</p> :
      <ul className="space-y-3 text-sm">{tasks.map((task) => <li key={task.id}>
        <span className="font-medium">{task.status}</span> · {task.thread_id}
        <p className="text-xs text-slate-500">{task.created_at} {task.error}</p>
      </li>)}</ul>}
    <p className="text-xs text-slate-500 mt-4">Statuses show the last recorded state. Tasks left running after a shutdown require review.</p>
  </section>;
}
