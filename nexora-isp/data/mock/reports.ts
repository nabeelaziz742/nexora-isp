import type {
  RecentReportRun,
  ReportDefinition,
  ReportMetric,
} from "@/types/reports";

export const reportMetrics: ReportMetric[] = [
  {
    id: "available-reports",
    label: "Available Reports",
    value: "18",
    description: "Operational report definitions",
    tone: "PRIMARY",
  },
  {
    id: "generated-month",
    label: "Generated This Month",
    value: "146",
    description: "Report execution volume",
    tone: "HEALTHY",
  },
  {
    id: "scheduled-reports",
    label: "Scheduled Reports",
    value: "7",
    description: "Recurring report workflows",
    tone: "INTELLIGENCE",
  },
  {
    id: "processing",
    label: "Currently Processing",
    value: "2",
    description: "Report generation jobs",
    tone: "WARNING",
  },
];

export const reportDefinitions: ReportDefinition[] = [
  {
    id: "report-001",
    name: "Customer Service Lifecycle Report",
    description:
      "Customer distribution across active, grace period, suspension pending, suspended and restore pending service states.",
    domain: "CUSTOMERS",
    availableFormats: ["PDF", "CSV", "XLSX"],
    lastGenerated: "Today · 09:42 PM",
    scheduleLabel: "Daily",
  },
  {
    id: "report-002",
    name: "Network Node Performance Report",
    description:
      "Node uptime, utilization, latency, customer impact and active network event context.",
    domain: "NETWORK",
    availableFormats: ["PDF", "CSV", "XLSX"],
    lastGenerated: "Today · 08:15 PM",
    scheduleLabel: "Daily",
  },
  {
    id: "report-003",
    name: "Billing Collection & Exposure Report",
    description:
      "Billed revenue, verified collections, outstanding exposure and billing lifecycle risk.",
    domain: "BILLING",
    availableFormats: ["PDF", "CSV", "XLSX"],
    lastGenerated: "Today · 07:30 PM",
    scheduleLabel: "Monthly",
  },
  {
    id: "report-004",
    name: "Incident Correlation Report",
    description:
      "Network incidents, correlated complaints, linked tickets and affected customer concentration.",
    domain: "SUPPORT",
    availableFormats: ["PDF", "CSV"],
    lastGenerated: "Yesterday · 11:18 PM",
    scheduleLabel: null,
  },
  {
    id: "report-005",
    name: "Technician Field Performance Report",
    description:
      "Technician workload, field resolution, completed jobs, SLA exposure and dispatch operations.",
    domain: "FIELD_OPERATIONS",
    availableFormats: ["PDF", "CSV", "XLSX"],
    lastGenerated: "Yesterday · 08:45 PM",
    scheduleLabel: "Weekly",
  },
  {
    id: "report-006",
    name: "Inventory Asset & Custody Report",
    description:
      "Serialized devices, customer assignments, technician custody, repair stock and low inventory exposure.",
    domain: "INVENTORY",
    availableFormats: ["PDF", "CSV", "XLSX"],
    lastGenerated: "02 Jul · 06:20 PM",
    scheduleLabel: "Weekly",
  },
];

export const recentReportRuns: RecentReportRun[] = [
  {
    id: "run-001",
    reportCode: "RPT-2026-0146",
    reportName: "Customer Service Lifecycle Report",
    domain: "CUSTOMERS",
    format: "PDF",
    status: "COMPLETED",
    requestedBy: "Nabeel · Owner",
    generatedAt: "2 min ago",
    period: "03 Jul 2026",
  },
  {
    id: "run-002",
    reportCode: "RPT-2026-0145",
    reportName: "Network Node Performance Report",
    domain: "NETWORK",
    format: "XLSX",
    status: "PROCESSING",
    requestedBy: "Nabeel · Owner",
    generatedAt: "6 min ago",
    period: "03 Jul 2026",
  },
  {
    id: "run-003",
    reportCode: "RPT-2026-0144",
    reportName: "Billing Collection & Exposure Report",
    domain: "BILLING",
    format: "PDF",
    status: "COMPLETED",
    requestedBy: "Nabeel · Owner",
    generatedAt: "48 min ago",
    period: "Jul 2026",
  },
  {
    id: "run-004",
    reportCode: "RPT-2026-0143",
    reportName: "Incident Correlation Report",
    domain: "SUPPORT",
    format: "CSV",
    status: "FAILED",
    requestedBy: "Operations Staff",
    generatedAt: "2 hours ago",
    period: "01 Jul - 03 Jul 2026",
  },
  {
    id: "run-005",
    reportCode: "RPT-2026-0142",
    reportName: "Inventory Asset & Custody Report",
    domain: "INVENTORY",
    format: "XLSX",
    status: "COMPLETED",
    requestedBy: "Nabeel · Owner",
    generatedAt: "Yesterday",
    period: "Week 27 · 2026",
  },
];