import { apiRequest } from "@/services/api-client";

export type PaymentSettings = {
  id: string;
  bank_name: string;
  account_title: string;
  account_number: string;
  iban: string;
  amount: string;
  instructions: string;
  is_active: boolean;
};

export type Registration = {
  id: string;
  company_name: string;
  organization_code: string;
  owner_email: string;
  owner_name: string;
  amount_due: string;
  status: "PENDING_PAYMENT" | "PENDING_VERIFICATION" | "ACTIVE" | "REJECTED";
  receipt_url: string | null;
  rejection_reason: string;
  submitted_at: string | null;
  verified_at: string | null;
  created_at: string;
};

export type RegistrationCreateResponse = {
  registration_id: string;
  access_token: string;
  status: Registration["status"];
  organization_code: string;
  amount_due: string;
  payment: PaymentSettings;
};

export async function registerISP(payload: {
  company_name: string;
  city: string;
  first_name: string;
  last_name: string;
  email: string;
  password: string;
}): Promise<RegistrationCreateResponse> {
  return apiRequest<RegistrationCreateResponse>("/onboarding/register/", {
    method: "POST",
    body: payload,
    skipAuth: true,
  });
}

export async function getRegistration(accessToken: string): Promise<Registration> {
  return apiRequest<Registration>(`/onboarding/registration/${accessToken}/`, {
    method: "GET",
    skipAuth: true,
  });
}

export async function uploadRegistrationReceipt(
  accessToken: string,
  file: File,
): Promise<{ status: Registration["status"] }> {
  const form = new FormData();
  form.append("receipt", file);

  return apiRequest<{ status: Registration["status"] }>(
    `/onboarding/registration/${accessToken}/receipt/`,
    {
      method: "POST",
      body: form,
      skipAuth: true,
    },
  );
}

export async function superAdminLogin(email: string, password: string) {
  return apiRequest<{ access: string; refresh: string; user: { id: string; email: string; first_name: string; last_name: string } }>(
    "/onboarding/superadmin/login/",
    {
      method: "POST",
      body: { email, password },
      skipAuth: true,
    },
  );
}

function adminHeaders(token: string) {
  return {
    Authorization: `Bearer ${token}`,
  };
}

export async function getAdminRegistrations(token: string, status?: Registration["status"]) {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiRequest<Registration[]>(`/onboarding/superadmin/registrations/${query}`, {
    method: "GET",
    headers: adminHeaders(token),
    skipAuth: true,
  });
}

export async function approveRegistration(token: string, id: string) {
  return apiRequest<Registration>(`/onboarding/superadmin/registrations/${id}/approve/`, {
    method: "POST",
    headers: adminHeaders(token),
    skipAuth: true,
  });
}

export async function rejectRegistration(token: string, id: string, reason: string) {
  return apiRequest<Registration>(`/onboarding/superadmin/registrations/${id}/reject/`, {
    method: "POST",
    headers: adminHeaders(token),
    body: { reason },
    skipAuth: true,
  });
}

export async function getPaymentSettings(token: string) {
  return apiRequest<PaymentSettings | null>("/onboarding/superadmin/payment-settings/", {
    method: "GET",
    headers: adminHeaders(token),
    skipAuth: true,
  });
}

export async function savePaymentSettings(token: string, payload: Omit<PaymentSettings, "id">) {
  return apiRequest<PaymentSettings>("/onboarding/superadmin/payment-settings/", {
    method: "PUT",
    headers: adminHeaders(token),
    body: payload,
    skipAuth: true,
  });
}
