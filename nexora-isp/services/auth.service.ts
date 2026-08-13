import { apiRequest } from "@/services/api-client";
import { setAuthTokens } from "@/services/auth-storage";

export interface AuthUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
}

export interface AuthOrganization {
  id: string;
  name: string;
  code: string;
}

export interface LoginRequest {
  organization_code: string;
  email: string;
  password: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  role: string;
  user: AuthUser;
  organization: AuthOrganization;
}

export interface CurrentSessionResponse {
  user: AuthUser;
  organization: AuthOrganization;
  role: string;
}

function storeSession(
  session: CurrentSessionResponse,
): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(
    "nexora_user",
    JSON.stringify(session.user),
  );

  window.localStorage.setItem(
    "nexora_organization",
    JSON.stringify(session.organization),
  );

  window.localStorage.setItem(
    "nexora_role",
    session.role,
  );
}

export async function login(
  data: LoginRequest,
): Promise<LoginResponse> {
  const response = await apiRequest<LoginResponse>(
    "/auth/login/",
    {
      method: "POST",
      body: data,
      skipAuth: true,
      retryOnUnauthorized: false,
    },
  );

  setAuthTokens(
    response.access,
    response.refresh,
  );

  storeSession(response);

  return response;
}

export async function getCurrentSession(): Promise<CurrentSessionResponse> {
  const response =
    await apiRequest<CurrentSessionResponse>(
      "/auth/me/",
      {
        method: "GET",
      },
    );

  storeSession(response);

  return response;
}