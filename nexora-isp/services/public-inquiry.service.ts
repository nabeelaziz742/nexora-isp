import { ApiError, normalizeApiErrorMessage } from "@/services/api-error";

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1"
).replace(/\/$/, "");

export type PublicPackage = {
  id: string;
  name: string;
  download_speed_mbps: number;
  upload_speed_mbps: number;
  monthly_price: string;
};

export type PublicApplyForm = {
  organization: {
    name: string;
    city: string;
    phone: string;
  };
  packages: PublicPackage[];
  connection_types: { value: string; label: string }[];
};

export type PublicInquiryPayload = {
  full_name: string;
  phone: string;
  email?: string;
  address_line: string;
  city: string;
  area?: string;
  preferred_package?: string | null;
  connection_type?: string;
  notes?: string;
  // Honeypot; must stay empty.
  website?: string;
};

export type PublicInquiryResponse = {
  detail: string;
  reference?: string;
};

function applyUrl(organizationCode: string) {
  return `${API_BASE_URL}/customers/public/apply/${encodeURIComponent(organizationCode)}/`;
}

// Public form endpoints: no auth header, so they work for anyone with the link.
export async function getPublicApplyForm(
  organizationCode: string,
): Promise<PublicApplyForm> {
  const response = await fetch(applyUrl(organizationCode));
  const data = await response.json();
  if (!response.ok) {
    throw new ApiError(
      normalizeApiErrorMessage(data, "This ISP link is not available."),
      response.status,
      data,
    );
  }
  return data as PublicApplyForm;
}

export async function submitPublicInquiry(
  organizationCode: string,
  payload: PublicInquiryPayload,
): Promise<PublicInquiryResponse> {
  const response = await fetch(applyUrl(organizationCode), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new ApiError(
      response.status === 429
        ? "Too many requests from this network. Please try again later."
        : normalizeApiErrorMessage(data, "Unable to submit your request."),
      response.status,
      data,
    );
  }
  return data as PublicInquiryResponse;
}
