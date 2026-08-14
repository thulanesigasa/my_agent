"use client";

import React, { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Globe, Search, MapPin, Building2, Phone, Mail } from "lucide-react";

const STANDERTON_LEADS = [
  { name: "Standerton Auto Repair & Panelbeating", address: "42 Main Street, Standerton, Mpumalanga", phone: "+27177121101", website: "Missing Website", email: "info@standertonauto.co.za" },
  { name: "Lekwa Bakery & Supply Store", address: "15 Kerk Street, Standerton, Mpumalanga", phone: "+27177121920", website: "Missing Website", email: "orders@lekwabakery.co.za" },
  { name: "Standerton Plumbing & Hardware", address: "88 Burger Street, Standerton, Mpumalanga", phone: "+27177122220", website: "Missing Website", email: "contact@standertonplumbing.co.za" },
  { name: "Highveld Agricultural Equipment & Spares", address: "5 Vaal River Road, Standerton, Mpumalanga", phone: "+27177123450", website: "Missing Website", email: "sales@highveldagri.co.za" },
  { name: "Standerton Tyre & Fitment Center", address: "201 Meyerville Drive, Standerton, Mpumalanga", phone: "+27177124560", website: "Missing Website", email: "fitment@standertontyres.co.za" },
  { name: "Lekwa Electrical & Solar Services", address: "74 Calie Street, Standerton, Mpumalanga", phone: "+27177125120", website: "Missing Website", email: "service@lekwaelectrical.co.za" },
  { name: "Standerton Laundry & Dry Cleaners", address: "33 Charl Cilliers Street, Standerton, Mpumalanga", phone: "+27177126770", website: "Missing Website", email: "clean@standertonlaundry.co.za" },
  { name: "Vaal River Landscaping & Fencing", address: "66 Industrial Road, Standerton, Mpumalanga", phone: "+27177127880", website: "Missing Website", email: "projects@vaallandscaping.co.za" },
];

export default function ResearchAgentPage() {
  const [searchLocation, setSearchLocation] = useState("Standerton, Mpumalanga");

  return (
    <div style={{
      minHeight: "100vh",
      background: "linear-gradient(to bottom, rgba(255,255,255,0.9), rgba(248,250,252,0.95)), url('/gemini-bg.png')",
      backgroundSize: "cover",
      color: "#0f172a",
      fontFamily: "'Inter', sans-serif",
      padding: "24px",
    }}>
      {/* Top Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Link href="/" style={{ display: "flex", alignItems: "center", gap: 6, color: "#64748b", textDecoration: "none", fontSize: 13, fontWeight: 600 }}>
            <ArrowLeft size={16} />
            Back to Hub
          </Link>
          <span style={{ color: "#cbd5e1" }}>|</span>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 32, height: 32, borderRadius: 8, background: "#0f172a", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Globe size={18} />
            </div>
            <div>
              <h1 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: "#0f172a" }}>research_agent Dashboard</h1>
              <span style={{ fontSize: 11, color: "#64748b" }}>Google Lead Finder — Small Active Companies Missing Websites</span>
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8, background: "#ffffff", padding: "6px 12px", borderRadius: 10, border: "1px solid rgba(226,232,240,0.9)" }}>
          <MapPin size={14} color="#ec4899" />
          <span style={{ fontSize: 12, fontWeight: 600, color: "#0f172a" }}>Standerton, Mpumalanga</span>
        </div>
      </div>

      {/* Discovered Leads Table */}
      <div style={{ background: "#ffffff", borderRadius: 16, border: "1px solid rgba(226,232,240,0.8)", padding: "20px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>Discovered Businesses Missing Official Websites</h3>
          <span style={{ fontSize: 12, color: "#ec4899", fontWeight: 700 }}>{STANDERTON_LEADS.length} Leads Found</span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {STANDERTON_LEADS.map((lead, idx) => (
            <div key={idx} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px", background: "#f8fafc", borderRadius: 10 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <Building2 size={16} color="#64748b" />
                <div>
                  <h4 style={{ fontSize: 13, fontWeight: 600, margin: 0 }}>{lead.name}</h4>
                  <span style={{ fontSize: 11, color: "#64748b" }}>{lead.address}</span>
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                <span style={{ fontSize: 11, color: "#475569", display: "flex", alignItems: "center", gap: 4 }}>
                  <Phone size={12} /> {lead.phone}
                </span>
                <span style={{ fontSize: 11, color: "#ec4899", fontWeight: 600, display: "flex", alignItems: "center", gap: 4 }}>
                  <Mail size={12} /> {lead.email}
                </span>
                <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 999, background: "rgba(239,68,68,0.1)", color: "#dc2626", fontWeight: 700 }}>
                  No Website
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
