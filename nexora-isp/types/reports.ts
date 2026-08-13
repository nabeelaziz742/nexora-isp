export type ReportDomain =
  | "CUSTOMERS"
  | "NETWORK"
  | "BILLING"
  | "SUPPORT"
  | "FIELD_OPERATIONS"
  | "INVENTORY";

export type ReportFormat =
  | "PDF"
  | "CSV"
  | "XLSX";

export type ReportRunStatus =
  | "COMPLETED"
  | "PROCESSING"
  | "FAILED";

export type ReportMetricTone =
  | "PRIMARY"
  | "HEALTHY"
  | "WARNING"
  | "INTELLIGENCE";

export interface ReportMetric {
  id: string;
  label: string;
  value: string;
  description: string;
  tone: ReportMetricTone;
}

export interface ReportDefinition {
  id: string;
  name: string;
  description: string;
  domain: ReportDomain;
  availableFormats: ReportFormat[];
  lastGenerated: string;
  scheduleLabel: string | null;
}

export interface RecentReportRun {
  id: string;
  reportCode: string;
  reportName: string;
  domain: ReportDomain;
  format: ReportFormat;
  status: ReportRunStatus;
  requestedBy: string;
  generatedAt: string;
  period: string;
}