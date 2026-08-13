import {
  BellRing,
  Boxes,
  BrainCircuit,
  CircleDollarSign,
  CreditCard,
  Headphones,
  LayoutDashboard,
  MessageSquareText,
  Network,
  Package,
  Settings,
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
        title: "Customers",
        href: "/customers",
        icon: Users,
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
        title: "Billing & Payments",
        href: "/billing",
        icon: CreditCard,
        roles: ["OWNER", "STAFF"],
      },
    ],
  },

  // ===========================
  // NEW COMMUNICATION CENTER
  // ===========================
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
    label: "RESOURCES",
    items: [
      {
        title: "Inventory",
        href: "/inventory",
        icon: Boxes,
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
        icon: Package,
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
        roles: ["OWNER"],
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