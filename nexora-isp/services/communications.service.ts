import { apiClient } from "@/services/api-client";

export interface CommunicationDashboard {
  messages_today: number;
  delivered: number;
  failed: number;
  pending: number;
  scheduled_jobs: number;
  templates: number;
  success_rate: number;
  providers: {
    whatsapp: boolean;
    sms: boolean;
    email: boolean;
  };
}

export interface CommunicationProvider {
  id: string;
  name: string;
  provider_type: "WHATSAPP" | "SMS" | "EMAIL";
  status: string;
  is_default: boolean;
  is_connected: boolean;
  created_at: string;
  updated_at: string;
}

export interface BroadcastChannel {
  id: string;
  name: string;
  provider_type: "WHATSAPP" | "SMS" | "EMAIL";
  is_connected: boolean;
}

export interface BroadcastAudienceFilter {
  value: string;
  label: string;
}

export interface BroadcastTemplate {
  id: string;
  name: string;
}

export interface BroadcastPreview {
  preview: string;
}

export interface BroadcastOptions {
  providers: BroadcastChannel[];
  templates: BroadcastTemplate[];
  audience: BroadcastAudienceFilter[];
}

export interface BroadcastPayload {
  provider_id: string;
  template_id: string;
  audience: string;
  title: string;
  message: string;
  schedule_at?: string | null;
  area_id?: string;
  package_id?: string;
  customer_ids?: string[];
}

export const communicationsService = {
  getDashboard() {
    return apiClient.get<CommunicationDashboard>(
      "/communications/dashboard/",
    );
  },

  getLogs() {
    return apiClient.get(
      "/communications/logs/",
    );
  },

  retryLog(id: string) {
    return apiClient.post(
      `/communications/logs/${id}/retry/`,
    );
  },

  getSchedules() {
    return apiClient.get(
      "/communications/schedules/",
    );
  },

  getProviders() {
    return apiClient.get<CommunicationProvider[]>(
      "/communications/providers/",
    );
  },

  getProviderSettings() {
    return apiClient.get(
      "/communications/providers/settings/",
    );
  },

  updateProviderSettings(
    id: string,
    data: unknown,
  ) {
    return apiClient.patch(
      `/communications/providers/${id}/settings/`,
      data,
    );
  },

  testProviderConnection(id: string) {
    return apiClient.post(
      `/communications/providers/${id}/test_connection/`,
    );
  },

  toggleProviderConnection(id: string) {
    return apiClient.post(
      `/communications/providers/${id}/toggle_connection/`,
    );
  },

  setDefaultProvider(id: string) {
    return apiClient.post(
      `/communications/providers/${id}/set_default/`,
    );
  },

  getBroadcastOptions() {
    return apiClient.get<BroadcastOptions>(
      "/communications/broadcast/options/",
    );
  },

  sendBroadcast(
    data: BroadcastPayload,
  ) {
    return apiClient.post(
      "/communications/broadcast/",
      data,
    );
  },

  createBroadcast(
    data: BroadcastPayload,
  ) {
    return apiClient.post(
      "/communications/broadcast/",
      data,
    );
  },

  getBroadcastPreview(
    payload: {
      title: string;
      message: string;
    },
  ) {
    return Promise.resolve<BroadcastPreview>({
      preview: payload.message,
    });
  },

  /* -------------------------------------------------------------------------- */
  /* Templates */
  /* -------------------------------------------------------------------------- */

  getTemplates(
  params?: {
    search?: string;
    status?: string;
    provider?: string;
    ordering?: string;
  },
) {
  const query = new URLSearchParams();

  if (params?.search) query.append("search", params.search);
  if (params?.status) query.append("status", params.status);
  if (params?.provider) query.append("provider", params.provider);
  if (params?.ordering) query.append("ordering", params.ordering);

  const path =
    query.toString().length > 0
      ? `/communications/templates/?${query.toString()}`
      : "/communications/templates/";

  return apiClient.get<CommunicationTemplate[]>(path);
},

  getTemplate(id: string) {
    return apiClient.get<CommunicationTemplate>(
      `/communications/templates/${id}/`,
    );
  },

  createTemplate(
    data: Partial<CommunicationTemplate>,
  ) {
    return apiClient.post(
      "/communications/templates/",
      data,
    );
  },

  updateTemplate(
    id: string,
    data: Partial<CommunicationTemplate>,
  ) {
    return apiClient.patch(
      `/communications/templates/${id}/`,
      data,
    );
  },

  deleteTemplate(id: string) {
    return apiClient.delete(
      `/communications/templates/${id}/`,
    );
  },

  duplicateTemplate(id: string) {
    return apiClient.post(
      `/communications/templates/${id}/duplicate/`,
    );
  },

  enableTemplate(id: string) {
    return apiClient.post(
      `/communications/templates/${id}/enable/`,
    );
  },

  disableTemplate(id: string) {
    return apiClient.post(
      `/communications/templates/${id}/disable/`,
    );
  },

  previewTemplate(
    id: string,
    variables: Record<string, string>,
  ) {
    return apiClient.post<TemplatePreviewResponse>(
      `/communications/templates/${id}/preview/`,
      {
        variables,
      },
    );
  },

  validateTemplate(id: string) {
    return apiClient.post<TemplateValidationResponse>(
      `/communications/templates/${id}/validate/`,
    );
  },

  /* -------------------------------------------------------------------------- */
  /* Automations */
  /* -------------------------------------------------------------------------- */

  getAutomations(
    params?: {
      search?: string;
      trigger?: string;
      enabled?: boolean;
      ordering?: string;
    },
  ) {
    const query = new URLSearchParams();

    if (params?.search)
      query.append("search", params.search);

    if (params?.trigger)
      query.append("trigger", params.trigger);

    if (params?.enabled !== undefined)
      query.append(
        "enabled",
        String(params.enabled),
      );

    if (params?.ordering)
      query.append(
        "ordering",
        params.ordering,
      );

    const path =
      query.toString().length > 0
        ? `/communications/automations/?${query.toString()}`
        : "/communications/automations/";

    return apiClient.get<CommunicationAutomation[]>(path);
  },

  getAutomation(id: string) {
    return apiClient.get<CommunicationAutomation>(
      `/communications/automations/${id}/`,
    );
  },

  createAutomation(
    data: Partial<CommunicationAutomation>,
  ) {
    return apiClient.post(
      "/communications/automations/",
      data,
    );
  },

  updateAutomation(
    id: string,
    data: Partial<CommunicationAutomation>,
  ) {
    return apiClient.patch(
      `/communications/automations/${id}/`,
      data,
    );
  },

  deleteAutomation(id: string) {
    return apiClient.delete(
      `/communications/automations/${id}/`,
    );
  },

  enableAutomation(id: string) {
    return apiClient.post(
      `/communications/automations/${id}/enable/`,
    );
  },

  disableAutomation(id: string) {
    return apiClient.post(
      `/communications/automations/${id}/disable/`,
    );
  },

  executeAutomation(
    id: string,
    customer_id: string,
  ) {
    return apiClient.post(
      `/communications/automations/${id}/execute-now/`,
      {
        customer_id,
      },
    );
  },
};

/* -------------------------------------------------------------------------- */
/* Named exports for Broadcast Wizard (page.tsx imports these directly)        */
/* -------------------------------------------------------------------------- */

export const getBroadcastOptions =
  communicationsService.getBroadcastOptions.bind(
    communicationsService,
  );

export const createBroadcast =
  communicationsService.createBroadcast.bind(
    communicationsService,
  );

export const sendBroadcast =
  communicationsService.sendBroadcast.bind(
    communicationsService,
  );

export const getBroadcastPreview =
  communicationsService.getBroadcastPreview.bind(
    communicationsService,
  );

export const retryLog =
  communicationsService.retryLog.bind(
    communicationsService,
  );

/* -------------------------------------------------------------------------- */
/* Named exports for Templates                                                 */
/* -------------------------------------------------------------------------- */

export const getTemplates =
  communicationsService.getTemplates.bind(
    communicationsService,
  );

export const getTemplate =
  communicationsService.getTemplate.bind(
    communicationsService,
  );

export const createTemplate =
  communicationsService.createTemplate.bind(
    communicationsService,
  );

export const updateTemplate =
  communicationsService.updateTemplate.bind(
    communicationsService,
  );

export const deleteTemplate =
  communicationsService.deleteTemplate.bind(
    communicationsService,
  );

export const duplicateTemplate =
  communicationsService.duplicateTemplate.bind(
    communicationsService,
  );

export const enableTemplate =
  communicationsService.enableTemplate.bind(
    communicationsService,
  );

export const disableTemplate =
  communicationsService.disableTemplate.bind(
    communicationsService,
  );

export const previewTemplate =
  communicationsService.previewTemplate.bind(
    communicationsService,
  );

export const validateTemplate =
  communicationsService.validateTemplate.bind(
    communicationsService,
  );

/* -------------------------------------------------------------------------- */
/* Named exports for Automations                                               */
/* -------------------------------------------------------------------------- */

export const getAutomations =
  communicationsService.getAutomations.bind(
    communicationsService,
  );

export const getAutomation =
  communicationsService.getAutomation.bind(
    communicationsService,
  );

export const createAutomation =
  communicationsService.createAutomation.bind(
    communicationsService,
  );

export const updateAutomation =
  communicationsService.updateAutomation.bind(
    communicationsService,
  );

export const deleteAutomation =
  communicationsService.deleteAutomation.bind(
    communicationsService,
  );

export const enableAutomation =
  communicationsService.enableAutomation.bind(
    communicationsService,
  );

export const disableAutomation =
  communicationsService.disableAutomation.bind(
    communicationsService,
  );

export const executeAutomation =
  communicationsService.executeAutomation.bind(
    communicationsService,
  );

export interface CommunicationTemplate {
  id: string;
  name: string;
  subject: string;
  body: string;
  variables: string[];
  status: "ACTIVE" | "DRAFT" | "ARCHIVED";
  communication_provider: string;
  communication_provider_name: string;
  communication_provider_type: "WHATSAPP" | "SMS" | "EMAIL";
  created_at: string;
  updated_at: string;
}

export interface TemplatePreviewResponse {
  subject: string;
  body: string;
}

export interface TemplateValidationResponse {
  valid: boolean;
  variables: string[];
  count: number;
}

export interface CommunicationAutomation {
  id: string;
  name: string;
  description: string;
  trigger: string;

  template: string;
  template_name: string;
  provider_name: string;

  execution_order: number;
  delay_minutes: number;
  max_retry_attempts: number;

  is_enabled: boolean;

  last_executed_at?: string | null;
  last_execution_status?: string | null;

  created_at: string;
  updated_at: string;
}