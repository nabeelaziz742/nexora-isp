"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
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
  Plus,
  Receipt,
  Search,
  Settings,
  Shield,
  ShoppingCart,
  UserCheck,
  UserCog,
  Users,
  Wrench,
  X,
} from "lucide-react";

export interface CommandItem {
  id: string;
  title: string;
  description?: string;
  category: "QUICK ACTIONS" | "OPERATIONS" | "FINANCE" | "RESOURCES & POS" | "COMMUNICATIONS & AI" | "SYSTEM";
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  keywords?: string[];
}

const COMMAND_REGISTRY: CommandItem[] = [
  // Quick Actions
  {
    id: "act-new-customer",
    title: "New Customer Activation",
    description: "Provision a subscriber & assign network connection",
    category: "QUICK ACTIONS",
    href: "/customers/new",
    icon: Plus,
    keywords: ["create", "add", "onboard", "signup"],
  },
  {
    id: "act-pos-terminal",
    title: "Launch POS Retail Terminal",
    description: "Sell hardware & collect cashier payments",
    category: "QUICK ACTIONS",
    href: "/pos",
    icon: ShoppingCart,
    keywords: ["sale", "counter", "checkout", "device"],
  },
  {
    id: "act-collections",
    title: "Collect Bill Payment",
    description: "Process subscriber invoice collection & print receipt",
    category: "QUICK ACTIONS",
    href: "/collections",
    icon: CircleDollarSign,
    keywords: ["pay", "cash", "receive", "receipt"],
  },
  {
    id: "act-accounting",
    title: "Post Journal Entry",
    description: "Record double-entry general ledger transaction",
    category: "QUICK ACTIONS",
    href: "/accounting",
    icon: Landmark,
    keywords: ["journal", "debit", "credit", "ledger"],
  },
  {
    id: "act-audit-logs",
    title: "Investigate Security Audit Logs",
    description: "Explore security, RBAC and financial audit events",
    category: "QUICK ACTIONS",
    href: "/audit-logs",
    icon: Shield,
    keywords: ["security", "history", "compliance", "events"],
  },

  // Operations
  {
    id: "nav-command-center",
    title: "Command Center",
    description: "Executive NOC dashboard & live operational metrics",
    category: "OPERATIONS",
    href: "/command-center",
    icon: LayoutDashboard,
    keywords: ["dashboard", "home", "kpi", "telemetry"],
  },
  {
    id: "nav-customers",
    title: "Customers Directory",
    description: "Subscriber database, lifecycle states & 360° CRM",
    category: "OPERATIONS",
    href: "/customers",
    icon: Users,
    keywords: ["subscribers", "clients", "users", "accounts"],
  },
  {
    id: "nav-inquiries",
    title: "Inquiries & Leads",
    description: "Feasibility intake & prospect conversions",
    category: "OPERATIONS",
    href: "/inquiries",
    icon: ClipboardList,
    keywords: ["leads", "feasibility", "prospects", "sales"],
  },
  {
    id: "nav-operators",
    title: "Operators & Field Recovery",
    description: "Field operator batches & collection quotas",
    category: "OPERATIONS",
    href: "/operators",
    icon: UserCheck,
    keywords: ["cashier", "riders", "recovery"],
  },
  {
    id: "nav-dealers",
    title: "Dealers & Sub-ISPs",
    description: "Franchise networks & commission settlements",
    category: "OPERATIONS",
    href: "/dealers",
    icon: Building2,
    keywords: ["franchise", "subisp", "commissions", "resellers"],
  },
  {
    id: "nav-packages",
    title: "Packages & Bandwidth Plans",
    description: "Speed profiles, pricing tiers & billing cycles",
    category: "OPERATIONS",
    href: "/packages",
    icon: Package,
    keywords: ["plans", "tariffs", "speeds", "bandwidth", "rates"],
  },
  {
    id: "nav-areas",
    title: "Areas & Geographic Coverage",
    description: "City and sub-area territory hierarchy",
    category: "OPERATIONS",
    href: "/areas",
    icon: MapPin,
    keywords: ["zones", "cities", "locations", "coverage"],
  },
  {
    id: "nav-network",
    title: "Network & POP Infrastructure",
    description: "Point of Presence sites, OLT nodes & assignments",
    category: "OPERATIONS",
    href: "/network",
    icon: Network,
    keywords: ["pops", "nodes", "olt", "routers", "topology"],
  },
  {
    id: "nav-support",
    title: "Support & Incident NOC",
    description: "Helpdesk complaints, SLA tracking & escalations",
    category: "OPERATIONS",
    href: "/support",
    icon: Headphones,
    keywords: ["tickets", "complaints", "incidents", "issues", "sla"],
  },
  {
    id: "nav-field-ops",
    title: "Field Operations & Dispatch",
    description: "Technician work orders, installations & repairs",
    category: "OPERATIONS",
    href: "/field-operations",
    icon: Wrench,
    keywords: ["jobs", "technicians", "workorders", "installs"],
  },

  // Finance
  {
    id: "nav-billing",
    title: "Billing Overview & Ledgers",
    description: "Subscriber billing cycles & ledger summaries",
    category: "FINANCE",
    href: "/billing",
    icon: CreditCard,
    keywords: ["finance", "ledgers", "statements"],
  },
  {
    id: "nav-invoices",
    title: "Invoices Management",
    description: "Monthly invoice runs, PDF generation & tax handling",
    category: "FINANCE",
    href: "/invoices",
    icon: FileSpreadsheet,
    keywords: ["bills", "charges", "tax", "generation"],
  },
  {
    id: "nav-collections",
    title: "Collections & Receipts",
    description: "Payment ledger, cashier desk & thermal receipts",
    category: "FINANCE",
    href: "/collections",
    icon: CircleDollarSign,
    keywords: ["payments", "cash", "bank", "receipts"],
  },
  {
    id: "nav-defaulters",
    title: "Defaulter Accounts",
    description: "Aging debt reports & overdue recovery tracking",
    category: "FINANCE",
    href: "/defaulters",
    icon: CircleAlert,
    keywords: ["overdue", "debt", "aging", "unpaid"],
  },
  {
    id: "nav-allocations",
    title: "Recovery Allocations",
    description: "Assign recovery officers to delinquent accounts",
    category: "FINANCE",
    href: "/allocations",
    icon: UserCheck,
    keywords: ["recovery", "assignments", "debtors"],
  },
  {
    id: "nav-promises",
    title: "Promises to Pay (PTP)",
    description: "Deferred payment commitments & grace period holds",
    category: "FINANCE",
    href: "/promises",
    icon: Clock,
    keywords: ["ptp", "promises", "extension", "grace"],
  },
  {
    id: "nav-suspensions",
    title: "Suspensions & Policy",
    description: "Automated network cutoff policies & restorations",
    category: "FINANCE",
    href: "/suspensions",
    icon: AlertTriangle,
    keywords: ["cutoff", "block", "freeze", "restore"],
  },
  {
    id: "nav-accounting",
    title: "Accounting & General Ledger",
    description: "Double-entry COA, journals, GL, trial balance & periods",
    category: "FINANCE",
    href: "/accounting",
    icon: Landmark,
    keywords: ["coa", "general ledger", "balance sheet", "trial balance"],
  },
  {
    id: "nav-expenses",
    title: "Operating Expenses",
    description: "Vendor payouts, operational costs & vouchers",
    category: "FINANCE",
    href: "/expenses",
    icon: Receipt,
    keywords: ["costs", "spend", "vouchers", "bills"],
  },

  // Resources & POS
  {
    id: "nav-inventory",
    title: "Inventory & Hardware Stock",
    description: "Stock levels, consumables & serialized CPE tracking",
    category: "RESOURCES & POS",
    href: "/inventory",
    icon: Boxes,
    keywords: ["stock", "devices", "cpe", "ont", "routers", "cables"],
  },
  {
    id: "nav-pos",
    title: "POS Terminal",
    description: "Rapid retail counter checkout & hardware sales",
    category: "RESOURCES & POS",
    href: "/pos",
    icon: ShoppingCart,
    keywords: ["register", "checkout", "retail", "store"],
  },
  {
    id: "nav-pos-sales",
    title: "POS Sales Register",
    description: "Hardware transaction history, receipts & reversals",
    category: "RESOURCES & POS",
    href: "/pos/sales",
    icon: History,
    keywords: ["receipts", "sales history", "reversals"],
  },

  // Communications & AI
  {
    id: "nav-communications",
    title: "Communication Center",
    description: "Multi-channel SMS, WhatsApp & email notifications",
    category: "COMMUNICATIONS & AI",
    href: "/communications",
    icon: MessageSquareText,
    keywords: ["sms", "whatsapp", "templates", "broadcast"],
  },
  {
    id: "nav-intelligence",
    title: "AI ISP Copilot",
    description: "Operational telemetry intelligence & anomaly detection",
    category: "COMMUNICATIONS & AI",
    href: "/intelligence",
    icon: BrainCircuit,
    keywords: ["ai", "copilot", "insights", "analytics"],
  },
  {
    id: "nav-reports",
    title: "Executive Reports Center",
    description: "Financial, operational & subscriber analytics exports",
    category: "COMMUNICATIONS & AI",
    href: "/reports",
    icon: FileSpreadsheet,
    keywords: ["exports", "analytics", "statements", "pdf"],
  },

  // System
  {
    id: "nav-audit-trail",
    title: "Security Audit Trail",
    description: "Immutable tenant audit logs & investigator tool",
    category: "SYSTEM",
    href: "/audit-logs",
    icon: Shield,
    keywords: ["audit", "logs", "security", "who did what"],
  },
  {
    id: "nav-staff",
    title: "Staff Management & RBAC",
    description: "User accounts, operational roles & permissions",
    category: "SYSTEM",
    href: "/staff",
    icon: UserCog,
    keywords: ["users", "roles", "rbac", "permissions", "team"],
  },
  {
    id: "nav-settings",
    title: "Tenant Settings & Policies",
    description: "Company profile, billing automation & system configuration",
    category: "SYSTEM",
    href: "/settings",
    icon: Settings,
    keywords: ["config", "preferences", "company", "profile"],
  },
];

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const [search, setSearch] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Filtered command items
  const filteredCommands = useMemo(() => {
    if (!search.trim()) {
      return COMMAND_REGISTRY;
    }
    const query = search.toLowerCase().trim();
    return COMMAND_REGISTRY.filter((cmd) => {
      const matchTitle = cmd.title.toLowerCase().includes(query);
      const matchDesc = cmd.description?.toLowerCase().includes(query) ?? false;
      const matchCategory = cmd.category.toLowerCase().includes(query);
      const matchKeywords = cmd.keywords?.some((k) => k.toLowerCase().includes(query)) ?? false;
      return matchTitle || matchDesc || matchCategory || matchKeywords;
    });
  }, [search]);

  // Group filtered commands by category
  const groupedCommands = useMemo(() => {
    const groups: { category: string; items: CommandItem[] }[] = [];
    filteredCommands.forEach((cmd) => {
      let group = groups.find((g) => g.category === cmd.category);
      if (!group) {
        group = { category: cmd.category, items: [] };
        groups.push(group);
      }
      group.items.push(cmd);
    });
    return groups;
  }, [filteredCommands]);

  // Reset selection index when query changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [search]);

  // Focus input on open
  useEffect(() => {
    if (isOpen) {
      setSearch("");
      setSelectedIndex(0);
      setTimeout(() => {
        inputRef.current?.focus();
      }, 50);
    }
  }, [isOpen]);

  // Keyboard navigation inside modal
  useEffect(() => {
    if (!isOpen) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev < filteredCommands.length - 1 ? prev + 1 : 0
        );
        return;
      }

      if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev > 0 ? prev - 1 : Math.max(0, filteredCommands.length - 1)
        );
        return;
      }

      if (e.key === "Enter") {
        e.preventDefault();
        const selected = filteredCommands[selectedIndex];
        if (selected) {
          router.push(selected.href);
          onClose();
        }
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, selectedIndex, filteredCommands, router, onClose]);

  // Ensure selected element is scrolled into view
  useEffect(() => {
    if (!listRef.current) return;
    const activeEl = listRef.current.querySelector(`[data-index="${selectedIndex}"]`);
    if (activeEl) {
      activeEl.scrollIntoView({ block: "nearest" });
    }
  }, [selectedIndex]);

  if (!isOpen) return null;

  let flatIndex = 0;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-16 sm:pt-24 px-4 pb-6">
      {/* Backdrop */}
      <div
        onClick={onClose}
        aria-hidden="true"
        className="fixed inset-0 bg-black/75 backdrop-blur-sm transition-opacity animate-in fade-in-0"
      />

      {/* Modal Dialog */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Global Command Palette"
        className="relative z-10 w-full max-w-2xl overflow-hidden rounded-xl border border-[#202938] bg-[#0D1117] shadow-2xl shadow-black/80 animate-in fade-in-0 zoom-in-95 duration-150"
      >
        {/* Search Input Bar */}
        <div className="flex h-14 items-center gap-3 border-b border-[#202938] px-4 bg-[#070A0F]">
          <Search className="h-5 w-5 shrink-0 text-blue-400" />
          <input
            ref={inputRef}
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Type a command, workspace or action..."
            className="flex-1 bg-transparent text-sm text-[#F8FAFC] placeholder:text-slate-500 outline-none"
          />
          {search && (
            <button
              type="button"
              onClick={() => setSearch("")}
              aria-label="Clear search"
              className="text-slate-500 hover:text-slate-300 transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          )}
          <kbd className="hidden sm:inline-flex items-center gap-1 rounded border border-[#202938] bg-[#121821] px-2 py-0.5 font-mono text-[10px] text-slate-400">
            ESC
          </kbd>
        </div>

        {/* Command List */}
        <div
          ref={listRef}
          className="nexora-scrollbar max-h-[60vh] overflow-y-auto p-2"
        >
          {filteredCommands.length === 0 ? (
            <div className="py-12 text-center">
              <Search className="mx-auto h-8 w-8 text-slate-600 mb-2" />
              <p className="text-xs font-medium text-slate-300">
                No matching workspaces or actions found
              </p>
              <p className="text-[11px] text-slate-500 mt-1">
                Try searching for &quot;customers&quot;, &quot;invoices&quot;, &quot;POS&quot;, or &quot;accounting&quot;
              </p>
            </div>
          ) : (
            groupedCommands.map((group) => (
              <div key={group.category} className="mb-3 last:mb-1">
                <p className="px-3 py-1.5 text-[9px] font-bold uppercase tracking-[0.14em] text-slate-500">
                  {group.category}
                </p>
                <div className="space-y-0.5">
                  {group.items.map((cmd) => {
                    const currentIndex = flatIndex++;
                    const isSelected = currentIndex === selectedIndex;
                    const Icon = cmd.icon;

                    return (
                      <button
                        key={cmd.id}
                        type="button"
                        data-index={currentIndex}
                        onClick={() => {
                          router.push(cmd.href);
                          onClose();
                        }}
                        onMouseEnter={() => setSelectedIndex(currentIndex)}
                        className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-xs transition-all ${
                          isSelected
                            ? "bg-blue-600/15 text-blue-400 border border-blue-500/30"
                            : "text-slate-300 hover:bg-[#121821] hover:text-slate-100 border border-transparent"
                        }`}
                      >
                        <div
                          className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md ${
                            isSelected
                              ? "bg-blue-600 text-white shadow-xs"
                              : "bg-[#121821] text-slate-400 border border-[#202938]"
                          }`}
                        >
                          <Icon className="h-4 w-4" />
                        </div>

                        <div className="min-w-0 flex-1">
                          <p className="font-medium text-slate-100 truncate">
                            {cmd.title}
                          </p>
                          {cmd.description && (
                            <p className="text-[11px] text-slate-400 truncate mt-0.5">
                              {cmd.description}
                            </p>
                          )}
                        </div>

                        {isSelected && (
                          <span className="shrink-0 font-mono text-[10px] text-blue-400">
                            ↵ Enter
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer info bar */}
        <div className="flex items-center justify-between border-t border-[#202938] bg-[#070A0F] px-4 py-2 text-[10px] text-slate-500">
          <div className="flex items-center gap-3">
            <span>
              <kbd className="rounded border border-[#202938] bg-[#121821] px-1 py-0.5 font-mono">↑</kbd>
              <kbd className="ml-1 rounded border border-[#202938] bg-[#121821] px-1 py-0.5 font-mono">↓</kbd> to navigate
            </span>
            <span>
              <kbd className="rounded border border-[#202938] bg-[#121821] px-1.5 py-0.5 font-mono">↵</kbd> to select
            </span>
          </div>
          <span>
            {filteredCommands.length} destination{filteredCommands.length !== 1 ? "s" : ""}
          </span>
        </div>
      </div>
    </div>
  );
}
