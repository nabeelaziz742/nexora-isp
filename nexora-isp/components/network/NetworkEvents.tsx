import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  LoaderCircle,
  XCircle,
} from "lucide-react";

import type {
  ProvisioningRequest,
  ProvisioningStatus,
} from "@/types/network";

interface NetworkEventsProps {
  events: ProvisioningRequest[];
}

const statusStyles: Record<
  ProvisioningStatus,
  {
    icon: typeof Clock3;
    color: string;
    border: string;
    badge: string;
  }
> = {
  PENDING: {
    icon: Clock3,
    color: "text-[#F59E0B]",
    border: "border-l-[#F59E0B]",
    badge:
      "border-[#F59E0B]/20 bg-[#F59E0B]/10 text-[#F59E0B]",
  },
  PROCESSING: {
    icon: LoaderCircle,
    color: "text-[#3B82F6]",
    border: "border-l-[#3B82F6]",
    badge:
      "border-[#3B82F6]/20 bg-[#3B82F6]/10 text-[#60A5FA]",
  },
  SUCCEEDED: {
    icon: CheckCircle2,
    color: "text-[#22C55E]",
    border: "border-l-[#22C55E]",
    badge:
      "border-[#22C55E]/20 bg-[#22C55E]/10 text-[#22C55E]",
  },
  FAILED: {
    icon: AlertCircle,
    color: "text-[#EF4444]",
    border: "border-l-[#EF4444]",
    badge:
      "border-[#EF4444]/20 bg-[#EF4444]/10 text-[#EF4444]",
  },
  CANCELLED: {
    icon: XCircle,
    color: "text-[#64748B]",
    border: "border-l-[#64748B]",
    badge:
      "border-[#64748B]/20 bg-[#64748B]/10 text-[#94A3B8]",
  },
};

function formatDate(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-PK", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export default function NetworkEvents({
  events,
}: NetworkEventsProps) {
  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="border-b border-[#202938] px-5 py-4">
        <h2 className="text-sm font-semibold text-[#F8FAFC]">
          Provisioning Requests
        </h2>

        <p className="mt-1 text-xs text-[#64748B]">
          Recent network service lifecycle requests
        </p>
      </div>

      {events.length === 0 ? (
        <div className="flex min-h-56 items-center justify-center p-6">
          <p className="text-xs text-[#64748B]">
            No provisioning requests are available.
          </p>
        </div>
      ) : (
        <div>
          {events.map((event) => {
            const styles = statusStyles[event.status];
            const Icon = styles.icon;

            return (
              <div
                key={event.id}
                className={`border-b border-l-2 border-b-[#202938] p-4 last:border-b-0 ${styles.border}`}
              >
                <div className="flex items-start gap-3">
                  <Icon
                    className={`mt-0.5 h-4 w-4 shrink-0 ${styles.color}`}
                  />

                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-[#F8FAFC]">
                          {event.action.replaceAll("_", " ")}
                        </p>

                        <p className="mt-1 truncate font-mono text-[10px] text-[#64748B]">
                          {event.service_number} ·{" "}
                          {event.network_node_code}
                        </p>
                      </div>

                      <span
                        className={`shrink-0 border px-2 py-1 text-[10px] font-medium ${styles.badge}`}
                      >
                        {event.status}
                      </span>
                    </div>

                    <p className="mt-3 text-xs leading-5 text-[#94A3B8]">
                      {event.customer_name} ·{" "}
                      {event.customer_number}
                    </p>

                    {event.error_message && (
                      <p className="mt-2 text-[11px] leading-5 text-[#EF4444]">
                        {event.error_message}
                      </p>
                    )}

                    <div className="mt-3 flex items-center justify-between gap-3 text-[11px] text-[#64748B]">
                      <span className="truncate">
                        {event.network_node_name}
                      </span>

                      <span className="shrink-0">
                        {formatDate(event.requested_at)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}