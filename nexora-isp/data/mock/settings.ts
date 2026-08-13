import type {
  BillingAutomationSettingsData,
  NotificationChannelSetting,
  NotificationEventSetting,
  OrganizationSettingsData,
} from "@/types/settings";

export const organizationSettings: OrganizationSettingsData = {
  organizationName: "NEXORA FIBER",
  organizationCode: "NXF-001",
  supportPhone: "+92 300 0000000",
  supportEmail: "support@nexorafiber.example",
  city: "Lahore",
  timezone: "Asia/Karachi",
  currency: "PKR",
};

export const billingAutomationSettings: BillingAutomationSettingsData = {
  gracePeriodDays: 5,
  autoSuspensionEnabled: true,
  finalWarningDaysBeforeSuspension: 1,
  autoRestoreAfterPayment: true,
  billNotificationsEnabled: true,
  paymentRemindersEnabled: true,
};

export const notificationChannels: NotificationChannelSetting[] = [
  {
    id: "channel-whatsapp",
    name: "WhatsApp",
    description:
      "Customer billing, outage and service lifecycle communication.",
    enabled: true,
    statusLabel: "Configuration Required",
  },
  {
    id: "channel-sms",
    name: "SMS",
    description:
      "Critical service alerts and payment workflow notifications.",
    enabled: true,
    statusLabel: "Configuration Required",
  },
  {
    id: "channel-email",
    name: "Email",
    description:
      "Bills, payment confirmations and structured customer notices.",
    enabled: true,
    statusLabel: "Configuration Required",
  },
  {
    id: "channel-push",
    name: "Push Notifications",
    description:
      "Future customer self-service application notifications.",
    enabled: false,
    statusLabel: "Not Available Yet",
  },
];

export const notificationEvents: NotificationEventSetting[] = [
  {
    id: "event-bill-generated",
    eventName: "Bill Generated",
    description: "Notify customer when a new billing cycle bill is generated.",
    whatsapp: true,
    sms: false,
    email: true,
  },
  {
    id: "event-payment-reminder",
    eventName: "Payment Reminder",
    description: "Send payment reminder during configured collection workflow.",
    whatsapp: true,
    sms: true,
    email: false,
  },
  {
    id: "event-final-warning",
    eventName: "Final Suspension Warning",
    description:
      "Notify customer before service enters automatic suspension workflow.",
    whatsapp: true,
    sms: true,
    email: true,
  },
  {
    id: "event-service-suspended",
    eventName: "Service Suspended",
    description:
      "Notify customer when service is suspended for verified non-payment.",
    whatsapp: true,
    sms: true,
    email: true,
  },
  {
    id: "event-service-restored",
    eventName: "Service Restored",
    description:
      "Confirm service restoration after payment verification and network access restoration.",
    whatsapp: true,
    sms: true,
    email: true,
  },
  {
    id: "event-network-outage",
    eventName: "Network Outage",
    description:
      "Notify affected customers when a sustained network incident is confirmed.",
    whatsapp: true,
    sms: true,
    email: false,
  },
];