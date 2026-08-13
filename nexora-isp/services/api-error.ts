export type ApiErrorPayload = {
  detail?: string;
  [key: string]: unknown;
};

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(
    message: string,
    status: number,
    payload: unknown = null,
  ) {
    super(message);

    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

function getFirstErrorMessage(value: unknown): string | null {
  if (typeof value === "string") {
    return value;
  }

  if (Array.isArray(value)) {
    for (const item of value) {
      const message = getFirstErrorMessage(item);

      if (message) {
        return message;
      }
    }

    return null;
  }

  if (value && typeof value === "object") {
    for (const nestedValue of Object.values(value)) {
      const message = getFirstErrorMessage(nestedValue);

      if (message) {
        return message;
      }
    }
  }

  return null;
}

export function normalizeApiErrorMessage(
  payload: unknown,
  fallbackMessage: string,
): string {
  if (
    payload &&
    typeof payload === "object" &&
    "detail" in payload
  ) {
    const detail = (payload as ApiErrorPayload).detail;

    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
  }

  return getFirstErrorMessage(payload) ?? fallbackMessage;
}