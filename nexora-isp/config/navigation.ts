import {
  AlertTriangle,
  BellRing,
  Boxes,
  BrainCircuit,
  Building2,
  CircleAlert,
  CircleDollarSign,
  ClipboardList,
  Clock,
  CreditCard,
  FileSpreadsheet,
  Headphones,
  History,
  Landmark,
  LayoutDashboard,
  MapPin,
  MessageSquareText,
  Network,
  Package,
  Receipt,
  Settings,
  Shield,
  ShoppingCart,
  UserCheck,
  UserCog,
  Users,
  Wrench,
} from "lucide-react";

export type NavigationRole =
  | "OWNER"
  | "STAFF"
  | "TECHNICIAN";

export type NavigationItem = {
  title: string;
  href: string;
  icon: typeof LayoutDashboard;
  roles?: NavigationRole[];
};

export type NavigationGroup = {
  label: string;
  items: NavigationItem[];
};

export const navigation: NavigationGroup[] = [
  {
    label: "COMMAND",
    items: [
      {
        title: "Command Center",
        href: "/command-center",
        icon: LayoutDashboard,
        roles: ["OWNER", "STAFF"],
      },
    ],
  },

  {
    label: "OPERATIONS",
    items: [
      {
        title: "Inquiries & Leads",
        href: "/inquiries",
        icon: ClipboardList,
        roles: ["OWNER", "STAFF"],
      },
      {
        title: "Customers",
        href: "/customers",
        icon: Users,
        roles: ["OWNER", "STAFF"],
      },
      {
        title: "Operators & Recovery",
        href: "/operators",
        icon: UserCheck,
        roles: ["OWNER", "STAFF"],
      },
      {
        title: "Dealers / Sub-ISPs",
        href: "/dealers",
        icon: Building2,
        roles: ["OWNER", "STAFF"],
      },
      {
        title: "Packages & Plans",
        href: "/packages",
        icon: Package,
        roles: ["OWNER", "STAFF"],
      },
      {
        title: "Areas & Hierarchy",
        href: "/areas",
        icon: MapPin,
        roles: ["OWNER", "STAFF"],
      },
      {
        title: "Network",
        href: "/network",
        icon: Network,
        roles: ["OWNER", "STAFF"],
      },
      {
        title: "Support & Incidents",
        href: "/support",
        icon: Headphones,
        roles: ["OWNER", "STAFF"],
      },
      {
        title: "My Field Jobs",
        href: "/field-operations",
        icon: Wrench,
        roles: ["TECHNICIAN"],
      },
      {
        title: "Field Operations",
        href: "/field-operations",
        icon: Wrench,
        roles: ["OWNER", "STAFF"],
      },
    ],
  },

  {
    label: "FINANCE",
    items: [
      {
        title: "Billing Overview",
        href: "/billing",
        icon: CreditCard,
        roles: ["OWNER", "STAFF"],
      },
      {
        title: "Invoices Management",
        href: "/invoices",
        icon: FileSpreadsheet,
        roles: ["OWNER", "STAFF"],
      },
      {
        title: "Collections & Receipts",
        href: "/collections",
        icon: CircleDollarSign,
        roles: ["OWNER", "STAFF"],
      },
      {
        title: "Defaulter Accounts",
        href: "/defaulters",
        icon: CircleAlert,
        roles: ["OWNER", "STAFF"],
      },
      {
        title: "Recovery Allocations",
        href: "/allocations",
        icon: UserCheck,
        roles: ["OWNER", "STAFF"],
      },
      {
        title: "Promises to Pay",
        href: "/promises",
        icon: Clock,
        roles: ["OWNER", "STAFF"],
      },
      {
        title: "Suspensions & Policy",
        href: "/suspensions",
        icon: AlertTriangle,
        roles: ["OWNER", "STAFF"],
      },
      {
        title: "Accounting & Ledger",
        href: "/accounting",
        icon: Landmark,
        roles: ["OWNER", "STAFF"],
      },
      {
        title: "Expenses",
        href: "/expenses",
        icon: Receipt,
        roles: ["OWNER", "STAFF"],
      },
    ],
  },

  {
    label: "COMMUNICATIONS",
    items: [
      {
        title: "Communication Center",
        href: "/communications",
        icon: MessageSquareText,
        roles: ["OWNER", "STAFF"],
      },
    ],
  },

  {
    label: "RESOURCES & POS",
    items: [
      {
        title: "Inventory",
        href: "/inventory",
        icon: Boxes,
        roles: ["OWNER", "STAFF"],
      },
      {
        title: "POS Terminal",
        href: "/pos",
        icon: ShoppingCart,
        roles: ["OWNER", "STAFF"],
      },
      {
        title: "Sales Register",
        href: "/pos/sales",
        icon: History,
        roles: ["OWNER", "STAFF"],
      },
    ],
  },

  {
    label: "INTELLIGENCE",
    items: [
      {
        title: "AI Copilot",
        href: "/intelligence",
        icon: BrainCircuit,
        roles: ["OWNER", "STAFF"],
      },
      {
        title: "Revenue Intelligence",
        href: "/intelligence/revenue",
        icon: CircleDollarSign,
        roles: ["OWNER", "STAFF"],
      },
      {
        title: "Reports",
        href: "/reports",
        icon: FileSpreadsheet,
        roles: ["OWNER", "STAFF"],
      },
    ],
  },

  {
    label: "SYSTEM",
    items: [
      {
        title: "Notification Operations",
        href: "/notifications",
        icon: BellRing,
        roles: ["OWNER", "STAFF"],
      },
      {
        title: "Staff Management",
        href: "/staff",
        icon: UserCog,
        roles: ["OWNER", "STAFF"],
      },
      {
        title: "Audit Trail",
        href: "/audit-logs",
        icon: Shield,
        roles: ["OWNER", "STAFF"],
      },
      {
        title: "Settings",
        href: "/settings",
        icon: Settings,
        roles: ["OWNER", "STAFF"],
      },
    ],
  },
];

export function getNavigationForRole(
  role: NavigationRole | null,
): NavigationGroup[] {
  if (!role) {
    return [];
  }

  return navigation
    .map((group) => ({
      ...group,
      items: group.items.filter(
        (item) =>
          !item.roles || item.roles.includes(role),
      ),
    }))
    .filter((group) => group.items.length > 0);
}