import {
  BellRing,
  Clock3,
  RefreshCw,
  ShieldAlert,
  Zap,
} from "lucide-react";

import { BillingAutomationSettings } from "@/types/billing";

interface BillingAutomationPanelProps {
  settings: BillingAutomationSettings;
}

interface AutomationRowProps {
  icon: typeof Zap;
  label: string;
  description: string;
  value: string;
  enabled?: boolean;
}

function AutomationRow({
  icon: Icon,
  label,
  description,
  value,
  enabled,
}: AutomationRowProps) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-[#202938] py-4 last:border-b-0">
      <div className="flex min-w-0 items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center border border-[#202938] bg-[#121821]">
          <Icon className="h-4 w-4 text-[#94A3B8]" />
        </div>

        <div>
          <p className="text-sm font-medium text-[#F8FAFC]">
            {label}
          </p>

          <p className="mt-1 text-xs leading-5 text-[#64748B]">
            {description}
          </p>
        </div>
      </div>

      <div className="shrink-0 text-right">
        <p className="text-xs font-medium text-[#CBD5E1]">
          {value}
        </p>

        {enabled !== undefined && (
          <p
            className={`mt-1 text-[10px] font-medium ${
              enabled ? "text-[#22C55E]" : "text-[#64748B]"
            }`}
          >
            {enabled ? "ENABLED" : "DISABLED"}
          </p>
        )}
      </div>
    </div>
  );
}

export default function BillingAutomationPanel({
  settings,
}: BillingAutomationPanelProps) {
  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="flex items-center justify-between border-b border-[#202938] px-5 py-4">
        <div>
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-[#8B5CF6]" />

            <h2 className="text-sm font-semibold text-[#F8FAFC]">
              Billing Automation
            </h2>
          </div>

          <p className="mt-1 text-xs text-[#64748B]">
            Current service suspension and restoration policy
          </p>
        </div>

        <button className="text-xs font-medium text-[#3B82F6] transition-colors hover:text-[#60A5FA]">
          Configure
        </button>
      </div>

      <div className="px-5">
        <AutomationRow
          icon={Clock3}
          label="Grace Period"
          description="Configured time after due date before suspension workflow."
          value={`${settings.gracePeriodDays} days`}
        />

        <AutomationRow
          icon={ShieldAlert}
          label="Automatic Suspension"
          description="Suspend unpaid services after final payment verification."
          value="Policy"
          enabled={settings.autoSuspensionEnabled}
        />

        <AutomationRow
          icon={BellRing}
          label="Final Suspension Warning"
          description="Customer warning before automatic suspension action."
          value={`${settings.finalWarningHoursBeforeSuspension} hours before`}
        />

        <AutomationRow
          icon={RefreshCw}
          label="Auto Restore After Payment"
          description="Queue network restoration after verified payment."
          value="Network action"
          enabled={settings.autoRestoreAfterPaymentEnabled}
        />

        <AutomationRow
          icon={BellRing}
          label="Payment Notifications"
          description="Bill notifications and payment reminder workflow."
          value={
            settings.billNotificationEnabled &&
            settings.paymentReminderEnabled
              ? "Bill + Reminder"
              : "Partial"
          }
          enabled={
            settings.billNotificationEnabled ||
            settings.paymentReminderEnabled
          }
        />
      </div>
    </section>
  );
}