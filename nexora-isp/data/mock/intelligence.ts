import type {
  CopilotActivityItem,
  CopilotSuggestedPrompt,
  OperationalInsight,
} from "@/types/intelligence";

export const copilotSuggestedPrompts: CopilotSuggestedPrompt[] = [
  {
    id: "prompt-001",
    title: "Network Risk",
    prompt:
      "Which network nodes require immediate operational attention?",
    domain: "NETWORK",
    icon: "RADIO_TOWER",
  },
  {
    id: "prompt-002",
    title: "Revenue Exposure",
    prompt:
      "Show me the biggest current revenue collection risks.",
    domain: "BILLING",
    icon: "BADGE_DOLLAR",
  },
  {
    id: "prompt-003",
    title: "Customer Churn",
    prompt:
      "Which customers show the strongest churn risk signals?",
    domain: "CUSTOMER",
    icon: "USERS",
  },
  {
    id: "prompt-004",
    title: "Incident Correlation",
    prompt:
      "Are multiple support complaints linked to the same network issue?",
    domain: "SUPPORT",
    icon: "CIRCLE_ALERT",
  },
  {
    id: "prompt-005",
    title: "Capacity Planning",
    prompt:
      "Which nodes may require capacity upgrades soon?",
    domain: "NETWORK",
    icon: "NETWORK",
  },
  {
    id: "prompt-006",
    title: "Growth Opportunity",
    prompt:
      "Where are the strongest package upgrade opportunities?",
    domain: "CUSTOMER",
    icon: "TRENDING_UP",
  },
];

export const operationalInsights: OperationalInsight[] = [
  {
    id: "insight-001",
    title:
      "JT-NODE-07 shows a concentrated service disruption pattern",
    description:
      "18 support complaints share the same distribution node while 126 subscribers are potentially exposed. Current complaint concentration strongly indicates a common network incident rather than isolated customer faults.",
    severity: "CRITICAL",
    domain: "NETWORK",
    confidence: 96,
    detectedAt: "8 min ago",
    actionLabel: "Open Incident Context",
  },
  {
    id: "insight-002",
    title:
      "Outstanding billing exposure requires collection attention",
    description:
      "A concentrated group of unpaid accounts is approaching suspension workflow stages. Prioritizing reminder and payment verification operations may reduce avoidable service suspensions.",
    severity: "WARNING",
    domain: "BILLING",
    confidence: 91,
    detectedAt: "21 min ago",
    actionLabel: "Review Billing Risk",
  },
  {
    id: "insight-003",
    title:
      "Fiber 20 Mbps subscribers show package upgrade potential",
    description:
      "A subscriber segment demonstrates sustained service usage patterns that may align with higher bandwidth packages. Package suitability should be reviewed before targeted upgrade communication.",
    severity: "OPPORTUNITY",
    domain: "CUSTOMER",
    confidence: 84,
    detectedAt: "46 min ago",
    actionLabel: "Review Opportunity",
  },
  {
    id: "insight-004",
    title:
      "Field dispatch duplication may be avoidable",
    description:
      "Several queued field jobs are associated with tickets linked to the same active network incident. Incident-level resolution may remove the need for separate customer dispatches.",
    severity: "INFO",
    domain: "FIELD_OPERATIONS",
    confidence: 89,
    detectedAt: "1 hour ago",
    actionLabel: "Review Dispatch Queue",
  },
];

export const copilotActivity: CopilotActivityItem[] = [
  {
    id: "activity-001",
    query: "Why are Internet Down complaints increasing?",
    summary:
      "Copilot identified a complaint concentration around JT-NODE-07 and referenced the active correlated incident.",
    createdAt: "12 min ago",
    requestedBy: "Nabeel · Owner",
  },
  {
    id: "activity-002",
    query: "Which customers are close to suspension?",
    summary:
      "Billing lifecycle exposure was summarized across grace period and suspension pending service states.",
    createdAt: "38 min ago",
    requestedBy: "Nabeel · Owner",
  },
  {
    id: "activity-003",
    query: "Where can we improve monthly revenue?",
    summary:
      "Copilot highlighted outstanding collection exposure and potential package upgrade segments.",
    createdAt: "2 hours ago",
    requestedBy: "Nabeel · Owner",
  },
];