import type {
  ActiveIncident,
  CommandMetric,
  DailyBriefingItem,
} from "@/types/command-center";

export const commandMetrics: CommandMetric[] = [
  {
    id: "customers",
    label: "Total Customers",
    value: "4,862",
    change: "+2.4%",
    helper: "116 added this month",
    tone: "primary",
  },
  {
    id: "services",
    label: "Active Services",
    value: "4,731",
    change: "97.3%",
    helper: "of total customers",
    tone: "success",
  },
  {
    id: "uptime",
    label: "Network Uptime",
    value: "99.94%",
    change: "+0.02%",
    helper: "last 30 days",
    tone: "success",
  },
  {
    id: "revenue",
    label: "Today Revenue",
    value: "Rs. 684K",
    change: "+8.2%",
    helper: "vs yesterday",
    tone: "primary",
  },
  {
    id: "outstanding",
    label: "Outstanding Bills",
    value: "Rs. 1.28M",
    change: "312",
    helper: "unpaid accounts",
    tone: "warning",
  },
  {
    id: "incidents",
    label: "Active Incidents",
    value: "3",
    change: "147",
    helper: "customers impacted",
    tone: "danger",
  },
  {
    id: "tickets",
    label: "Open Tickets",
    value: "42",
    change: "11",
    helper: "awaiting assignment",
    tone: "warning",
  },
  {
    id: "churn",
    label: "Churn Risk",
    value: "23",
    change: "High",
    helper: "customers need attention",
    tone: "intelligence",
  },
];

export const dailyBriefing: DailyBriefingItem[] = [
  {
    id: "brief-1",
    title: "Bandwidth capacity risk detected",
    description:
      "DHA Node 04 reached 94% utilization during peak hours for the fourth consecutive day.",
    severity: "warning",
  },
  {
    id: "brief-2",
    title: "Common network incident identified",
    description:
      "147 customers and 18 complaints correlate with JOHAR-TOWN-NODE-07.",
    severity: "critical",
  },
  {
    id: "brief-3",
    title: "Package upgrade opportunity",
    description:
      "87 customers repeatedly exceed 90% peak usage on their current packages.",
    severity: "intelligence",
  },
  {
    id: "brief-4",
    title: "Revenue leakage requires review",
    description:
      "17 active network users appear to have no active billing plan. Estimated exposure: Rs. 42,500/month.",
    severity: "info",
  },
];

export const activeIncidents: ActiveIncident[] = [
  {
    id: "INC-1024",
    node: "JOHAR-TOWN-NODE-07",
    title: "Probable common network outage",
    impactedCustomers: 147,
    relatedComplaints: 18,
    status: "Identified",
    severity: "Major",
  },
  {
    id: "INC-1021",
    node: "DHA-NODE-04",
    title: "Severe bandwidth degradation",
    impactedCustomers: 63,
    relatedComplaints: 9,
    status: "Investigating",
    severity: "Major",
  },
];