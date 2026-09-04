import { apiClient } from "./api-client";

export interface Account {
  id: string;
  code: string;
  name: string;
  category: "ASSET" | "LIABILITY" | "EQUITY" | "REVENUE" | "EXPENSE";
  account_type: string;
  parent?: string | null;
  parent_code?: string;
  parent_name?: string;
  description: string;
  is_system: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface JournalLine {
  id?: string;
  account: string;
  account_code?: string;
  account_name?: string;
  account_category?: string;
  description: string;
  debit: string | number;
  credit: string | number;
  line_order?: number;
}

export interface JournalEntry {
  id: string;
  entry_number: string;
  date: string;
  narration: string;
  reference_type: string;
  reference_id: string;
  status: "DRAFT" | "POSTED" | "REVERSED";
  period?: string | null;
  period_name?: string;
  created_by?: string;
  created_by_name?: string;
  posted_by?: string;
  posted_by_name?: string;
  posted_at?: string;
  reversed_entry?: string | null;
  reversed_entry_number?: string;
  total_debit: string;
  total_credit: string;
  is_balanced: boolean;
  lines: JournalLine[];
  created_at: string;
  updated_at: string;
}

export interface GeneralLedgerEntry {
  id: string;
  journal_entry_id: string;
  entry_number: string;
  date: string;
  narration: string;
  description: string;
  reference_type: string;
  reference_id: string;
  debit: string;
  credit: string;
  running_balance: string;
}

export interface GeneralLedgerStatement {
  account: {
    id: string;
    code: string;
    name: string;
    category: string;
    account_type: string;
    normal_side: "DEBIT" | "CREDIT";
  };
  currency: string;
  start_date: string | null;
  end_date: string | null;
  opening_balance: string;
  total_debits: string;
  total_credits: string;
  net_change: string;
  closing_balance: string;
  entries: GeneralLedgerEntry[];
}

export interface TrialBalanceRow {
  account_id: string;
  code: string;
  name: string;
  category: string;
  account_type: string;
  debit_total: string;
  credit_total: string;
  net_balance: string;
  normal_side: "DEBIT" | "CREDIT";
}

export interface TrialBalanceStatement {
  organization_code: string;
  currency: string;
  as_of_date: string | null;
  start_date: string | null;
  end_date: string | null;
  total_debits: string;
  total_credits: string;
  is_balanced: boolean;
  accounts: TrialBalanceRow[];
}

export interface ExpenseRecord {
  id: string;
  expense_number: string;
  expense_account: string;
  expense_account_code: string;
  expense_account_name: string;
  payment_account: string;
  payment_account_code: string;
  payment_account_name: string;
  amount: string;
  date: string;
  payee: string;
  category: string;
  reference: string;
  description: string;
  receipt_file?: string | null;
  journal_entry?: string | null;
  journal_entry_number?: string;
  recorded_by?: string;
  recorded_by_name?: string;
  created_at: string;
  updated_at: string;
}

export interface DirectIncomeRecord {
  id: string;
  income_number: string;
  income_account: string;
  income_account_code: string;
  income_account_name: string;
  deposit_account: string;
  deposit_account_code: string;
  deposit_account_name: string;
  amount: string;
  date: string;
  received_from: string;
  reference: string;
  description: string;
  journal_entry?: string | null;
  journal_entry_number?: string;
  recorded_by?: string;
  recorded_by_name?: string;
  created_at: string;
  updated_at: string;
}

export interface FundTransferRecord {
  id: string;
  transfer_number: string;
  from_account: string;
  from_account_code: string;
  from_account_name: string;
  to_account: string;
  to_account_code: string;
  to_account_name: string;
  amount: string;
  date: string;
  reference: string;
  description: string;
  journal_entry?: string | null;
  journal_entry_number?: string;
  transferred_by?: string;
  transferred_by_name?: string;
  created_at: string;
  updated_at: string;
}

export interface DealerSettlementRecord {
  id: string;
  settlement_number: string;
  dealer: string;
  dealer_code: string;
  dealer_name: string;
  payment_account: string;
  payment_account_code: string;
  payment_account_name: string;
  amount: string;
  period_start: string;
  period_end: string;
  settlement_date: string;
  notes: string;
  journal_entry?: string | null;
  journal_entry_number?: string;
  created_by?: string;
  created_by_name?: string;
  created_at: string;
  updated_at: string;
}

export interface FinancialPeriodRecord {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  is_closed: boolean;
  closed_at?: string | null;
  closed_by?: string | null;
  closed_by_name?: string;
  created_at: string;
  updated_at: string;
}

export interface AccountingOverview {
  currency: string;
  metrics: {
    cash_bank_balance: string;
    receivables_balance: string;
    mtd_revenue: string;
    mtd_expenses: string;
    net_margin: string;
    total_accounts_count: number;
    total_journal_entries_count: number;
  };
  cash_bank_accounts: Array<{
    id: string;
    code: string;
    name: string;
    account_type: string;
    balance: string;
  }>;
  recent_journals: JournalEntry[];
}

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

export const accountingService = {
  async getOverview(): Promise<AccountingOverview> {
    return apiClient.get<AccountingOverview>("/accounting/overview/");
  },

  async getAccounts(params?: { category?: string; search?: string; is_active?: boolean }): Promise<Account[]> {
    return apiClient.get<Account[]>(`/accounting/accounts/${buildQuery(params)}`);
  },

  async createAccount(data: Partial<Account>): Promise<Account> {
    return apiClient.post<Account>("/accounting/accounts/", data);
  },

  async updateAccount(id: string, data: Partial<Account>): Promise<Account> {
    return apiClient.put<Account>(`/accounting/accounts/${id}/`, data);
  },

  async initDefaultCOA(): Promise<{ message: string; accounts_count: number }> {
    return apiClient.post<{ message: string; accounts_count: number }>("/accounting/accounts/init-default/");
  },

  async getJournalEntries(params?: { reference_type?: string; status?: string; start_date?: string; end_date?: string; search?: string }): Promise<JournalEntry[]> {
    return apiClient.get<JournalEntry[]>(`/accounting/journals/${buildQuery(params)}`);
  },

  async getJournalEntry(id: string): Promise<JournalEntry> {
    return apiClient.get<JournalEntry>(`/accounting/journals/${id}/`);
  },

  async createJournalEntry(data: {
    date: string;
    narration: string;
    lines: Array<{ account_id: string; debit: number | string; credit: number | string; description?: string }>;
    reference_type?: string;
    reference_id?: string;
  }): Promise<JournalEntry> {
    return apiClient.post<JournalEntry>("/accounting/journals/", data);
  },

  async reverseJournalEntry(id: string, reason: string): Promise<JournalEntry> {
    return apiClient.post<JournalEntry>(`/accounting/journals/${id}/reverse/`, { reason });
  },

  async getGeneralLedger(params: { account_id?: string; account_code?: string; start_date?: string; end_date?: string }): Promise<GeneralLedgerStatement> {
    return apiClient.get<GeneralLedgerStatement>(`/accounting/ledger/${buildQuery(params)}`);
  },

  async getTrialBalance(params?: { as_of_date?: string; start_date?: string; end_date?: string }): Promise<TrialBalanceStatement> {
    return apiClient.get<TrialBalanceStatement>(`/accounting/trial-balance/${buildQuery(params)}`);
  },

  async getExpenses(params?: { category?: string; search?: string }): Promise<ExpenseRecord[]> {
    return apiClient.get<ExpenseRecord[]>(`/accounting/expenses/${buildQuery(params)}`);
  },

  async createExpense(data: {
    expense_account_id: string;
    payment_account_id: string;
    amount: number | string;
    date: string;
    payee?: string;
    category?: string;
    reference?: string;
    description?: string;
  }): Promise<ExpenseRecord> {
    return apiClient.post<ExpenseRecord>("/accounting/expenses/", data);
  },

  async getDirectIncome(params?: { search?: string }): Promise<DirectIncomeRecord[]> {
    return apiClient.get<DirectIncomeRecord[]>(`/accounting/income/${buildQuery(params)}`);
  },

  async createDirectIncome(data: {
    income_account_id: string;
    deposit_account_id: string;
    amount: number | string;
    date: string;
    received_from?: string;
    reference?: string;
    description?: string;
  }): Promise<DirectIncomeRecord> {
    return apiClient.post<DirectIncomeRecord>("/accounting/income/", data);
  },

  async getFundTransfers(): Promise<FundTransferRecord[]> {
    return apiClient.get<FundTransferRecord[]>("/accounting/transfers/");
  },

  async createFundTransfer(data: {
    from_account_id: string;
    to_account_id: string;
    amount: number | string;
    date: string;
    reference?: string;
    description?: string;
  }): Promise<FundTransferRecord> {
    return apiClient.post<FundTransferRecord>("/accounting/transfers/", data);
  },

  async getDealerSettlements(params?: { dealer_id?: string }): Promise<DealerSettlementRecord[]> {
    return apiClient.get<DealerSettlementRecord[]>(`/accounting/dealer-settlements/${buildQuery(params)}`);
  },

  async createDealerSettlement(data: {
    dealer_id: string;
    payment_account_id: string;
    amount: number | string;
    period_start: string;
    period_end: string;
    settlement_date: string;
    notes?: string;
  }): Promise<DealerSettlementRecord> {
    return apiClient.post<DealerSettlementRecord>("/accounting/dealer-settlements/", data);
  },

  async createDealerAccrual(data: {
    dealer_id: string;
    period_start: string;
    period_end: string;
    commission_amount: number | string;
    notes?: string;
  }): Promise<JournalEntry> {
    return apiClient.post<JournalEntry>("/accounting/dealer-accruals/", data);
  },

  async getFinancialPeriods(): Promise<FinancialPeriodRecord[]> {
    return apiClient.get<FinancialPeriodRecord[]>("/accounting/periods/");
  },

  async closeFinancialPeriod(id: string): Promise<FinancialPeriodRecord> {
    return apiClient.post<FinancialPeriodRecord>(`/accounting/periods/${id}/close/`);
  },

  async reopenFinancialPeriod(id: string, reason: string): Promise<FinancialPeriodRecord> {
    return apiClient.post<FinancialPeriodRecord>(`/accounting/periods/${id}/reopen/`, { reason });
  },
};
