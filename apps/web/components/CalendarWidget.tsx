"use client";

import React, { useState, useEffect } from "react";
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight } from "lucide-react";

export default function CalendarWidget() {
  const [currentDate, setCurrentDate] = useState<Date>(new Date());
  const [viewDate, setViewDate] = useState<Date>(new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentDate(new Date());
    }, 1000 * 60);
    return () => clearInterval(timer);
  }, []);

  const year = viewDate.getFullYear();
  const month = viewDate.getMonth();

  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];
  const dayLabels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  const firstDayOfMonth = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const isToday = (day: number) => {
    const today = new Date();
    return (
      day === today.getDate() &&
      month === today.getMonth() &&
      year === today.getFullYear()
    );
  };

  const handlePrevMonth = () => {
    setViewDate(new Date(year, month - 1, 1));
  };

  const handleNextMonth = () => {
    setViewDate(new Date(year, month + 1, 1));
  };

  return (
    <div style={{
      width: "100%",
      background: "transparent",
      border: "1px solid rgba(226, 232, 240, 0.5)",
      borderRadius: 16,
      padding: "12px 14px",
      display: "flex",
      flexDirection: "column",
      gap: 8,
    }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <div style={{
            width: 24, height: 24, borderRadius: 6,
            background: "rgba(236, 72, 153, 0.1)",
            display: "flex", alignItems: "center", justifyContent: "center",
            color: "#ec4899",
          }}>
            <CalendarIcon size={14} />
          </div>
          <span style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>
            {monthNames[month]} {year}
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 2 }}>
          <button
            onClick={handlePrevMonth}
            style={{
              background: "none", border: "none", cursor: "pointer",
              padding: 2, borderRadius: 4, color: "#64748b",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}
          >
            <ChevronLeft size={14} />
          </button>
          <button
            onClick={handleNextMonth}
            style={{
              background: "none", border: "none", cursor: "pointer",
              padding: 2, borderRadius: 4, color: "#64748b",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}
          >
            <ChevronRight size={14} />
          </button>
        </div>
      </div>

      {/* Days Header */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", textAlign: "center" }}>
        {dayLabels.map((day) => (
          <span key={day} style={{ fontSize: 10, fontWeight: 600, color: "#94a3b8" }}>
            {day}
          </span>
        ))}
      </div>

      {/* Days Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 2, textAlign: "center" }}>
        {Array.from({ length: firstDayOfMonth }).map((_, idx) => (
          <div key={`empty-${idx}`} />
        ))}
        {Array.from({ length: daysInMonth }).map((_, idx) => {
          const day = idx + 1;
          const active = isToday(day);
          return (
            <div
              key={day}
              style={{
                height: 22,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                borderRadius: "50%",
                fontSize: 11,
                fontWeight: active ? 700 : 500,
                background: active ? "#ec4899" : "transparent",
                color: active ? "#ffffff" : "#334155",
                boxShadow: active ? "0 0 10px rgba(236, 72, 153, 0.45)" : "none",
                transition: "all 150ms ease",
              }}
            >
              {day}
            </div>
          );
        })}
      </div>
    </div>
  );
}
