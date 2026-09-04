import { apiClient } from "@/services/api-client";
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
  getExpenses(params?: { category?: string; search?: string }): Promise<ExpenseRecord[]> {
    const query = new URLSearchParams();
    if (params?.category) query.set("category", params.category);
    if (params?.search) query.set("search", params.search);
    const qs = query.toString();
    return apiClient.get<ExpenseRecord[]>(`/accounting/expenses/${qs ? `?${qs}` : ""}`);
  },

  createExpense(payload: CreateExpensePayload): Promise<ExpenseRecord> {
    return apiClient.post<ExpenseRecord>("/accounting/expenses/", payload);
  },

  getAccounts(): Promise<Account[]> {
    return apiClient.get<Account[]>("/accounting/accounts/");
  },
};
