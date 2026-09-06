import { ApiError, normalizeApiErrorMessage } from "@/services/api-error";

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1"
).replace(/\/$/, "");

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
  payment: PaymentSettings | null;
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
  const response = await fetch(`${API_BASE_URL}/onboarding/register/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new ApiError(
      normalizeApiErrorMessage(data, "Unable to create registration."),
      response.status,
      data,
    );
  }
  return data as RegistrationCreateResponse;
}

export async function getRegistration(
  accessToken: string,
): Promise<Registration> {
  const response = await fetch(
    `${API_BASE_URL}/onboarding/registration/${accessToken}/`,
  );
  const data = await response.json();
  if (!response.ok) {
    throw new ApiError(
      normalizeApiErrorMessage(data, "Unable to load registration."),
      response.status,
      data,
    );
  }
  return data as Registration;
}

export async function uploadRegistrationReceipt(
  accessToken: string,
  file: File,
): Promise<{ status: Registration["status"] }> {
  const form = new FormData();
  form.append("receipt", file);
  const response = await fetch(
    `${API_BASE_URL}/onboarding/registration/${accessToken}/receipt/`,
    {
      method: "POST",
      body: form,
    },
  );
  const data = await response.json();
  if (!response.ok) {
    throw new ApiError(
      normalizeApiErrorMessage(data, "Unable to upload receipt."),
      response.status,
      data,
    );
  }
  return data as { status: Registration["status"] };
}

export async function superAdminLogin(email: string, password: string) {
  const response = await fetch(`${API_BASE_URL}/onboarding/superadmin/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new ApiError(
      normalizeApiErrorMessage(data, "Invalid administrator credentials."),
      response.status,
      data,
    );
  }
  return data as {
    access: string;
    refresh: string;
    user: { id: string; email: string; first_name: string; last_name: string };
  };
}

let superAdminRefreshPromise: Promise<string | null> | null = null;

export async function refreshSuperAdminToken(): Promise<string | null> {
  if (superAdminRefreshPromise) return superAdminRefreshPromise;

  superAdminRefreshPromise = (async () => {
    if (typeof window === "undefined") return null;
    const refreshToken = localStorage.getItem("nexora_superadmin_refresh");
    if (!refreshToken) {
      localStorage.removeItem("nexora_superadmin_access");
      localStorage.removeItem("nexora_superadmin_refresh");
      return null;
    }

    try {
      const response = await fetch(
        `${API_BASE_URL}/onboarding/superadmin/refresh/`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh: refreshToken }),
        },
      );

      if (!response.ok) {
        localStorage.removeItem("nexora_superadmin_access");
        localStorage.removeItem("nexora_superadmin_refresh");
        return null;
      }

      const data = await response.json();
      if (data?.access) {
        localStorage.setItem("nexora_superadmin_access", data.access);
        if (data.refresh) {
          localStorage.setItem("nexora_superadmin_refresh", data.refresh);
        }
        return data.access as string;
      }

      localStorage.removeItem("nexora_superadmin_access");
      localStorage.removeItem("nexora_superadmin_refresh");
      return null;
    } catch {
      localStorage.removeItem("nexora_superadmin_access");
      localStorage.removeItem("nexora_superadmin_refresh");
      return null;
    }
  })();

  try {
    return await superAdminRefreshPromise;
  } finally {
    superAdminRefreshPromise = null;
  }
}

async function superAdminFetch<T>(
  path: string,
  options: RequestInit = {},
  currentToken?: string,
  isRetry = false,
): Promise<T> {
  const token =
    currentToken ||
    (typeof window !== "undefined"
      ? localStorage.getItem("nexora_superadmin_access")
      : null);

  const headers = new Headers(options.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (
    options.body &&
    !(options.body instanceof FormData) &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && !isRetry) {
    const newToken = await refreshSuperAdminToken();
    if (newToken) {
      return superAdminFetch<T>(path, options, newToken, true);
    }
    throw new ApiError("Session expired. Please sign in again.", 401);
  }

  const contentType = response.headers.get("content-type") ?? "";
  let data: unknown = null;
  if (contentType.includes("application/json")) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    const message = normalizeApiErrorMessage(
      data,
      `Request failed with status ${response.status}.`,
    );
    throw new ApiError(message, response.status, data);
  }

  return data as T;
}

export async function getAdminRegistrations(
  token?: string,
  status?: Registration["status"],
) {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return superAdminFetch<Registration[]>(
    `/onboarding/superadmin/registrations/${query}`,
    { method: "GET" },
    token,
  );
}

export async function approveRegistration(token: string, id: string) {
  return superAdminFetch<Registration>(
    `/onboarding/superadmin/registrations/${id}/approve/`,
    { method: "POST" },
    token,
  );
}

export async function rejectRegistration(
  token: string,
  id: string,
  reason: string,
) {
  return superAdminFetch<Registration>(
    `/onboarding/superadmin/registrations/${id}/reject/`,
    {
      method: "POST",
      body: JSON.stringify({ reason }),
    },
    token,
  );
}

export async function getPaymentSettings(token?: string) {
  return superAdminFetch<PaymentSettings | null>(
    "/onboarding/superadmin/payment-settings/",
    { method: "GET" },
    token,
  );
}

export async function savePaymentSettings(
  token: string,
  payload: Omit<PaymentSettings, "id">,
) {
  return superAdminFetch<PaymentSettings>(
    "/onboarding/superadmin/payment-settings/",
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function getReceiptObjectUrl(
  token?: string,
  id?: string,
): Promise<string> {
  if (!id) throw new Error("Registration ID is required.");
  let authToken =
    token ||
    (typeof window !== "undefined"
      ? localStorage.getItem("nexora_superadmin_access")
      : null);

  let response = await fetch(
    `${API_BASE_URL}/onboarding/superadmin/registrations/${id}/receipt/`,
    {
      headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
    },
  );

  if (response.status === 401) {
    authToken = await refreshSuperAdminToken();
    if (authToken) {
      response = await fetch(
        `${API_BASE_URL}/onboarding/superadmin/registrations/${id}/receipt/`,
        {
          headers: { Authorization: `Bearer ${authToken}` },
        },
      );
    }
  }

  if (!response.ok) throw new Error("Unable to load receipt.");
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}
