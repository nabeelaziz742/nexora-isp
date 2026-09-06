import { apiClient, normalizeList, type ListResponse } from "@/services/api-client";
import { Account } from "@/services/accounting.service";

export type ExpenseRecord = {
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
  journal_entry: string | null;
  journal_entry_number: string;
  recorded_by_email: string | null;
  created_at: string;
};

export type CreateExpensePayload = {
  expense_account_id: string;
  payment_account_id: string;
  amount: number | string;
  date?: string;
  payee?: string;
  category?: string;
  reference?: string;
  description?: string;
};

export const expensesService = {
  async getExpenses(params?: { category?: string; search?: string }): Promise<ExpenseRecord[]> {
    const query = new URLSearchParams();
    if (params?.category) query.set("category", params.category);
    if (params?.search) query.set("search", params.search);
    const qs = query.toString();
    const res = await apiClient.get<ListResponse<ExpenseRecord>>(`/accounting/expenses/${qs ? `?${qs}` : ""}`);
    return normalizeList<ExpenseRecord>(res);
  },

  createExpense(payload: CreateExpensePayload): Promise<ExpenseRecord> {
    return apiClient.post<ExpenseRecord>("/accounting/expenses/", payload);
  },

  async getAccounts(): Promise<Account[]> {
    const res = await apiClient.get<ListResponse<Account>>("/accounting/accounts/");
    return normalizeList<Account>(res);
  },
};
