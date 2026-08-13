"use client";

import { useEffect, useMemo, useState } from "react";

import RevenueMetricCard from "@/components/intelligence/RevenueMetricCard";
import RevenueOpportunities from "@/components/intelligence/RevenueOpportunities";
import RevenuePerformance from "@/components/intelligence/RevenuePerformance";
import RevenueRiskSignals from "@/components/intelligence/RevenueRiskSignals";

import {
  getRevenueIntelligence,
  mapRevenueOpportunities,
  mapRevenuePerformance,
  mapRevenueRiskSignals,
} from "@/services/revenue-intelligence";

import type {
  RevenueIntelligenceResponse,
  RevenueMetric,
} from "@/types/revenue-intelligence";

function formatCurrency(
  currency: string,
  value: string,
) {
  const numericValue = Number(value);

  return `${currency} ${numericValue.toLocaleString(
    "en-PK",
    {
      maximumFractionDigits: 2,
    },
  )}`;
}

function buildRevenueMetrics(
  data: RevenueIntelligenceResponse,
): RevenueMetric[] {
  const metrics = data.metrics;

  const billedChange =
    metrics.billed_change_percent === null
      ? "No previous billing cycle baseline"
      : `${Number(
          metrics.billed_change_percent,
        ).toFixed(1)}% vs previous cycle`;

  const healthTone =
    metrics.revenue_health >= 80
      ? "HEALTHY"
      : metrics.revenue_health >= 60
        ? "WARNING"
        : "CRITICAL";

  return [
    {
      id: "monthly-billed",
      label: "Monthly Billed",
      value: formatCurrency(
        data.currency,
        metrics.monthly_billed,
      ),
      description: "Current billing cycle value",
      change: billedChange,
      tone: "PRIMARY",
    },
    {
      id: "collected-revenue",
      label: "Collected Revenue",
      value: formatCurrency(
        data.currency,
        metrics.collected_revenue,
      ),
      description: "Verified customer payments",
      change: `${Number(
        metrics.collection_rate,
      ).toFixed(1)}% collection rate`,
      tone: "HEALTHY",
    },
    {
      id: "outstanding-exposure",
      label: "Outstanding Exposure",
      value: formatCurrency(
        data.currency,
        metrics.outstanding_exposure,
      ),
      description: "Uncollected billed revenue",
      change: `${metrics.outstanding_service_count} service accounts`,
      tone: "WARNING",
    },
    {
      id: "suspension-risk",
      label: "Suspension Risk Revenue",
      value: formatCurrency(
        data.currency,
        metrics.suspension_risk_revenue,
      ),
      description:
        "Non-payment suspension lifecycle exposure",
      change: `${metrics.suspension_risk_service_count} customer services`,
      tone: "CRITICAL",
    },
    {
      id: "upgrade-potential",
      label: "Upgrade Potential",
      value: formatCurrency(
        data.currency,
        metrics.upgrade_potential,
      ),
      description:
        "Deterministic package ladder opportunity",
      change: `${metrics.upgrade_candidate_count} subscriber candidates`,
      tone: "INTELLIGENCE",
    },
    {
      id: "revenue-health",
      label: "Revenue Health",
      value: `${metrics.revenue_health} / 100`,
      description: "Operational revenue score",
      change: data.health_formula.description,
      tone: healthTone,
    },
  ];
}

export default function RevenueIntelligencePage() {
  const [data, setData] =
    useState<RevenueIntelligenceResponse | null>(null);

  const [isLoading, setIsLoading] = useState(true);

  const [error, setError] = useState<string | null>(
    null,
  );

  useEffect(() => {
    let active = true;

    async function loadRevenueIntelligence() {
      try {
        setIsLoading(true);
        setError(null);

        const response =
          await getRevenueIntelligence();

        if (active) {
          setData(response);
        }
      } catch (requestError) {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Revenue intelligence could not be loaded.",
          );
        }
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    }

    void loadRevenueIntelligence();

    return () => {
      active = false;
    };
  }, []);

  const revenueMetrics = useMemo(
    () => (data ? buildRevenueMetrics(data) : []),
    [data],
  );

  const monthlyRevenuePerformance = useMemo(
    () => (data ? mapRevenuePerformance(data) : []),
    [data],
  );

  const revenueRiskSignals = useMemo(
    () => (data ? mapRevenueRiskSignals(data) : []),
    [data],
  );

  const revenueOpportunities = useMemo(
    () => (data ? mapRevenueOpportunities(data) : []),
    [data],
  );

  if (isLoading) {
    return (
      <div className="space-y-6">
        <section>
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-violet-400">
            Financial Intelligence
          </p>

          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-50">
            Revenue Intelligence
          </h1>

          <p className="mt-2 text-sm text-slate-500">
            Loading verified tenant billing intelligence...
          </p>
        </section>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <section>
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-violet-400">
            Financial Intelligence
          </p>

          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-50">
            Revenue Intelligence
          </h1>
        </section>

        <div className="border border-red-500/20 bg-red-500/5 px-5 py-4">
          <p className="text-sm font-medium text-red-400">
            Revenue intelligence unavailable
          </p>

          <p className="mt-2 text-xs text-slate-500">
            {error ??
              "Verified billing intelligence could not be loaded."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section>
        <p className="text-xs font-medium uppercase tracking-[0.12em] text-violet-400">
          Financial Intelligence
        </p>

        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-50">
          Revenue Intelligence
        </h1>

        <p className="mt-2 max-w-3xl text-sm text-slate-500">
          Monitor collection performance, identify revenue exposure
          and surface recurring growth opportunities across ISP
          operations.
        </p>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
        {revenueMetrics.map((metric) => (
          <RevenueMetricCard
            key={metric.id}
            metric={metric}
          />
        ))}
      </section>

      <RevenuePerformance
        data={monthlyRevenuePerformance}
      />

      <div className="grid gap-6 2xl:grid-cols-[minmax(0,1.6fr)_minmax(340px,0.7fr)]">
        {revenueRiskSignals.length > 0 ? (
          <RevenueRiskSignals
            signals={revenueRiskSignals}
          />
        ) : (
          <section className="border border-[#202938] bg-[#0D1117] px-5 py-5">
            <h2 className="text-sm font-semibold text-slate-100">
              Revenue Risk Intelligence
            </h2>

            <p className="mt-2 text-xs text-slate-500">
              No verified revenue risk signals are present
              in the current tenant billing data.
            </p>
          </section>
        )}

        {revenueOpportunities.length > 0 ? (
          <RevenueOpportunities
            opportunities={revenueOpportunities}
          />
        ) : (
          <section className="border border-[#202938] bg-[#0D1117] px-5 py-5">
            <h2 className="text-sm font-semibold text-slate-100">
              Revenue Opportunities
            </h2>

            <p className="mt-2 text-xs text-slate-500">
              No deterministic revenue opportunities are
              available from current package and billing data.
            </p>
          </section>
        )}
      </div>
    </div>
  );
}