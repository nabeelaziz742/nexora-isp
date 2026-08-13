import {
  BellRing,
  CheckCircle2,
  Clock3,
  MessageSquareText,
  Send,
  TriangleAlert,
} from "lucide-react";

import type {
  AutomationDeliverySummary,
} from "@/types/notifications";

interface AutomationDeliveryOverviewProps {
  summaries: AutomationDeliverySummary[];
}

const icons = [
  BellRing,
  Clock3,
  Send,
  CheckCircle2,
  TriangleAlert,
  MessageSquareText,
];

export default function AutomationDeliveryOverview({
  summaries,
}: AutomationDeliveryOverviewProps) {
  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="border-b border-[#202938] px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-100">
          Event Delivery Overview
        </h2>

        <p className="mt-1 text-[11px] text-slate-500">
          Real notification delivery grouped by operational event
        </p>
      </div>

      {summaries.length === 0 ? (
        <div className="px-4 py-12 text-center text-xs text-slate-500">
          No notification events available.
        </div>
      ) : (
        <div className="grid gap-px bg-[#202938] md:grid-cols-2 xl:grid-cols-3">
          {summaries.map((summary, index) => {
            const Icon = icons[index % icons.length];

            return (
              <article
                key={summary.id}
                className="bg-[#0D1117] p-4"
              >
                <div className="flex items-start gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center bg-blue-500/10">
                    <Icon className="h-3.5 w-3.5 text-blue-400" />
                  </div>

                  <div className="min-w-0 flex-1">
                    <p className="text-[9px] font-semibold uppercase tracking-[0.08em] text-slate-600">
                      Operational Event
                    </p>

                    <h3 className="mt-1 text-xs font-semibold text-slate-200">
                      {summary.title}
                    </h3>
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-3 gap-2">
                  <DeliveryValue
                    label="Targeted"
                    value={summary.targeted}
                  />

                  <DeliveryValue
                    label="Sent"
                    value={summary.delivered}
                    valueClassName="text-emerald-400"
                  />

                  <DeliveryValue
                    label="Failed"
                    value={summary.failed}
                    valueClassName={
                      summary.failed > 0
                        ? "text-red-400"
                        : "text-slate-400"
                    }
                  />
                </div>

                <div className="mt-2 grid grid-cols-2 gap-2">
                  <ChannelValue
                    label="WhatsApp"
                    value={summary.whatsappDelivered}
                  />

                  <ChannelValue
                    label="SMS"
                    value={summary.smsDelivered}
                  />
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

interface DeliveryValueProps {
  label: string;
  value: number;
  valueClassName?: string;
}

function DeliveryValue({
  label,
  value,
  valueClassName = "text-slate-300",
}: DeliveryValueProps) {
  return (
    <div className="bg-[#121821] px-2 py-2">
      <p className="text-[8px] uppercase tracking-[0.06em] text-slate-600">
        {label}
      </p>

      <p className={`mt-1 text-xs font-semibold ${valueClassName}`}>
        {value.toLocaleString("en-PK")}
      </p>
    </div>
  );
}

interface ChannelValueProps {
  label: string;
  value: number;
}

function ChannelValue({
  label,
  value,
}: ChannelValueProps) {
  return (
    <div className="flex items-center justify-between bg-[#121821] px-2 py-2">
      <span className="text-[9px] text-slate-600">
        {label}
      </span>

      <span className="text-[10px] font-semibold text-slate-300">
        {value.toLocaleString("en-PK")}
      </span>
    </div>
  );
}