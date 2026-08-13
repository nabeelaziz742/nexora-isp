export interface OrganizationSettingsData {
  organizationName: string;
  organizationCode: string;
  supportPhone: string;
  supportEmail: string;
  city: string;
  timezone: string;
  currency: string;
}

export interface BillingAutomationSettingsData {
  gracePeriodDays: number;
  autoSuspensionEnabled: boolean;
  finalWarningDaysBeforeSuspension: number;
  autoRestoreAfterPayment: boolean;
  billNotificationsEnabled: boolean;
  paymentRemindersEnabled: boolean;
}

export interface NotificationChannelSetting {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  statusLabel: string;
}

export interface NotificationEventSetting {
  id: string;
  eventName: string;
  description: string;
  whatsapp: boolean;
  sms: boolean;
  email: boolean;
}