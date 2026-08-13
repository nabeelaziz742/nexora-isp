export type RevenueMetricTone =
  | "PRIMARY"
  | "HEALTHY"
  | "WARNING"
  | "CRITICAL"
  | "INTELLIGENCE";

export type RevenueSignalSeverity =
  | "CRITICAL"
  | "WARNING"
  | "INFO";

export type RevenueOpportunityType =
  | "PACKAGE_UPGRADE"
  | "COLLECTION_RECOVERY"
  | "REVENUE_LEAKAGE";

export interface RevenueMetric {
  id: string;
  label: string;
  value: string;
  description: string;
  change: string;
  tone: RevenueMetricTone;
}

export interface MonthlyRevenuePerformance {
  month: string;
  year: number;
  billed: number;
  collected: number;
}

export interface RevenueRiskSignal {
  id: string;
  title: string;
  description: string;
  severity: RevenueSignalSeverity;
  exposureAmount: number;
  affectedCustomers: number;
  confidence: number;
  actionLabel: string;
}

export interface RevenueOpportunity {
  id: string;
  title: string;
  description: string;
  type: RevenueOpportunityType;
  estimatedMonthlyImpact: number;
  customerSegment: string;
  customerCount: number;
  confidence: number;
}

export interface RevenueIntelligenceMetrics {
  monthly_billed: string;
  collected_revenue: string;
  outstanding_exposure: string;
  suspension_risk_revenue: string;
  upgrade_potential: string;
  revenue_health: number;
  collection_rate: string;
  billed_change_percent: string | null;
  previous_collected_revenue: string;
  outstanding_service_count: number;
  suspension_risk_service_count: number;
  upgrade_candidate_count: number;
}

export interface RevenueIntelligenceApiRiskSignal {
  id: string;
  title: string;
  description: string;
  severity: RevenueSignalSeverity;
  exposure_amount: string;
  affected_customers: number;
  confidence: number;
  action_label: string;
}

export interface RevenueIntelligenceApiOpportunity {
  id: string;
  title: string;
  description: string;
  type: RevenueOpportunityType;
  estimated_monthly_impact: string;
  customer_segment: string;
  customer_count: number;
  confidence: number;
}

export interface RevenueIntelligenceResponse {
  currency: string;
  period: {
    year: number;
    month: number;
    start: string;
    end: string;
  };
  metrics: RevenueIntelligenceMetrics;
  performance: Array<{
    month: string;
    year: number;
    billed: string;
    collected: string;
  }>;
  risk_signals: RevenueIntelligenceApiRiskSignal[];
  opportunities: RevenueIntelligenceApiOpportunity[];
  health_formula: {
    collection_rate_weight: number;
    outstanding_control_weight: number;
    suspension_exposure_control_weight: number;
    description: string;
  };
}