"use client";

import {
  Activity,
  Banknote,
  CheckCircle2,
  Loader2,
  Package,
  RefreshCw,
  Users,
  Wifi,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  PackageContribution,
  PackageRevenueContext,
  ServiceStatusDistribution,
  SubscriberOverview,
  reportsService,
} from "@/services/reports.service";

function formatMoney(value: string | number) {
  const amount = Number(value);

  return new Intl.NumberFormat("en-PK", {
    style: "currency",
    currency: "PKR",
    maximumFractionDigits: 0,
  }).format(Number.isFinite(amount) ? amount : 0);
}

function MetricCard({
  label,
  value,
  description,
  icon: Icon,
}: {
  label: string;
  value: number;
  description: string;
  icon: typeof Users;
}) {
  return (
    <div className="border border-[#202938] bg-[#0D1117] p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-slate-500">
            {label}
          </p>

          <p className="mt-3 text-2xl font-semibold text-slate-50">
            {value}
          </p>
        </div>

        <div className="flex h-9 w-9 items-center justify-center border border-[#202938] bg-[#121821]">
          <Icon className="h-4 w-4 text-blue-400" />
        </div>
      </div>

      <p className="mt-3 border-t border-[#202938] pt-3 text-xs text-slate-500">
        {description}
      </p>
    </div>
  );
}

export default function ReportsPage() {
  const [overview, setOverview] =
    useState<SubscriberOverview | null>(null);

  const [
    serviceDistribution,
    setServiceDistribution,
  ] = useState<ServiceStatusDistribution[]>([]);

  const [
    packageContribution,
    setPackageContribution,
  ] = useState<PackageContribution[]>([]);

  const [
    packageRevenue,
    setPackageRevenue,
  ] = useState<PackageRevenueContext[]>([]);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const loadReports = useCallback(
    async (background = false) => {
      try {
        if (background) {
          setRefreshing(true);
        } else {
          setLoading(true);
        }

        setError("");

        const [
          overviewResponse,
          distributionResponse,
          contributionResponse,
          revenueResponse,
        ] = await Promise.all([
          reportsService.getSubscriberOverview(),
          reportsService.getServiceStatusDistribution(),
          reportsService.getPackageContribution(),
          reportsService.getPackageRevenueContext(),
        ]);

        setOverview(overviewResponse);
        setServiceDistribution(distributionResponse);
        setPackageContribution(contributionResponse);
        setPackageRevenue(revenueResponse);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load reporting data.",
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [],
  );

  useEffect(() => {
    void loadReports();
  }, [loadReports]);

  const revenueByPackage = useMemo(() => {
    return new Map(
      packageRevenue.map((item) => [
        item.package_id,
        item,
      ]),
    );
  }, [packageRevenue]);

  const revenueTotals = useMemo(() => {
    return packageRevenue.reduce(
      (totals, item) => ({
        invoiced:
          totals.invoiced
          + Number(item.invoiced_amount),
        collected:
          totals.collected
          + Number(item.collected_amount),
        outstanding:
          totals.outstanding
          + Number(item.outstanding_amount),
      }),
      {
        invoiced: 0,
        collected: 0,
        outstanding: 0,
      },
    );
  }, [packageRevenue]);

  if (loading) {
    return (
      <div className="flex min-h-[420px] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-blue-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-blue-400">
            Operational Reporting
          </p>

          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-50">
            Reports Center
          </h1>

          <p className="mt-2 max-w-3xl text-sm text-slate-500">
            Live tenant reporting across subscribers, service
            lifecycle, package contribution and billing revenue
            context.
          </p>
        </div>

        <button
          type="button"
          disabled={refreshing}
          onClick={() => void loadReports(true)}
          className="flex h-10 items-center gap-2 border border-[#202938] bg-[#0D1117] px-4 text-xs text-slate-300 transition hover:border-blue-500 hover:text-blue-400 disabled:opacity-50"
        >
          <RefreshCw
            className={`h-4 w-4 ${
              refreshing ? "animate-spin" : ""
            }`}
          />

          Refresh Reports
        </button>
      </section>

      {error ? (
        <div className="border border-red-900/60 bg-red-950/30 px-4 py-3 text-xs text-red-400">
          {error}
        </div>
      ) : null}

      {overview ? (
        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
          <MetricCard
            label="Customers"
            value={overview.total_customers}
            description={`${overview.active_customers} active customers`}
            icon={Users}
          />

          <MetricCard
            label="Active Services"
            value={overview.active_services}
            description={`${overview.total_services} total services`}
            icon={Wifi}
          />

          <MetricCard
            label="Non-Active Services"
            value={overview.non_active_services}
            description="Services outside active state"
            icon={Activity}
          />

          <MetricCard
            label="Service Customers"
            value={overview.customers_with_services}
            description="Customers with service accounts"
            icon={CheckCircle2}
          />

          <MetricCard
            label="Without Service"
            value={overview.customers_without_services}
            description="Customers without service accounts"
            icon={Users}
          />

          <MetricCard
            label="Active Packages"
            value={overview.active_packages}
            description={`${overview.total_packages} total packages`}
            icon={Package}
          />
        </section>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="border border-[#202938] bg-[#0D1117]">
          <div className="border-b border-[#202938] px-5 py-4">
            <h2 className="text-sm font-semibold text-slate-100">
              Service Status Distribution
            </h2>

            <p className="mt-1 text-xs text-slate-500">
              Current service accounts grouped by lifecycle
              status.
            </p>
          </div>

          <div className="p-5">
            {serviceDistribution.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-500">
                No service distribution records found.
              </p>
            ) : (
              <div className="space-y-4">
                {serviceDistribution.map((item) => {
                  const total =
                    overview?.total_services ?? 0;

                  const percentage =
                    total > 0
                      ? (
                          (item.service_count / total)
                          * 100
                        ).toFixed(1)
                      : "0.0";

                  return (
                    <div key={item.status}>
                      <div className="flex items-center justify-between gap-4">
                        <span className="text-xs font-medium text-slate-300">
                          {item.status}
                        </span>

                        <span className="text-xs text-slate-500">
                          {item.service_count} · {percentage}%
                        </span>
                      </div>

                      <div className="mt-2 h-1.5 overflow-hidden bg-[#121821]">
                        <div
                          className="h-full bg-blue-500"
                          style={{
                            width: `${Math.min(
                              Number(percentage),
                              100,
                            )}%`,
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        <div className="border border-[#202938] bg-[#0D1117]">
          <div className="border-b border-[#202938] px-5 py-4">
            <h2 className="text-sm font-semibold text-slate-100">
              Revenue Context
            </h2>

            <p className="mt-1 text-xs text-slate-500">
              Billing totals represented by package-linked
              services.
            </p>
          </div>

          <div className="grid gap-3 p-5 sm:grid-cols-3">
            <div className="border border-[#202938] bg-[#090D13] p-4">
              <Banknote className="h-4 w-4 text-blue-400" />

              <p className="mt-4 text-[10px] uppercase tracking-[0.12em] text-slate-500">
                Invoiced
              </p>

              <p className="mt-2 text-lg font-semibold text-slate-100">
                {formatMoney(revenueTotals.invoiced)}
              </p>
            </div>

            <div className="border border-[#202938] bg-[#090D13] p-4">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />

              <p className="mt-4 text-[10px] uppercase tracking-[0.12em] text-slate-500">
                Collected
              </p>

              <p className="mt-2 text-lg font-semibold text-slate-100">
                {formatMoney(revenueTotals.collected)}
              </p>
            </div>

            <div className="border border-[#202938] bg-[#090D13] p-4">
              <Activity className="h-4 w-4 text-amber-400" />

              <p className="mt-4 text-[10px] uppercase tracking-[0.12em] text-slate-500">
                Outstanding
              </p>

              <p className="mt-2 text-lg font-semibold text-slate-100">
                {formatMoney(revenueTotals.outstanding)}
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="border border-[#202938] bg-[#0D1117]">
        <div className="border-b border-[#202938] px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-100">
            Package Contribution & Revenue
          </h2>

          <p className="mt-1 text-xs text-slate-500">
            Real package service adoption joined with package
            billing context.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[1100px] text-left">
            <thead>
              <tr className="border-b border-[#202938] text-[10px] uppercase tracking-[0.12em] text-slate-500">
                <th className="px-5 py-3">Package</th>
                <th className="px-5 py-3">Speed</th>
                <th className="px-5 py-3">Monthly Price</th>
                <th className="px-5 py-3">Services</th>
                <th className="px-5 py-3">Active</th>
                <th className="px-5 py-3">Invoiced</th>
                <th className="px-5 py-3">Collected</th>
                <th className="px-5 py-3">Outstanding</th>
              </tr>
            </thead>

            <tbody>
              {packageContribution.length === 0 ? (
                <tr>
                  <td
                    colSpan={8}
                    className="px-5 py-10 text-center text-sm text-slate-500"
                  >
                    No package contribution records found.
                  </td>
                </tr>
              ) : (
                packageContribution.map((item) => {
                  const revenue = revenueByPackage.get(
                    item.package_id,
                  );

                  return (
                    <tr
                      key={item.package_id}
                      className="border-b border-[#202938]/80"
                    >
                      <td className="px-5 py-4">
                        <p className="text-xs font-medium text-slate-100">
                          {item.package_name}
                        </p>

                        <p className="mt-1 text-[11px] text-slate-600">
                          {item.package_code}
                        </p>
                      </td>

                      <td className="px-5 py-4 text-xs text-slate-300">
                        {item.download_speed_mbps} /{" "}
                        {item.upload_speed_mbps} Mbps
                      </td>

                      <td className="px-5 py-4 text-xs text-slate-300">
                        {formatMoney(item.monthly_price)}
                      </td>

                      <td className="px-5 py-4 text-xs text-slate-100">
                        {item.service_count}
                      </td>

                      <td className="px-5 py-4 text-xs text-emerald-400">
                        {item.active_service_count}
                      </td>

                      <td className="px-5 py-4 text-xs text-slate-300">
                        {formatMoney(
                          revenue?.invoiced_amount ?? 0,
                        )}
                      </td>

                      <td className="px-5 py-4 text-xs text-emerald-400">
                        {formatMoney(
                          revenue?.collected_amount ?? 0,
                        )}
                      </td>

                      <td className="px-5 py-4 text-xs text-amber-400">
                        {formatMoney(
                          revenue?.outstanding_amount ?? 0,
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>

      <p className="text-[11px] text-slate-600">
        Reports are calculated from current tenant operational
        records. No mock report runs, fake generated reports or
        unsupported custom-report execution is displayed.
      </p>
    </div>
  );
}