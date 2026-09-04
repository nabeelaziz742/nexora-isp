export interface SuspensionPolicy {
  id: string;
  grace_period_days: number;
  suspension_threshold_days: number;
  minimum_outstanding_amount: string;
  auto_suspension_enabled: boolean;
  auto_restoration_enabled: boolean;
  restore_on_partial_payment: boolean;
  ptp_exemption_enabled: boolean;
  warning_days_before_suspension: number;
  send_suspension_warning: boolean;
  updated_at?: string;
}

export interface ServiceSuspensionLog {
  id: string;
  service_account: string;
  service_number: string;
  customer: string;
  customer_name: string;
  event_type: 'SUSPENSION' | 'RESTORATION' | 'WARNING';
  trigger_type: 'SYSTEM_AUTOMATED' | 'MANUAL_STAFF' | 'PAYMENT_RESTORE' | 'ADMIN_OVERRIDE';
  previous_status: string;
  new_status: string;
  outstanding_amount: string;
  reason: string;
  actor_name: string | null;
  invoices_snapshot: Array<{
    invoice_id: string;
    invoice_number: string;
    due_date: string;
    total_amount: string;
    paid_amount: string;
    outstanding_amount: string;
  }>;
  linked_payment_id?: string | null;
  linked_promise_id?: string | null;
  created_at: string;
}

export interface OverdueEligibilityItem {
  service_id: string;
  service_number: string;
  customer_id: string;
  customer_name: string;
  phone: string;
  package_name: string;
  status: string;
  total_outstanding: string;
  oldest_due_date: string | null;
  days_past_due: number;
  days_overdue: number;
  in_grace_period: boolean;
  is_ptp_exempt: boolean;
  active_ptp_id: string | null;
  is_eligible_for_suspension: boolean;
  is_warning_eligible: boolean;
  unpaid_invoices: Array<{
    invoice_id: string;
    invoice_number: string;
    due_date: string;
    total_amount: string;
    paid_amount: string;
    outstanding_amount: string;
  }>;
}

export interface SuspensionDashboardMetrics {
  currently_suspended: number;
  eligible_for_suspension: number;
  in_grace_period: number;
  ptp_exempt: number;
  warning_eligible: number;
  auto_suspension_enabled: boolean;
  auto_restoration_enabled: boolean;
  policy: SuspensionPolicy;
}

export interface AutomatedRunResult {
  status: string;
  eligible_count: number;
  suspended_count: number;
  warnings_sent_count: number;
  errors_count: number;
  suspended_services: string[];
  warnings_sent: string[];
  errors: Array<{ service_id: string; error: string }>;
}
