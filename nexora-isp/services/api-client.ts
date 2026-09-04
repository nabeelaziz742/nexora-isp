import {
  clearAuthTokens,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
} from "@/services/auth-storage";
import {
  ApiError,
  normalizeApiErrorMessage,
} from "@/services/api-error";

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://127.0.0.1:8000/api/v1"
).replace(/\/$/, "");

const TOKEN_REFRESH_PATH = "/auth/token/refresh/";

type ApiRequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  skipAuth?: boolean;
  retryOnUnauthorized?: boolean;
  timeoutMs?: number;
};

let refreshPromise: Promise<string | null> | null = null;

function buildUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}

async function parseResponseBody(response: Response): Promise<unknown> {
  if (response.status === 204) return null;

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    try {
      return await response.json();
    } catch {
      return null;
    }
  }

  try {
    const text = await response.text();
    return text || null;
  } catch {
    return null;
  }
}

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      clearAuthTokens();
      return null;
    }

    try {
      const response = await fetch(buildUrl(TOKEN_REFRESH_PATH), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh: refreshToken }),
      });

      const payload = await parseResponseBody(response);
      if (!response.ok) {
        clearAuthTokens();
        return null;
      }

      if (
        !payload ||
        typeof payload !== "object" ||
        !("access" in payload) ||
        typeof payload.access !== "string"
      ) {
        clearAuthTokens();
        return null;
      }

      setAccessToken(payload.access);
      return payload.access;
    } catch {
      clearAuthTokens();
      return null;
    }
  })();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const {
    body,
    headers,
    skipAuth = false,
    retryOnUnauthorized = true,
    timeoutMs = 30000,
    ...requestOptions
  } = options;

  const requestHeaders = new Headers(headers);

  if (body !== undefined && !(body instanceof FormData)) {
    requestHeaders.set("Content-Type", "application/json");
  }

  if (!skipAuth) {
    const accessToken = getAccessToken();
    if (accessToken) {
      requestHeaders.set("Authorization", `Bearer ${accessToken}`);
    }
  }

  // Timeout controller
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(buildUrl(path), {
      ...requestOptions,
      headers: requestHeaders,
      signal: controller.signal,
      body:
        body === undefined
          ? undefined
          : body instanceof FormData
            ? body
            : JSON.stringify(body),
    });
  } catch (networkError: unknown) {
    clearTimeout(timeoutId);
    if (networkError instanceof Error && networkError.name === "AbortError") {
      throw new ApiError(
        "Request timed out. The server took too long to respond.",
        408,
        null,
      );
    }
    throw new ApiError(
      "Unable to connect to the NEXORA server. Please verify your network connection.",
      0,
      null,
    );
  } finally {
    clearTimeout(timeoutId);
  }

  if (response.status === 401 && !skipAuth && retryOnUnauthorized) {
    const refreshedAccessToken = await refreshAccessToken();
    if (refreshedAccessToken) {
      return apiRequest<T>(path, {
        ...options,
        retryOnUnauthorized: false,
      });
    }
    clearAuthTokens();
    if (typeof window !== "undefined") {
      window.location.href = "/";
    }
  }

  const payload = await parseResponseBody(response);

  if (!response.ok) {
    const normalizedMessage = normalizeApiErrorMessage(
      payload,
      `API request failed with status ${response.status}.`,
    );

    throw new ApiError(normalizedMessage, response.status, payload);
  }

  return payload as T;
}

export const apiClient = {
  get<T>(path: string, options?: ApiRequestOptions): Promise<T> {
    return apiRequest<T>(path, { ...options, method: "GET" });
  },
  post<T>(path: string, body?: unknown, options?: ApiRequestOptions): Promise<T> {
    return apiRequest<T>(path, { ...options, method: "POST", body });
  },
  put<T>(path: string, body?: unknown, options?: ApiRequestOptions): Promise<T> {
    return apiRequest<T>(path, { ...options, method: "PUT", body });
  },
  patch<T>(path: string, body?: unknown, options?: ApiRequestOptions): Promise<T> {
    return apiRequest<T>(path, { ...options, method: "PATCH", body });
  },
  delete<T>(path: string, options?: ApiRequestOptions): Promise<T> {
    return apiRequest<T>(path, { ...options, method: "DELETE" });
  },
};
