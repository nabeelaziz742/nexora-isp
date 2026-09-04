import { apiClient } from "./api-client";

function buildQuery(params?: Record<string, unknown>): string {
  if (!params) return "";
  const searchParams = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") {
      searchParams.append(k, String(v));
    }
  }
  const str = searchParams.toString();
  return str ? `?${str}` : "";
}

export interface CustomerMasterRow {
  service_id: string;
  service_number: string;
  customer_number: string;
  customer_name: string;
  phone: string;
  address: string;
  area: string;
  city: string;
  package_name: string;
  speed_mbps: string;
  monthly_price: string;
  status: string;
  dealer_name: string;
  ip_address: string;
  node_name: string;
  created_at: string;
}

export interface CustomerMasterResponse {
  summary: {
    total_subscribers: number;
    active_count: number;
    suspended_count: number;
  };
  pagination: {
    page: number;
    page_size: number;
    total_records: number;
    total_pages: number;
  };
  records: CustomerMasterRow[];
}

export interface CustomerGrowthChurnResponse {
  intervals: Array<{
    period: string;
    new_activations: number;
    deactivations: number;
    net_growth: number;
    churn_rate_percent: number;
    active_subscribers_end: number;
  }>;
  total_new: number;
  total_churned: number;
  net_overall_growth: number;
}

export interface AreaRevenueDensityRow {
  city_name: string;
  area_name: string;
  active_subscribers: number;
  invoiced_amount: string;
  collected_amount: string;
  outstanding_amount: string;
  collection_rate_percent: number;
}

export interface CollectionRow {
  id: string;
  payment_number: string;
  paid_at: string;
  customer_number: string;
  customer_name: string;
  service_number: string;
  package_name: string;
  payment_method: string;
  amount: string;
  reference: string;
  received_by_name: string;
}

export interface CustomerCollectionsResponse {
  summary: {
    total_collected: string;
    payment_count: number;
    method_breakdown: Array<{
      method: string;
      total: string;
      count: number;
    }>;
  };
  pagination: {
    page: number;
    page_size: number;
    total_records: number;
    total_pages: number;
  };
  records: CollectionRow[];
}

export interface DefaulterAgingRow {
  invoice_id: string;
  invoice_number: string;
  due_date: string;
  days_overdue: number;
  aging_bucket: string;
  customer_id: string;
  customer_number: string;
  customer_name: string;
  phone: string;
  area: string;
  service_number: string;
  package_name: string;
  dealer_name: string;
  total_invoiced: string;
  paid_amount: string;
  outstanding_amount: string;
}

export interface DefaultersAgingResponse {
  summary: {
    total_exposure: string;
    total_defaulters_count: number;
    aging_buckets: {
      "0-30": string;
      "31-60": string;
      "61-90": string;
      "90+": string;
    };
  };
  pagination: {
    page: number;
    page_size: number;
    total_records: number;
    total_pages: number;
  };
  records: DefaulterAgingRow[];
}

export interface CashierShiftResponse {
  cashier_name: string;
  shift_date: string;
  total_intake: string;
  transaction_count: number;
  method_breakdown: Record<string, string>;
  transactions: Array<{
    payment_number: string;
    time: string;
    customer: string;
    service_number: string;
    amount: string;
    method: string;
    reference: string;
  }>;
}

export interface InvoiceRegisterRow {
  id: string;
  invoice_number: string;
  issue_date: string;
  due_date: string;
  period: string;
  customer_number: string;
  customer_name: string;
  service_number: string;
  package_name: string;
  total_amount: string;
  paid_amount: string;
  outstanding_amount: string;
  status: string;
}

export interface InvoiceRegisterResponse {
  summary: {
    total_invoices_count: number;
    total_billed: string;
  };
  pagination: {
    page: number;
    page_size: number;
    total_records: number;
    total_pages: number;
  };
  records: InvoiceRegisterRow[];
}

export interface PromiseToPayResponse {
  summary: {
    total_promises: number;
    fulfilled_count: number;
    broken_count: number;
    active_count: number;
    fulfillment_rate_percent: number;
    total_promised_amount: string;
  };
  pagination: {
    page: number;
    page_size: number;
    total_records: number;
    total_pages: number;
  };
  records: Array<{
    id: string;
    promise_number: string;
    customer_name: string;
    service_number: string;
    promised_amount: string;
    outstanding_amount: string;
    promise_date: string;
    deadline: string;
    status: string;
    created_by: string;
    completed_at: string;
  }>;
}

export interface RecoveryOfficerScorecardRow {
  officer_id: string;
  officer_name: string;
  total_allocations: number;
  completed_allocations: number;
  in_progress_count: number;
  allocated_amount: string;
  recovered_amount: string;
  recovery_rate_percent: number;
}

export interface Dealer360Row {
  dealer_id: string;
  dealer_code: string;
  dealer_name: string;
  area_name: string;
  commission_type: string;
  commission_rate: string;
  total_subscribers: number;
  active_subscribers: number;
  invoiced_amount: string;
  collected_amount: string;
  commission_accrued: string;
  commission_settled: string;
  commission_outstanding: string;
  net_isp_margin: string;
}

export interface ProfitAndLossResponse {
  period: {
    start_date: string;
    end_date: string;
  };
  currency: string;
  revenue_statement: {
    accounts: Array<{ code: string; name: string; amount: string }>;
    total_revenue: string;
  };
  expense_statement: {
    accounts: Array<{ code: string; name: string; amount: string }>;
    total_expenses: string;
  };
  net_income: {
    net_profit_amount: string;
    profit_margin_percent: number;
    is_profitable: boolean;
  };
}

export interface BalanceSheetResponse {
  as_of_date: string;
  currency: string;
  assets: {
    accounts: Array<{ code: string; name: string; amount: string }>;
    total_assets: string;
  };
  liabilities: {
    accounts: Array<{ code: string; name: string; amount: string }>;
    total_liabilities: string;
  };
  equity: {
    accounts: Array<{ code: string; name: string; amount: string }>;
    retained_earnings: string;
    total_equity: string;
  };
  total_liabilities_and_equity: string;
  is_balanced: boolean;
}

export interface CashPositionResponse {
  period: {
    start_date: string;
    end_date: string;
  };
  total_liquid_funds: string;
  accounts: Array<{
    code: string;
    name: string;
    account_type: string;
    opening_balance: string;
    inflows: string;
    outflows: string;
    closing_balance: string;
  }>;
}

export interface ComplaintSlaResponse {
  summary: {
    total_complaints: number;
    resolved_count: number;
    breached_count: number;
    sla_breach_rate_percent: number;
    sla_compliance_rate_percent: number;
  };
  category_breakdown: Array<{
    category: string;
    total_count: number;
    breached_count: number;
    breach_rate_percent: number;
  }>;
}

export interface LeadConversionResponse {
  summary: {
    total_inquiries: number;
    contacted_count: number;
    feasible_count: number;
    converted_count: number;
    lost_count: number;
    conversion_rate_percent: number;
  };
  funnel_stages: Array<{
    stage: string;
    count: number;
    dropoff_percent: number;
  }>;
  source_breakdown: Array<{
    source: string;
    total: number;
    converted: number;
    conversion_rate: number;
  }>;
}

export interface DeviceCustodyResponse {
  summary: {
    total_devices: number;
    assigned_count: number;
    available_count: number;
    faulty_count: number;
  };
  pagination: {
    page: number;
    page_size: number;
    total_records: number;
    total_pages: number;
  };
  records: Array<{
    id: string;
    asset_tag: string;
    device_type: string;
    manufacturer: string;
    model_name: string;
    serial_number: string;
    mac_address: string;
    status: string;
    assigned_customer: string;
    assigned_service: string;
    assigned_date: string;
  }>;
}

export const reportingEngineService = {
  // Domain 1: Customers & Subscribers
  async getCustomerMaster(params?: {
    status?: string;
    area_id?: string;
    package_id?: string;
    dealer_id?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<CustomerMasterResponse> {
    return apiClient.get<CustomerMasterResponse>(`/reports/customers/master/${buildQuery(params)}`);
  },

  async getCustomerGrowthChurn(params?: { start_date?: string; end_date?: string }): Promise<CustomerGrowthChurnResponse> {
    return apiClient.get<CustomerGrowthChurnResponse>(`/reports/customers/growth-churn/${buildQuery(params)}`);
  },

  async getAreaRevenueDensity(): Promise<AreaRevenueDensityRow[]> {
    return apiClient.get<AreaRevenueDensityRow[]>("/reports/customers/area-density/");
  },

  // Domain 2: Collections & Cashier
  async getCollectionsRegister(params?: {
    start_date?: string;
    end_date?: string;
    collector_id?: string;
    payment_method?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<CustomerCollectionsResponse> {
    return apiClient.get<CustomerCollectionsResponse>(`/reports/collections/register/${buildQuery(params)}`);
  },

  async getDefaultersAging(params?: {
    aging_bucket?: string;
    area_id?: string;
    package_id?: string;
    dealer_id?: string;
    page?: number;
    page_size?: number;
    as_of_date?: string;
  }): Promise<DefaultersAgingResponse> {
    return apiClient.get<DefaultersAgingResponse>(`/reports/collections/defaulters-aging/${buildQuery(params)}`);
  },

  async getCashierShiftClose(params?: { collector_id?: string; shift_date?: string }): Promise<CashierShiftResponse> {
    return apiClient.get<CashierShiftResponse>(`/reports/collections/cashier-shift/${buildQuery(params)}`);
  },

  // Domain 3: Billing & Invoices
  async getInvoiceRegister(params?: {
    status?: string;
    start_date?: string;
    end_date?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<InvoiceRegisterResponse> {
    return apiClient.get<InvoiceRegisterResponse>(`/reports/billing/invoice-register/${buildQuery(params)}`);
  },

  // Domain 4: Recovery & Promises
  async getPromiseToPayReport(params?: {
    start_date?: string;
    end_date?: string;
    status?: string;
    staff_id?: string;
    page?: number;
    page_size?: number;
  }): Promise<PromiseToPayResponse> {
    return apiClient.get<PromiseToPayResponse>(`/reports/recovery/ptp-performance/${buildQuery(params)}`);
  },

  async getFieldRecoveryScorecard(params?: {
    start_date?: string;
    end_date?: string;
    staff_id?: string;
  }): Promise<RecoveryOfficerScorecardRow[]> {
    return apiClient.get<RecoveryOfficerScorecardRow[]>(`/reports/recovery/officer-scorecard/${buildQuery(params)}`);
  },

  // Domain 5: Dealer 360
  async getDealer360Performance(params?: {
    start_date?: string;
    end_date?: string;
    dealer_id?: string;
  }): Promise<Dealer360Row[]> {
    return apiClient.get<Dealer360Row[]>(`/reports/dealers/performance-360/${buildQuery(params)}`);
  },

  // Domain 6: Formal Financial Statements
  async getProfitAndLoss(params?: { start_date?: string; end_date?: string }): Promise<ProfitAndLossResponse> {
    return apiClient.get<ProfitAndLossResponse>(`/reports/financial/profit-and-loss/${buildQuery(params)}`);
  },

  async getBalanceSheet(params?: { as_of_date?: string }): Promise<BalanceSheetResponse> {
    return apiClient.get<BalanceSheetResponse>(`/reports/financial/balance-sheet/${buildQuery(params)}`);
  },

  async getCashPosition(params?: { start_date?: string; end_date?: string }): Promise<CashPositionResponse> {
    return apiClient.get<CashPositionResponse>(`/reports/financial/cash-position/${buildQuery(params)}`);
  },

  // Domain 7: Support & SLA
  async getComplaintSla(params?: {
    start_date?: string;
    end_date?: string;
    category?: string;
    priority?: string;
  }): Promise<ComplaintSlaResponse> {
    return apiClient.get<ComplaintSlaResponse>(`/reports/support/sla-mttr/${buildQuery(params)}`);
  },

  // Domain 8: Inquiries & Sales
  async getLeadConversionFunnel(params?: { start_date?: string; end_date?: string }): Promise<LeadConversionResponse> {
    return apiClient.get<LeadConversionResponse>(`/reports/inquiries/conversion-funnel/${buildQuery(params)}`);
  },

  // Domain 9: Inventory & Devices
  async getDeviceCustody(params?: {
    device_type?: string;
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<DeviceCustodyResponse> {
    return apiClient.get<DeviceCustodyResponse>(`/reports/inventory/device-custody/${buildQuery(params)}`);
  },
};
