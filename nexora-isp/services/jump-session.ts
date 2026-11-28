import { apiRequest } from "@/services/api-client";
import {
  clearAuthTokens,
  getAccessToken,
  getRefreshToken,
  setAuthTokens,
} from "@/services/auth-storage";

const STACK_KEY = "nexora_jump_stack";

export interface JumpSessionResponse {
  access: string;
  refresh: string;
  jump_kind: "DEALER" | "DEALER_EMPLOYEE";
  target_name: string;
  target_email: string;
  impersonated_by: string;
  impersonated_by_name: string;
  user: {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
  };
  organization: {
    id: string;
    name: string;
    code: string;
  };
  role: string;
}

export interface JumpFrame {
  access: string;
  refresh: string;
  user: string | null;
  organization: string | null;
  role: string | null;
  returnTo: string;
  viewerLabel: string;
}

function readStack(): JumpFrame[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STACK_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as JumpFrame[]) : [];
  } catch {
    return [];
  }
}

function writeStack(frames: JumpFrame[]): void {
  if (typeof window === "undefined") return;
  if (frames.length === 0) {
    window.localStorage.removeItem(STACK_KEY);
  } else {
    window.localStorage.setItem(STACK_KEY, JSON.stringify(frames));
  }
}

export function getJumpBanner(): { viewerLabel: string; returnTo: string } | null {
  const stack = readStack();
  if (stack.length === 0) return null;
  const top = stack[stack.length - 1];
  return { viewerLabel: top.viewerLabel, returnTo: top.returnTo };
}

export function clearJumpStack(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STACK_KEY);
}

export function pushJumpSession(
  res: JumpSessionResponse,
  options: { returnTo: string; viewerLabel: string },
): void {
  if (typeof window === "undefined") return;
  const stack = readStack();
  stack.push({
    access: getAccessToken() ?? "",
    refresh: getRefreshToken() ?? "",
    user: window.localStorage.getItem("nexora_user"),
    organization: window.localStorage.getItem("nexora_organization"),
    role: window.localStorage.getItem("nexora_role"),
    returnTo: options.returnTo,
    viewerLabel: options.viewerLabel,
  });
  writeStack(stack);

  setAuthTokens(res.access, res.refresh);
  window.localStorage.setItem("nexora_user", JSON.stringify(res.user));
  window.localStorage.setItem("nexora_organization", JSON.stringify(res.organization));
  window.localStorage.setItem("nexora_role", res.role);
}

export async function popJumpSession(): Promise<string> {
  const currentRefresh = getRefreshToken() ?? "";
  try {
    await apiRequest("/auth/jump/back/", {
      method: "POST",
      body: { refresh: currentRefresh },
    });
  } catch {
    // Restore original session locally even if the temporary jump token already expired.
  }

  const stack = readStack();
  const top = stack.pop();
  writeStack(stack);
  if (!top) {
    return "/";
  }

  setAuthTokens(top.access, top.refresh);
  if (top.user !== null) window.localStorage.setItem("nexora_user", top.user);
  else window.localStorage.removeItem("nexora_user");
  if (top.organization !== null) window.localStorage.setItem("nexora_organization", top.organization);
  else window.localStorage.removeItem("nexora_organization");
  if (top.role !== null) window.localStorage.setItem("nexora_role", top.role);
  else window.localStorage.removeItem("nexora_role");

  return top.returnTo || "/";
}

export async function signOutAllStackedSessions(): Promise<void> {
  if (typeof window === "undefined") return;
  const tokensToRevoke: string[] = [];
  const currentRefresh = getRefreshToken();
  if (currentRefresh) tokensToRevoke.push(currentRefresh);
  for (const frame of readStack()) {
    if (frame.refresh) tokensToRevoke.push(frame.refresh);
  }

  await Promise.allSettled(
    tokensToRevoke.map((refresh) =>
      apiRequest("/auth/logout/", { method: "POST", body: { refresh } }).catch(() => null),
    ),
  );
  clearJumpStack();
  clearAuthTokens();
  window.localStorage.removeItem("nexora_user");
  window.localStorage.removeItem("nexora_organization");
  window.localStorage.removeItem("nexora_role");
}
