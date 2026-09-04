"use client";

import BillingAutomationSettings from "@/components/settings/BillingAutomationSettings";
import NotificationSettings from "@/components/settings/NotificationSettings";
import OrganizationSettings from "@/components/settings/OrganizationSettings";
import StaffRoleManagement from "@/components/settings/StaffRoleManagement";

import {
  billingAutomationSettings,
  notificationChannels,
  notificationEvents,
} from "@/data/mock/settings";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <section>
        <p className="text-xs font-medium uppercase tracking-[0.12em] text-[#38BDF8]">
          System Configuration & Security
        </p>

        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-[#F8FAFC]">
          ISP Tenant Settings
        </h1>

        <p className="mt-2 max-w-3xl text-sm text-[#64748B]">
          Configure organization context, staff capabilities, billing lifecycle automation and customer communication policies.
        </p>
      </section>

      {/* Live Organization Profile Settings */}
      <OrganizationSettings />

      {/* Staff & RBAC Role Management */}
      <StaffRoleManagement />

      {/* Billing Automation Preferences */}
      <BillingAutomationSettings settings={billingAutomationSettings} />

      {/* Notification Channel Policies */}
      <NotificationSettings
        channels={notificationChannels}
        events={notificationEvents}
      />
    </div>
  );
}
