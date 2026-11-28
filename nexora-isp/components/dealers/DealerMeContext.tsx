"use client";

import { createContext, useContext } from "react";

import { ALL_DEALER_RIGHTS, type DealerMe, type DealerRights } from "@/services/dealer-portal.service";

// Who is signed in to the dealer portal: the dealer (every right) or one of their employees.
export const DealerMeContext = createContext<DealerMe | null>(null);

export function useDealerMe(): DealerMe {
  return useContext(DealerMeContext) ?? { is_dealer: true, name: "", rights: ALL_DEALER_RIGHTS };
}

export function canSeeCustomers(rights: DealerRights) {
  return (
    rights.can_view_customers ||
    rights.can_view_all_customers ||
    rights.can_collect_payments ||
    rights.can_recharge
  );
}
