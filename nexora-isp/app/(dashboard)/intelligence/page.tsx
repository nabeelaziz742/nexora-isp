"use client";

import { useCallback, useEffect, useState } from "react";

import CopilotActivity from "@/components/intelligence/CopilotActivity";
import CopilotPrompt from "@/components/intelligence/CopilotPrompt";
import OperationalInsights from "@/components/intelligence/OperationalInsights";
import {
  commandCenterService,
  type OperationalAlert,
  type OperationsCopilotResponse,
} from "@/services/command-center-service";

import type {
  CopilotActivityItem,
  CopilotSuggestedPrompt,
  IntelligenceDomain,
  IntelligenceSeverity,
  OperationalInsight,
} from "@/types/intelligence";

// Questions the Copilot can answer from the tenant snapshot it receives.
const SUGGESTED_PROMPTS: CopilotSuggestedPrompt[] = [
  {
    id: "attention",
    title: "Today's Priorities",
    prompt: "What requires my attention right now?",
    domain: "NETWORK",
    icon: "CIRCLE_ALERT",
  },
  {
    id: "collections",
    title: "Revenue Exposure",
    prompt: "What are the biggest collection and outstanding balance risks?",
    domain: "BILLING",
    icon: "BADGE_DOLLAR",
  },
  {
    id: "provisioning",
    title: "Provisioning Health",
    prompt: "Are there failed or stuck provisioning requests?",
    domain: "NETWORK",
    icon: "RADIO_TOWER",
  },
  {
    id: "support",
    title: "Support Pressure",
    prompt: "Which critical complaints and incidents are still open?",
    domain: "SUPPORT",
    icon: "USERS",
  },
  {
    id: "field",
    title: "Field Operations",
    prompt: "Which work orders are critical or overdue?",
    domain: "FIELD_OPERATIONS",
    icon: "NETWORK",
  },
  {
    id: "risks",
    title: "Operational Risks",
    prompt: "Summarize the highest operational risks across the ISP.",
    domain: "CUSTOMER",
    icon: "TRENDING_UP",
  },
];

const ALERT_ROUTING: Record<
  string,
  { domain: IntelligenceDomain; actionLabel: string; actionHref: string }
> = {
  PROVISIONING_FAILED: { domain: "NETWORK", actionLabel: "Open Network", actionHref: "/network" },
  CRITICAL_INCIDENT: { domain: "SUPPORT", actionLabel: "Open Incidents", actionHref: "/support" },
  CRITICAL_COMPLAINT: { domain: "SUPPORT", actionLabel: "Open Complaints", actionHref: "/support" },
  CRITICAL_WORK_ORDER: { domain: "FIELD_OPERATIONS", actionLabel: "Open Work Orders", actionHref: "/field-operations" },
  NOTIFICATION_FAILED: { domain: "CUSTOMER", actionLabel: "Open Communications", actionHref: "/communications" },
};

function toSeverity(severity: string): IntelligenceSeverity {
  const normalized = severity.toUpperCase();
  if (normalized === "CRITICAL") return "CRITICAL";
  if (normalized === "HIGH" || normalized === "MEDIUM" || normalized === "WARNING") return "WARNING";
  return "INFO";
}

function formatTimestamp(value: string): string {
  try {
    return new Intl.DateTimeFormat("en-PK", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function toInsight(alert: OperationalAlert, index: number): OperationalInsight {
  const routing = ALERT_ROUTING[alert.alert_type] ?? {
    domain: "NETWORK" as IntelligenceDomain,
    actionLabel: "Open Command Center",
    actionHref: "/command-center",
  };

  return {
    id: `${alert.alert_type}-${alert.resource_id}-${index}`,
    title: alert.title,
    description: alert.description,
    severity: toSeverity(alert.severity),
    domain: routing.domain,
    detectedAt: formatTimestamp(alert.occurred_at),
    actionLabel: routing.actionLabel,
    actionHref: routing.actionHref,
  };
}

export default function IntelligencePage() {
  const [insights, setInsights] = useState<OperationalInsight[]>([]);
  const [activities, setActivities] = useState<CopilotActivityItem[]>([]);
  const [loadingAlerts, setLoadingAlerts] = useState(true);
  const [alertsError, setAlertsError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadAlerts() {
      try {
        const alerts = await commandCenterService.getAlerts();
        if (active) {
          setInsights(alerts.map(toInsight));
        }
      } catch (requestError) {
        if (active) {
          setAlertsError(
            requestError instanceof Error
              ? requestError.message
              : "Unable to load operational alerts.",
          );
        }
      } finally {
        if (active) {
          setLoadingAlerts(false);
        }
      }
    }

    void loadAlerts();

    return () => {
      active = false;
    };
  }, []);

  const handleAnswered = useCallback(
    (question: string, response: OperationsCopilotResponse) => {
      setActivities((current) => [
        {
          id: `${response.generated_at}-${current.length}`,
          query: question,
          summary: response.answer,
          createdAt: formatTimestamp(response.generated_at),
          requestedBy: "You",
        },
        ...current,
      ]);
    },
    [],
  );

  return (
    <div className="space-y-6">
      <section>
        <p className="text-xs font-medium uppercase tracking-[0.12em] text-violet-400">
          ISP Intelligence
        </p>

        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-50">
          AI ISP Copilot
        </h1>

        <p className="mt-2 max-w-3xl text-sm text-slate-500">
          Cross-module operational intelligence for network risk,
          billing exposure, customer behavior, support patterns and
          field operations.
        </p>
      </section>

      <CopilotPrompt prompts={SUGGESTED_PROMPTS} onAnswered={handleAnswered} />

      <div className="grid gap-6 2xl:grid-cols-[minmax(0,1.7fr)_minmax(340px,0.7fr)]">
        {loadingAlerts ? (
          <div className="flex min-h-48 items-center justify-center border border-[#202938] bg-[#0D1117]">
            <p className="text-xs text-slate-500">Loading operational alerts...</p>
          </div>
        ) : alertsError ? (
          <div className="border border-red-500/20 bg-red-500/5 px-5 py-4">
            <p className="text-xs font-medium text-red-400">Unable to load operational alerts</p>
            <p className="mt-1 text-[11px] text-slate-400">{alertsError}</p>
          </div>
        ) : (
          <OperationalInsights insights={insights} />
        )}

        <CopilotActivity activities={activities} />
      </div>
    </div>
  );
}
