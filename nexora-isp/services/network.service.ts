import { apiRequest, normalizeList, type ListResponse } from "@/services/api-client";

import type {
  NetworkAssignment,
  NetworkNode,
  PointOfPresence,
  ProvisioningAction,
  ProvisioningRequest,
  ProvisioningStatus,
} from "@/types/network";

interface GetNetworkNodesParams {
  active?: boolean;
  type?: string;
  search?: string;
}

interface GetNetworkAssignmentsParams {
  nodeId?: string;
  active?: boolean;
  search?: string;
}

interface GetProvisioningRequestsParams {
  status?: ProvisioningStatus | "";
  action?: ProvisioningAction | "";
  search?: string;
}

function buildQueryString(
  params: Record<
    string,
    string | boolean | undefined
  >,
) {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (typeof value === "boolean") {
      searchParams.set(
        key,
        value ? "true" : "false",
      );

      return;
    }

    if (
      typeof value === "string" &&
      value.trim()
    ) {
      searchParams.set(key, value.trim());
    }
  });

  const queryString = searchParams.toString();

  return queryString ? `?${queryString}` : "";
}

export const networkService = {
  async getNodes(
    params: GetNetworkNodesParams = {},
  ): Promise<NetworkNode[]> {
    const queryString = buildQueryString({
      active: params.active,
      type: params.type,
      search: params.search,
    });

    const res = await apiRequest<ListResponse<NetworkNode>>(
      `/network/nodes/${queryString}`,
    );
    return normalizeList<NetworkNode>(res);
  },

  getNode(nodeId: string): Promise<NetworkNode> {
    return apiRequest<NetworkNode>(
      `/network/nodes/${nodeId}/`,
    );
  },

  async getAssignments(
    params: GetNetworkAssignmentsParams = {},
  ): Promise<NetworkAssignment[]> {
    const queryString = buildQueryString({
      node_id: params.nodeId,
      active: params.active,
      search: params.search,
    });

    const res = await apiRequest<ListResponse<NetworkAssignment>>(
      `/network/assignments/${queryString}`,
    );
    return normalizeList<NetworkAssignment>(res);
  },

  async getProvisioningRequests(
    params: GetProvisioningRequestsParams = {},
  ): Promise<ProvisioningRequest[]> {
    const queryString = buildQueryString({
      status: params.status,
      action: params.action,
      search: params.search,
    });

    const res = await apiRequest<ListResponse<ProvisioningRequest>>(
      `/network/provisioning-requests/${queryString}`,
    );
    return normalizeList<ProvisioningRequest>(res);
  },

  requestSuspension(
    serviceAccountId: string,
  ): Promise<ProvisioningRequest> {
    return apiRequest<ProvisioningRequest>(
      `/network/services/${serviceAccountId}/suspension-requests/`,
      {
        method: "POST",
      },
    );
  },

  requestRestore(
    serviceAccountId: string,
  ): Promise<ProvisioningRequest> {
    return apiRequest<ProvisioningRequest>(
      `/network/services/${serviceAccountId}/restore-requests/`,
      {
        method: "POST",
      },
    );
  },

  requestPackageChange(
    serviceAccountId: string,
    internetPackageId: string,
  ): Promise<ProvisioningRequest> {
    return apiRequest<ProvisioningRequest>(
      `/network/services/${serviceAccountId}/package-change-requests/`,
      {
        method: "POST",
        body: {
          internet_package_id: internetPackageId,
        },
      },
    );
  },

  async getPops(
    params: {
      pop_type?: string;
      status?: string;
      area_id?: string;
      search?: string;
    } = {},
  ): Promise<PointOfPresence[]> {
    const queryString = buildQueryString({
      pop_type: params.pop_type,
      status: params.status,
      area_id: params.area_id,
      search: params.search,
    });

    const res = await apiRequest<ListResponse<PointOfPresence>>(
      `/network/pops/${queryString}`,
    );
    return normalizeList<PointOfPresence>(res);
  },

  getPop(popId: string): Promise<PointOfPresence> {
    return apiRequest<PointOfPresence>(
      `/network/pops/${popId}/`,
    );
  },

  createPop(data: Partial<PointOfPresence>): Promise<PointOfPresence> {
    return apiRequest<PointOfPresence>(
      `/network/pops/`,
      {
        method: "POST",
        body: data,
      },
    );
  },

  updatePop(popId: string, data: Partial<PointOfPresence>): Promise<PointOfPresence> {
    return apiRequest<PointOfPresence>(
      `/network/pops/${popId}/`,
      {
        method: "PATCH",
        body: data,
      },
    );
  },
};

export type { NetworkNode, PointOfPresence, PopType, PopStatus } from "@/types/network";