import { apiClient } from "@/services/api-client";

import type {
  CommandCenterSummary,
} from "@/types/command-center";

export interface OperationalAlert {
  alert_type: string;
  severity: string;
  title: string;
  description: string;
  resource_type: string;
  resource_id: string;
  occurred_at: string;
  context: Record<string, unknown>;
}

export interface PriorityQueueItem {
  resource_id: string;
  status?: string;
  action?: string;
  priority?: string;
  severity?: string;
  work_order_type?: string;
  channel?: string;
  event_type?: string;
  asset_tag?: string;
  device_type?: string;
  queued_at: string;
}

export interface PriorityQueues {
  pending_provisioning: PriorityQueueItem[];
  critical_complaints: PriorityQueueItem[];
  critical_incidents: PriorityQueueItem[];
  critical_work_orders: PriorityQueueItem[];
  failed_notifications: PriorityQueueItem[];
  inventory_attention: PriorityQueueItem[];
}

export interface OperationalActivityActor {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
}

export interface OperationalActivity {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  actor: OperationalActivityActor | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface OperationsCopilotResponse {
  answer: string;
  generated_at: string;
  provider: string;
  model: string;
}

export const commandCenterService = {
  getSummary(): Promise<CommandCenterSummary> {
    return apiClient.get<CommandCenterSummary>(
      "/command-center/summary/",
    );
  },

  getAlerts(): Promise<OperationalAlert[]> {
    return apiClient.get<OperationalAlert[]>(
      "/command-center/alerts/",
    );
  },

  getPriorityQueues(): Promise<PriorityQueues> {
    return apiClient.get<PriorityQueues>(
      "/command-center/priority-queues/",
    );
  },

  getRecentActivity(): Promise<
    OperationalActivity[]
  > {
    return apiClient.get<OperationalActivity[]>(
      "/command-center/recent-activity/",
    );
  },

  askCopilot(
    question: string,
  ): Promise<OperationsCopilotResponse> {
    return apiClient.post<OperationsCopilotResponse>(
      "/command-center/copilot/",
      {
        question,
      },
    );
  },
};