import { apiClient } from "@/services/api-client";

import type {
  MonthlyRevenuePerformance,
  RevenueIntelligenceResponse,
  RevenueOpportunity,
  RevenueRiskSignal,
} from "@/types/revenue-intelligence";

export async function getRevenueIntelligence(): Promise<RevenueIntelligenceResponse> {
  return apiClient.get<RevenueIntelligenceResponse>(
    "/billing/revenue-intelligence/",
  );
}

export function mapRevenuePerformance(
  response: RevenueIntelligenceResponse,
): MonthlyRevenuePerformance[] {
  return response.performance.map((item) => ({
    month: item.month,
    year: item.year,
    billed: Number(item.billed),
    collected: Number(item.collected),
  }));
}

export function mapRevenueRiskSignals(
  response: RevenueIntelligenceResponse,
): RevenueRiskSignal[] {
  return response.risk_signals.map((signal) => ({
    id: signal.id,
    title: signal.title,
    description: signal.description,
    severity: signal.severity,
    exposureAmount: Number(signal.exposure_amount),
    affectedCustomers: signal.affected_customers,
    confidence: signal.confidence,
    actionLabel: signal.action_label,
  }));
}

export function mapRevenueOpportunities(
  response: RevenueIntelligenceResponse,
): RevenueOpportunity[] {
  return response.opportunities.map(
    (opportunity) => ({
      id: opportunity.id,
      title: opportunity.title,
      description: opportunity.description,
      type: opportunity.type,
      estimatedMonthlyImpact: Number(
        opportunity.estimated_monthly_impact,
      ),
      customerSegment: opportunity.customer_segment,
      customerCount: opportunity.customer_count,
      confidence: opportunity.confidence,
    }),
  );
}