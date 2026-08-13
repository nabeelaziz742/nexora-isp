import BillingAutomationSettings from "@/components/settings/BillingAutomationSettings";
import NotificationSettings from "@/components/settings/NotificationSettings";
import OrganizationSettings from "@/components/settings/OrganizationSettings";

import {
  billingAutomationSettings,
  notificationChannels,
  notificationEvents,
  organizationSettings,
} from "@/data/mock/settings";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <section>
        <p className="text-xs font-medium uppercase tracking-[0.12em] text-blue-400">
          System Configuration
        </p>

        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-50">
          ISP Settings
        </h1>

        <p className="mt-2 max-w-3xl text-sm text-slate-500">
          Configure organization context, billing lifecycle
          automation and customer communication policies.
        </p>
      </section>

      <OrganizationSettings
        settings={organizationSettings}
      />

      <BillingAutomationSettings
        settings={billingAutomationSettings}
      />

      <NotificationSettings
        channels={notificationChannels}
        events={notificationEvents}
      />
    </div>
  );
}