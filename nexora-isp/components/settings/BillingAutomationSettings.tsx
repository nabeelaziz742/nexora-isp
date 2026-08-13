import { ShieldCheck } from "lucide-react";

import type { BillingAutomationSettingsData } from "@/types/settings";

interface BillingAutomationSettingsProps {
  settings: BillingAutomationSettingsData;
}

export default function BillingAutomationSettings({
  settings,
}: BillingAutomationSettingsProps) {
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

      <div className="grid gap-5 p-5 xl:grid-cols-2">
        <NumberSetting
          label="Grace Period Days"
          description="Number of days after due date before suspension workflow progresses."
          value={settings.gracePeriodDays}
        />

        <NumberSetting
          label="Final Warning Timing"
          description="Days before planned suspension when the final customer warning is triggered."
          value={settings.finalWarningDaysBeforeSuspension}
        />

        <ToggleSetting
          label="Automatic Suspension"
          description="Allow eligible unpaid services to progress into automatic network suspension workflow."
          enabled={settings.autoSuspensionEnabled}
        />

        <ToggleSetting
          label="Auto Restore After Payment"
          description="Queue network access restoration after successful payment verification."
          enabled={settings.autoRestoreAfterPayment}
        />

        <ToggleSetting
          label="Bill Notifications"
          description="Trigger configured customer notification channels when bills are generated."
          enabled={settings.billNotificationsEnabled}
        />

        <ToggleSetting
          label="Payment Reminders"
          description="Send configured reminders during unpaid billing lifecycle stages."
          enabled={settings.paymentRemindersEnabled}
        />
      </div>

      <div className="flex justify-end border-t border-[#202938] px-5 py-4">
        <button className="bg-blue-600 px-4 py-2 text-xs font-medium text-white transition hover:bg-blue-500">
          Save Automation Policy
        </button>
      </div>
    </section>
  );
}

interface NumberSettingProps {
  label: string;
  description: string;
  value: number;
}

function NumberSetting({
  label,
  description,
  value,
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
          defaultValue={value}
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
}

function ToggleSetting({
  label,
  description,
  enabled,
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

      <div
        className={`relative mt-1 h-5 w-9 shrink-0 ${
          enabled ? "bg-blue-600" : "bg-slate-700"
        }`}
      >
        <span
          className={`absolute top-0.5 h-4 w-4 bg-white transition ${
            enabled ? "left-[18px]" : "left-0.5"
          }`}
        />
      </div>
    </div>
  );
}