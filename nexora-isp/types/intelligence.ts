export type IntelligenceSeverity =
  | "INFO"
  | "OPPORTUNITY"
  | "WARNING"
  | "CRITICAL";

export type IntelligenceDomain =
  | "NETWORK"
  | "BILLING"
  | "CUSTOMER"
  | "SUPPORT"
  | "FIELD_OPERATIONS";

export type CopilotPromptIcon =
  | "RADIO_TOWER"
  | "BADGE_DOLLAR"
  | "USERS"
  | "CIRCLE_ALERT"
  | "NETWORK"
  | "TRENDING_UP";

export interface CopilotSuggestedPrompt {
  id: string;
  title: string;
  prompt: string;
  domain: IntelligenceDomain;
  icon: CopilotPromptIcon;
}

export interface OperationalInsight {
  id: string;
  title: string;
  description: string;
  severity: IntelligenceSeverity;
  domain: IntelligenceDomain;
  confidence: number;
  detectedAt: string;
  actionLabel: string;
}

export interface CopilotActivityItem {
  id: string;
  query: string;
  summary: string;
  createdAt: string;
  requestedBy: string;
}