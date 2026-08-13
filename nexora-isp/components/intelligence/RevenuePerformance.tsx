"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { MonthlyRevenuePerformance } from "@/types/revenue-intelligence";

interface RevenuePerformanceProps {
  data: MonthlyRevenuePerformance[];
}

function formatRevenue(value: number) {
  return `PKR ${(value / 1000000).toFixed(1)}M`;
}

export default function RevenuePerformance({
  data,
}: RevenuePerformanceProps) {
  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="flex flex-col gap-3 border-b border-[#202938] px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-sm font-semibold text-slate-100">
            Billing vs Collection Performance
          </h2>

          <p className="mt-1 text-xs text-slate-500">
            Monthly billed revenue compared with verified collections
          </p>
        </div>

        <div className="flex items-center gap-4 text-[11px]">
          <div className="flex items-center gap-2 text-slate-500">
            <span className="h-2 w-2 bg-blue-500" />
            Billed
          </div>

          <div className="flex items-center gap-2 text-slate-500">
            <span className="h-2 w-2 bg-emerald-500" />
            Collected
          </div>
        </div>
      </div>

      <div className="h-[340px] p-5">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{
              top: 10,
              right: 10,
              left: 10,
              bottom: 0,
            }}
          >
            <CartesianGrid
              stroke="#202938"
              vertical={false}
            />

            <XAxis
              dataKey="month"
              axisLine={false}
              tickLine={false}
              tick={{
                fill: "#64748B",
                fontSize: 11,
              }}
            />

            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{
                fill: "#64748B",
                fontSize: 11,
              }}
              tickFormatter={(value) =>
                `${(value / 1000000).toFixed(0)}M`
              }
            />

            <Tooltip
              cursor={{
                fill: "#121821",
              }}
              contentStyle={{
                backgroundColor: "#0D1117",
                border: "1px solid #202938",
                borderRadius: 0,
                fontSize: 12,
              }}
              labelStyle={{
                color: "#F8FAFC",
              }}
              formatter={(value) => [
                formatRevenue(Number(value)),
              ]}
            />

            <Bar
              dataKey="billed"
              name="Billed Revenue"
              fill="#3B82F6"
              radius={[2, 2, 0, 0]}
            />

            <Bar
              dataKey="collected"
              name="Collected Revenue"
              fill="#22C55E"
              radius={[2, 2, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}