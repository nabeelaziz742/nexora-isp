import { apiRequest } from "@/services/api-client";

import type {
  MarkNotificationFailedPayload,
  MarkNotificationSentPayload,
  NotificationJob,
  NotificationJobFilters,
  NotificationSummary,
  QueueNotificationPayload,
  StartNotificationProcessingPayload,
} from "@/types/notifications";

function buildQueryString(
  filters: NotificationJobFilters = {},
): string {
  const params = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (value) {
      params.set(key, value);
    }
  });

  const query = params.toString();

  return query ? `?${query}` : "";
}

export const notificationService = {
  getJobs(
    filters: NotificationJobFilters = {},
  ): Promise<NotificationJob[]> {
    return apiRequest<NotificationJob[]>(
      `/notifications/jobs/${buildQueryString(filters)}`,
    );
  },

  getJob(
    notificationJobId: string,
  ): Promise<NotificationJob> {
    return apiRequest<NotificationJob>(
      `/notifications/jobs/${notificationJobId}/`,
    );
  },

  getSummary(): Promise<NotificationSummary> {
    return apiRequest<NotificationSummary>(
      "/notifications/summary/",
    );
  },

  queueNotification(
    payload: QueueNotificationPayload,
  ): Promise<NotificationJob> {
    return apiRequest<NotificationJob>(
      "/notifications/jobs/",
      {
        method: "POST",
        body: payload,
      },
    );
  },

  startProcessing(
    notificationJobId: string,
    payload: StartNotificationProcessingPayload,
  ): Promise<NotificationJob> {
    return apiRequest<NotificationJob>(
      `/notifications/jobs/${notificationJobId}/start-processing/`,
      {
        method: "POST",
        body: payload,
      },
    );
  },

  markSent(
    notificationJobId: string,
    payload: MarkNotificationSentPayload,
  ): Promise<NotificationJob> {
    return apiRequest<NotificationJob>(
      `/notifications/jobs/${notificationJobId}/mark-sent/`,
      {
        method: "POST",
        body: payload,
      },
    );
  },

  markFailed(
    notificationJobId: string,
    payload: MarkNotificationFailedPayload,
  ): Promise<NotificationJob> {
    return apiRequest<NotificationJob>(
      `/notifications/jobs/${notificationJobId}/mark-failed/`,
      {
        method: "POST",
        body: payload,
      },
    );
  },
};