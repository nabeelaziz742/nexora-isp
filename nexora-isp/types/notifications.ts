export type NotificationChannel =
  | "SMS"
  | "WHATSAPP";

export type NotificationJobStatus =
  | "PENDING"
  | "PROCESSING"
  | "SENT"
  | "FAILED"
  | "CANCELLED";

export type NotificationMetricTone =
  | "PRIMARY"
  | "HEALTHY"
  | "WARNING"
  | "CRITICAL";

export interface NotificationJob {
  id: string;
  channel: NotificationChannel;
  status: NotificationJobStatus;
  event_type: string;
  recipient: string;
  subject: string;
  message: string;
  context: Record<string, unknown>;
  customer_id: string;
  customer_number: string;
  customer_name: string;
  service_account_id: string | null;
  service_number: string | null;
  service_status: string | null;
  provider_name: string;
  provider_message_id: string;
  failure_reason: string;
  attempt_count: number;
  processing_started_at: string | null;
  sent_at: string | null;
  failed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface NotificationSummary {
  total: number;
  pending: number;
  processing: number;
  sent: number;
  failed: number;
  cancelled: number;
  sms: number;
  whatsapp: number;
}

export interface NotificationMetric {
  id: string;
  label: string;
  value: string;
  description: string;
  tone: NotificationMetricTone;
}

export interface NotificationJobFilters {
  status?: NotificationJobStatus | "";
  channel?: NotificationChannel | "";
  event_type?: string;
  customer_id?: string;
  service_account_id?: string;
  search?: string;
}

export interface QueueNotificationPayload {
  customer_id: string;
  service_account_id?: string | null;
  channel: NotificationChannel;
  event_type: string;
  subject?: string;
  message: string;
  context?: Record<string, unknown>;
}

export interface StartNotificationProcessingPayload {
  provider_name: string;
}

export interface MarkNotificationSentPayload {
  provider_message_id: string;
}

export interface MarkNotificationFailedPayload {
  failure_reason: string;
}

export interface AutomationDeliverySummary {
  id: string;
  eventType: string;
  title: string;
  description?: string;
  targeted: number;
  delivered: number;
  failed: number;
  whatsappDelivered: number;
  smsDelivered: number;
  automationContext?: string;
}

export type NotificationDeliveryLogStatus =
  | NotificationJobStatus
  | "DELIVERED";

export interface NotificationDeliveryLogItem {
  id: string;
  eventCode: string;
  customerName: string;
  customerCode: string;
  eventType: string;
  channel: NotificationChannel;
  status: NotificationDeliveryLogStatus;
  messageContext: string;
  triggeredAt: string;
}