"use client";

import React from "react";
import Link from "next/link";
import { ArrowLeft, MapPin, Building2, LayoutDashboard } from "lucide-react";

const STANDERTON_LEADS = [
  { name: "Standerton Auto Repair & Panelbeating", address: "42 Main Street, Standerton, Mpumalanga", phone: "+27177121101", email: "info@standertonauto.co.za" },
  { name: "Lekwa Bakery & Supply Store", address: "15 Kerk Street, Standerton, Mpumalanga", phone: "+27177121920", email: "orders@lekwabakery.co.za" },
  { name: "Standerton Plumbing & Hardware", address: "88 Burger Street, Standerton, Mpumalanga", phone: "+27177122220", email: "contact@standertonplumbing.co.za" },
  { name: "Highveld Agricultural Equipment & Spares", address: "5 Vaal River Road, Standerton, Mpumalanga", phone: "+27177123450", email: "sales@highveldagri.co.za" },
  { name: "Standerton Tyre & Fitment Center", address: "201 Meyerville Drive, Standerton, Mpumalanga", phone: "+27177124560", email: "fitment@standertontyres.co.za" },
  { name: "Lekwa Electrical & Solar Services", address: "74 Calie Street, Standerton, Mpumalanga", phone: "+27177125120", email: "service@lekwaelectrical.co.za" },
  { name: "Standerton Laundry & Dry Cleaners", address: "33 Charl Cilliers Street, Standerton, Mpumalanga", phone: "+27177126770", email: "clean@standertonlaundry.co.za" },
  { name: "Vaal River Landscaping & Fencing", address: "66 Industrial Road, Standerton, Mpumalanga", phone: "+27177127880", email: "projects@vaallandscaping.co.za" },
];

export default function ResearchAgentPage() {
  return (
    <div style={{ minHeight: "100vh", background: "#f8fafc", color: "#0f172a", fontFamily: "Inter, sans-serif" }}>
      {/* Top Header */}
      <header style={{ height: 54, borderBottom: "1px solid rgba(226,232,240,0.8)", background: "#ffffff", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 24px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Link href="/" style={{ display: "flex", alignItems: "center", gap: 6, color: "#64748b", textDecoration: "none", fontSize: 13, fontWeight: 600 }}>
            <ArrowLeft size={16} />
            Back to Central Hub
          </Link>
          <span style={{ color: "#cbd5e1" }}>|</span>
          <span style={{ fontWeight: 700, fontSize: 16, color: "#0f172a" }}>research_agent</span>
          <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 999, background: "rgba(236,72,153,0.1)", color: "#ec4899", fontWeight: 600 }}>
            Google Lead Discovery
          </span>
        </div>

        <Link
          href="/dashboard"
          style={{
            display: "flex", alignItems: "center", gap: 6,
            padding: "7px 14px", fontSize: 12, fontWeight: 600, color: "#0f172a",
            background: "#ffffff", border: "1px solid rgba(0,0,0,0.1)",
            borderRadius: 999, textDecoration: "none", boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
          }}
        >
          <LayoutDashboard size={14} />
          Admin Dashboard
        </Link>
      </header>

      {/* Main Content */}
      <main style={{ maxWidth: 960, margin: "32px auto", padding: "0 24px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, margin: "0 0 4px", color: "#0f172a" }}>
              Active Companies Missing Official Websites
            </h1>
            <p style={{ fontSize: 13, color: "#64748b", margin: 0 }}>
              Scraped business directory leads operating in Standerton, Mpumalanga
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 6, background: "#ffffff", padding: "6px 14px", borderRadius: 999, border: "1px solid rgba(226,232,240,0.9)", boxShadow: "0 2px 8px rgba(0,0,0,0.02)" }}>
            <MapPin size={14} color="#ec4899" />
            <span style={{ fontSize: 12, fontWeight: 600, color: "#0f172a" }}>Standerton, Mpumalanga</span>
          </div>
        </div>

        {/* Directory Leads Table */}
        <div style={{ background: "#ffffff", borderRadius: 12, border: "1px solid rgba(226,232,240,0.9)", overflow: "hidden", boxShadow: "0 2px 8px rgba(0,0,0,0.02)" }}>
          <div style={{ padding: "14px 18px", borderBottom: "1px solid #f1f5f9", background: "#fafafa", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: "#0f172a" }}>Scraped Lead Directory</span>
            <span style={{ fontSize: 11, color: "#ec4899", fontWeight: 700 }}>8 Leads Found</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column" }}>
            {STANDERTON_LEADS.map((lead, idx) => (
              <div
                key={idx}
                style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  padding: "14px 18px", borderBottom: idx < STANDERTON_LEADS.length - 1 ? "1px solid #f8fafc" : "none",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div style={{ width: 32, height: 32, borderRadius: "50%", background: "#f1f5f9", display: "flex", alignItems: "center", justifyContent: "center", color: "#64748b" }}>
                    <Building2 size={16} />
                  </div>
                  <div>
                    <h4 style={{ fontSize: 13, fontWeight: 600, margin: 0, color: "#0f172a" }}>{lead.name}</h4>
                    <p style={{ fontSize: 11, color: "#64748b", margin: "2px 0 0" }}>{lead.address}</p>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                  <div style={{ textAlign: "right" }}>
                    <p style={{ fontSize: 11, color: "#ec4899", fontWeight: 600, margin: 0 }}>{lead.phone}</p>
                    <p style={{ fontSize: 11, color: "#64748b", margin: "2px 0 0" }}>{lead.email}</p>
                  </div>

                  <span style={{ fontSize: 10, padding: "3px 8px", borderRadius: 999, background: "rgba(239,68,68,0.1)", color: "#dc2626", fontWeight: 700 }}>
                    No Website
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
