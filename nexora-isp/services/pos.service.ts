import { apiClient } from "@/services/api-client";
import { InventoryItem, PaginatedResult } from "@/services/inventory.service";

export type PosSalePaymentMethod =
  | "CASH"
  | "BANK_TRANSFER"
  | "CARD"
  | "MOBILE_WALLET";

export type PosSaleStatus = "COMPLETED" | "CANCELLED";

export type PosSaleItem = {
  id: string;
  item: string;
  item_name: string;
  item_code: string;
  quantity: string;
  unit_price: string;
  unit_cost: string;
  line_discount: string;
  line_total: string;
  device: string | null;
  device_asset_tag: string;
  created_at: string;
};

export type PosSale = {
  id: string;
  sale_number: string;
  customer: string | null;
  customer_name: string;
  customer_phone: string;
  walk_in_customer_name: string;
  walk_in_customer_phone: string;
  sale_date: string;
  subtotal_amount: string;
  discount_amount: string;
  tax_amount: string;
  total_amount: string;
  paid_amount: string;
  payment_method: PosSalePaymentMethod;
  payment_reference: string;
  status: PosSaleStatus;
  cancellation_reason: string;
  cancelled_at: string | null;
  cancelled_by: string | null;
  cancelled_by_name: string;
  journal_entry: string | null;
  journal_entry_number: string;
  sold_by: string | null;
  sold_by_name: string;
  notes: string;
  items: PosSaleItem[];
  created_at: string;
  updated_at: string;
};

export type CreatePosSaleItemPayload = {
  item_id: string;
  quantity: number | string;
  unit_price?: number | string;
  line_discount?: number | string;
  device_id?: string | null;
};

export type CreatePosSalePayload = {
  customer_id?: string | null;
  walk_in_customer_name?: string;
  walk_in_customer_phone?: string;
  sale_date?: string;
  items: CreatePosSaleItemPayload[];
  payment_method: PosSalePaymentMethod;
  payment_reference?: string;
  discount_amount?: number | string;
  tax_amount?: number | string;
  notes?: string;
};

export const posService = {
  getCatalog(params?: { category?: string; search?: string }): Promise<InventoryItem[]> {
    const query = new URLSearchParams();
    if (params?.category) query.set("category", params.category);
    if (params?.search) query.set("search", params.search);
    const qs = query.toString();
    return apiClient.get<InventoryItem[]>(`/pos/catalog/${qs ? `?${qs}` : ""}`);
  },

  getSales(params?: {
    customer_id?: string;
    status?: string;
    payment_method?: string;
    start_date?: string;
    end_date?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResult<PosSale>> {
    const query = new URLSearchParams();
    if (params?.customer_id) query.set("customer_id", params.customer_id);
    if (params?.status) query.set("status", params.status);
    if (params?.payment_method) query.set("payment_method", params.payment_method);
    if (params?.start_date) query.set("start_date", params.start_date);
    if (params?.end_date) query.set("end_date", params.end_date);
    if (params?.search) query.set("search", params.search);
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));

    const qs = query.toString();
    return apiClient.get<PaginatedResult<PosSale>>(`/pos/sales/${qs ? `?${qs}` : ""}`);
  },

  getSale(id: string): Promise<PosSale> {
    return apiClient.get<PosSale>(`/pos/sales/${id}/`);
  },

  createSale(payload: CreatePosSalePayload): Promise<PosSale> {
    return apiClient.post<PosSale>("/pos/sales/", payload);
  },

  cancelSale(id: string, cancellationReason: string): Promise<PosSale> {
    return apiClient.post<PosSale>(`/pos/sales/${id}/cancel/`, {
      cancellation_reason: cancellationReason,
    });
  },
};
