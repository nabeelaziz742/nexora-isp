import {
  Activity,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";

interface ISPHealthScoreProps {
  score: number;
}

export default function ISPHealthScore({
  score,
}: ISPHealthScoreProps) {
  const normalizedScore = Math.max(
    0,
    Math.min(100, score),
  );

  const healthState =
    normalizedScore >= 90
      ? "Excellent"
      : normalizedScore >= 75
        ? "Healthy"
        : normalizedScore >= 50
          ? "Degraded"
          : "Critical";

  const isCritical = normalizedScore < 50;
  const isDegraded =
    normalizedScore >= 50 &&
    normalizedScore < 75;
  const isHealthy =
    normalizedScore >= 75;

  return (
    <section className="border border-[var(--border)] bg-[var(--surface)] p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">
            ISP Health
          </p>

          <h3 className="mt-1.5 text-sm font-semibold text-white">
            Operational Health Score
          </h3>
        </div>

        <div
          className={`flex size-9 items-center justify-center rounded-md border ${
            isCritical
              ? "border-red-500/20 bg-red-500/10"
              : isDegraded
                ? "border-amber-500/20 bg-amber-500/10"
                : "border-emerald-500/20 bg-emerald-500/10"
          }`}
        >
          <Activity
            className={`size-4 ${
              isCritical
                ? "text-red-400"
                : isDegraded
                  ? "text-amber-400"
                  : "text-emerald-400"
            }`}
          />
        </div>
      </div>

      <div className="mt-8 flex min-h-[112px] flex-col items-center justify-center text-center">
        <div
          className={`flex size-10 items-center justify-center rounded-md border ${
            isCritical
              ? "border-red-500/20 bg-red-500/10"
              : isDegraded
                ? "border-amber-500/20 bg-amber-500/10"
                : "border-emerald-500/20 bg-emerald-500/10"
          }`}
        >
          {isCritical ? (
            <ShieldAlert className="size-4 text-red-400" />
          ) : (
            <ShieldCheck
              className={`size-4 ${
                isDegraded
                  ? "text-amber-400"
                  : "text-emerald-400"
              }`}
            />
          )}
        </div>

        <p className="mt-3 text-3xl font-semibold tracking-tight text-white">
          {normalizedScore}

          <span className="text-sm text-[var(--text-muted)]">
            {" "}
            / 100
          </span>
        </p>

        <p
          className={`mt-2 text-[12px] font-semibold ${
            isCritical
              ? "text-red-400"
              : isDegraded
                ? "text-amber-400"
                : "text-emerald-400"
          }`}
        >
          {healthState}
        </p>

        <p className="mt-1 max-w-[260px] text-[10px] leading-4 text-[var(--text-muted)]">
          Deterministic operational score based on
          network availability, critical operations,
          provisioning, inventory and notification
          health.
        </p>
      </div>
    </section>
  );
}