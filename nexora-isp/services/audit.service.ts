import { apiRequest } from "@/services/api-client";

export interface AuditLog {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  actor_id: string | null;
  actor_name: string;
  actor_email: string;
  metadata: Record<string, any>;
  created_at: string;
}

export interface GetAuditLogsParams {
  action?: string;
  resource_type?: string;
  actor_id?: string;
  start_date?: string;
  end_date?: string;
  search?: string;
}

export const auditService = {
  getAuditLogs(params: GetAuditLogsParams = {}): Promise<AuditLog[]> {
    const searchParams = new URLSearchParams();
    if (params.action?.trim()) searchParams.set("action", params.action.trim());
    if (params.resource_type?.trim()) searchParams.set("resource_type", params.resource_type.trim());
    if (params.actor_id?.trim()) searchParams.set("actor_id", params.actor_id.trim());
    if (params.start_date?.trim()) searchParams.set("start_date", params.start_date.trim());
    if (params.end_date?.trim()) searchParams.set("end_date", params.end_date.trim());
    if (params.search?.trim()) searchParams.set("search", params.search.trim());

    const qs = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return apiRequest<AuditLog[]>(`/tenant/audit-logs/${qs}`);
  },
};
