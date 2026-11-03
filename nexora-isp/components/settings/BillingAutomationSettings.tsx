"use client";

import { useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";

import ErrorState from "@/components/ui/ErrorState";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { useToast } from "@/hooks/useToast";
import { suspensionService } from "@/services/suspension.service";
import type { SuspensionPolicy } from "@/types/suspension";

type PolicyForm = Pick<
  SuspensionPolicy,
  | "grace_period_days"
  | "warning_days_before_suspension"
  | "auto_suspension_enabled"
  | "auto_restoration_enabled"
  | "restore_on_partial_payment"
  | "send_suspension_warning"
  | "ptp_exemption_enabled"
>;

function toForm(policy: SuspensionPolicy): PolicyForm {
  return {
    grace_period_days: policy.grace_period_days,
    warning_days_before_suspension: policy.warning_days_before_suspension,
    auto_suspension_enabled: policy.auto_suspension_enabled,
    auto_restoration_enabled: policy.auto_restoration_enabled,
    restore_on_partial_payment: policy.restore_on_partial_payment,
    send_suspension_warning: policy.send_suspension_warning,
    ptp_exemption_enabled: policy.ptp_exemption_enabled,
  };
}

export default function BillingAutomationSettings() {
  const { success, error: toastError } = useToast();

  const [form, setForm] = useState<PolicyForm | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function loadPolicy() {
    try {
      setLoading(true);
      setError(null);
      setForm(toForm(await suspensionService.getPolicy()));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load the automation policy.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadPolicy();
  }, []);

  async function handleSave() {
    if (!form) return;

    try {
      setSaving(true);
      setForm(toForm(await suspensionService.updatePolicy(form)));
      success("Billing automation policy saved.");
    } catch (err) {
      toastError(err instanceof Error ? err.message : "Failed to save the automation policy.");
    } finally {
      setSaving(false);
    }
  }

  function update<K extends keyof PolicyForm>(key: K, value: PolicyForm[K]) {
    setForm((current) => (current ? { ...current, [key]: value } : current));
  }

  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="border-b border-[#202938] px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center bg-blue-500/10">
            <ShieldCheck className="h-4 w-4 text-blue-400" />
          </div>

          <div>
            <h2 className="text-sm font-semibold text-slate-100">
              Billing & Service Automation
            </h2>

            <p className="mt-1 text-xs text-slate-500">
              Configure non-payment service lifecycle policies
            </p>
          </div>
        </div>
      </div>

      <div className="border-b border-[#202938] bg-amber-500/5 px-5 py-4">
        <p className="text-xs leading-5 text-amber-300">
          Grace period and suspension timing are ISP policy
          configuration values. They are not fixed NEXORA business
          rules.
        </p>
      </div>

      {loading ? (
        <div className="p-5">
          <SkeletonCard />
        </div>
      ) : error || !form ? (
        <div className="p-5">
          <ErrorState message={error ?? "Unable to load the automation policy."} onRetry={() => void loadPolicy()} />
        </div>
      ) : (
        <>
          <div className="grid gap-5 p-5 xl:grid-cols-2">
            <NumberSetting
              label="Grace Period Days"
              description="Number of days after due date before suspension workflow progresses."
              value={form.grace_period_days}
              onChange={(value) => update("grace_period_days", value)}
            />

            <NumberSetting
              label="Final Warning Timing"
              description="Days before planned suspension when the final customer warning is triggered."
              value={form.warning_days_before_suspension}
              onChange={(value) => update("warning_days_before_suspension", value)}
            />

            <ToggleSetting
              label="Automatic Suspension"
              description="Allow eligible unpaid services to progress into automatic network suspension workflow."
              enabled={form.auto_suspension_enabled}
              onToggle={() => update("auto_suspension_enabled", !form.auto_suspension_enabled)}
            />

            <ToggleSetting
              label="Auto Restore After Payment"
              description="Queue network access restoration after successful payment verification."
              enabled={form.auto_restoration_enabled}
              onToggle={() => update("auto_restoration_enabled", !form.auto_restoration_enabled)}
            />

            <ToggleSetting
              label="Restore on Partial Payment"
              description="Restore service even when the customer clears only part of the outstanding balance."
              enabled={form.restore_on_partial_payment}
              onToggle={() => update("restore_on_partial_payment", !form.restore_on_partial_payment)}
            />

            <ToggleSetting
              label="Send Suspension Warning"
              description="Notify customers on configured channels before their service is suspended."
              enabled={form.send_suspension_warning}
              onToggle={() => update("send_suspension_warning", !form.send_suspension_warning)}
            />

            <ToggleSetting
              label="Promise-to-Pay Exemption"
              description="Skip automatic suspension while a customer has an active promise to pay."
              enabled={form.ptp_exemption_enabled}
              onToggle={() => update("ptp_exemption_enabled", !form.ptp_exemption_enabled)}
            />
          </div>

          <div className="flex justify-end border-t border-[#202938] px-5 py-4">
            <button
              type="button"
              onClick={() => void handleSave()}
              disabled={saving}
              className="bg-blue-600 px-4 py-2 text-xs font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save Automation Policy"}
            </button>
          </div>
        </>
      )}
    </section>
  );
}

interface NumberSettingProps {
  label: string;
  description: string;
  value: number;
  onChange: (value: number) => void;
}

function NumberSetting({
  label,
  description,
  value,
  onChange,
}: NumberSettingProps) {
  return (
    <div className="border border-[#202938] bg-[#121821] p-4">
      <label>
        <span className="text-xs font-medium text-slate-200">
          {label}
        </span>

        <p className="mt-1 text-[11px] leading-5 text-slate-500">
          {description}
        </p>

        <input
          type="number"
          min={0}
          value={value}
          onChange={(event) => onChange(Math.max(0, Number(event.target.value) || 0))}
          className="mt-4 h-10 w-full border border-[#202938] bg-[#070A0F] px-3 text-sm font-medium text-slate-200 outline-none transition focus:border-blue-500"
        />
      </label>
    </div>
  );
}

interface ToggleSettingProps {
  label: string;
  description: string;
  enabled: boolean;
  onToggle: () => void;
}

function ToggleSetting({
  label,
  description,
  enabled,
  onToggle,
}: ToggleSettingProps) {
  return (
    <div className="flex items-start justify-between gap-4 border border-[#202938] bg-[#121821] p-4">
      <div>
        <p className="text-xs font-medium text-slate-200">
          {label}
        </p>

        <p className="mt-1 text-[11px] leading-5 text-slate-500">
          {description}
        </p>
      </div>

      <button
        type="button"
        role="switch"
        aria-checked={enabled}
        aria-label={label}
        onClick={onToggle}
        className={`relative mt-1 h-5 w-9 shrink-0 ${
          enabled ? "bg-blue-600" : "bg-slate-700"
        }`}
      >
        <span
          className={`absolute top-0.5 h-4 w-4 bg-white transition ${
            enabled ? "left-[18px]" : "left-0.5"
          }`}
        />
      </button>
    </div>
  );
}
