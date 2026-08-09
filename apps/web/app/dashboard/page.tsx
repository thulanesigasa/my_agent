"use client";

import { AppShell } from "@/components/app-shell";
import { Dashboard } from "@/components/dashboard";

export function EfferdDashboard2() {
  return (
    <AppShell>
      {(activeTab) => <Dashboard activeTab={activeTab} />}
    </AppShell>
  );
}

export default EfferdDashboard2;
