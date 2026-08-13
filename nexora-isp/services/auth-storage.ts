const ACCESS_TOKEN_KEY = "nexora_access_token";
const REFRESH_TOKEN_KEY = "nexora_refresh_token";

function canUseBrowserStorage(): boolean {
  return typeof window !== "undefined";
}

export function getAccessToken(): string | null {
  if (!canUseBrowserStorage()) {
    return null;
  }

  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (!canUseBrowserStorage()) {
    return null;
  }

  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setAuthTokens(
  accessToken: string,
  refreshToken: string,
): void {
  if (!canUseBrowserStorage()) {
    return;
  }

  window.localStorage.setItem(
    ACCESS_TOKEN_KEY,
    accessToken,
  );

  window.localStorage.setItem(
    REFRESH_TOKEN_KEY,
    refreshToken,
  );
}

export function setAccessToken(
  accessToken: string,
): void {
  if (!canUseBrowserStorage()) {
    return;
  }

  window.localStorage.setItem(
    ACCESS_TOKEN_KEY,
    accessToken,
  );
}

export function clearAuthTokens(): void {
  if (!canUseBrowserStorage()) {
    return;
  }

  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}