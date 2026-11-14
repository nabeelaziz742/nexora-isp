"use client";

import { createContext, useContext } from "react";

import type { DealerMe, DealerRights } from "@/services/dealer-portal.service";

// Who is signed in to the dealer portal: the dealer (every right) or one of their employees.
export const DealerMeContext = createContext<DealerMe | null>(null);

const ALL_RIGHTS: DealerRights = {
  can_view_customers: true,
  can_collect_payments: true,
  can_recharge: true,
  can_request_customers: true,
  can_view_collections: true,
};

export function useDealerMe(): DealerMe {
  return useContext(DealerMeContext) ?? { is_dealer: true, name: "", rights: ALL_RIGHTS };
}

export function canSeeCustomers(rights: DealerRights) {
  return rights.can_view_customers || rights.can_collect_payments || rights.can_recharge;
}
