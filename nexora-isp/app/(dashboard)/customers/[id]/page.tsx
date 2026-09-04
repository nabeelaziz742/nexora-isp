"use client";

import {
  useCallback,
  useEffect,
  useState,
} from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  BellRing,
  Check,
  ChevronRight,
  Copy,
  CreditCard,
  Edit,
  HardDrive,
  HelpCircle,
  History,
  Loader2,
  MapPin,
  Network,
  Package,
  PauseCircle,
  Phone,
  PlayCircle,
  Plus,
  RefreshCw,
  RotateCcw,
  Router,
  ShieldAlert,
  ShieldCheck,
  UserCheck,
  UserRound,
  Wifi,
  X,
} from "lucide-react";

import EmptyState from "@/components/ui/EmptyState";
import ErrorState from "@/components/ui/ErrorState";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import Skeleton from "@/components/ui/Skeleton";
import { useToast } from "@/hooks/useToast";
import { billingService } from "@/services/billing.service";
import {
  customersService,
  type CustomerDetail,
  type CustomerServiceAccount,
  type CustomerServiceStatus,
  type CustomerUpdatePayload,
  type InternetPackage,
} from "@/services/customers.service";
import { geoService, type City, type Area } from "@/services/geo.service";
import {
  inventoryService,
  type InventoryDevice,
  type ReturnCondition,
} from "@/services/inventory.service";
import { networkService } from "@/services/network.service";
import { supportService, type Complaint } from "@/services/support.service";
import type {
  FinancialLedger,
  Invoice,
  Payment,
  PaymentMethod,
  PaymentReceipt,
} from "@/types/billing";
import type { ProvisioningRequest } from "@/types/network";

const serviceStatusStyles: Record<
  CustomerServiceStatus,
  { badge: string; dot: string; label: string }
> = {
  ACTIVE: {
    badge: "border-green-500/20 bg-green-500/10 text-green-400",
    dot: "bg-green-400",
    label: "Active",
  },
  GRACE_PERIOD: {
    badge: "border-amber-500/20 bg-amber-500/10 text-amber-400",
    dot: "bg-amber-400",
    label: "Grace Period",
  },
  SUSPENSION_PENDING: {
    badge: "border-orange-500/20 bg-orange-500/10 text-orange-400",
    dot: "bg-orange-400",
    label: "Suspension Pending",
  },
  SUSPENDED_NON_PAYMENT: {
    badge: "border-red-500/20 bg-red-500/10 text-red-400",
    dot: "bg-red-400",
    label: "Suspended (Non-Payment)",
  },
  RESTORE_PENDING: {
    badge: "border-blue-500/20 bg-blue-500/10 text-blue-400",
    dot: "bg-blue-400",
    label: "Restore Pending",
  },
};

function formatMoney(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return "—";
  const amount = Number(value);
  if (Number.isNaN(amount)) return String(value);
  return `Rs. ${amount.toLocaleString()}`;
}

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-PK", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

export default function CustomerDetailPage() {
  const params = useParams<{ id: string }>();
  const customerId = params.id;
  const toast = useToast();

  const [customer, setCustomer] = useState<CustomerDetail | null>(null);
  const [packages, setPackages] = useState<InternetPackage[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [ledger, setLedger] = useState<FinancialLedger | null>(null);
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [provisioningRequests, setProvisioningRequests] = useState<ProvisioningRequest[]>([]);
  const [availableDevices, setAvailableDevices] = useState<InventoryDevice[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"connections" | "devices" | "billing" | "support" | "profile">("connections");

  // Modals state
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isChangePackageModalOpen, setIsChangePackageModalOpen] = useState(false);
  const [isSuspendModalOpen, setIsSuspendModalOpen] = useState(false);
  const [isRestoreModalOpen, setIsRestoreModalOpen] = useState(false);
  const [isAssignDeviceModalOpen, setIsAssignDeviceModalOpen] = useState(false);
  const [isReturnDeviceModalOpen, setIsReturnDeviceModalOpen] = useState<string | null>(null);

  // Billing modals
  const [isCollectPaymentOpen, setIsCollectPaymentOpen] = useState(false);
  const [collectPayAmount, setCollectPayAmount] = useState("");
  const [collectPayMethod, setCollectPayMethod] = useState<PaymentMethod>("CASH");
  const [collectPayRef, setCollectPayRef] = useState("");
  const [collectPayNotes, setCollectPayNotes] = useState("");
  const [isReceiptModalOpen, setIsReceiptModalOpen] = useState(false);
  const [selectedReceipt, setSelectedReceipt] = useState<PaymentReceipt | null>(null);
  const [receiptLoading, setReceiptLoading] = useState(false);

  // Action loaders
  const [actionLoading, setActionLoading] = useState(false);
  const [selectedServiceId, setSelectedServiceId] = useState<string>("");
  const [targetPackageId, setTargetPackageId] = useState<string>("");
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>("");
  const [deviceNotes, setDeviceNotes] = useState<string>("");
  const [returnCondition, setReturnCondition] = useState<ReturnCondition>("GOOD");
  const [returnNotes, setReturnNotes] = useState<string>("");

  const loadCustomerData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [customerData, pkgData] = await Promise.all([
        customersService.getCustomer(customerId),
        customersService.getInternetPackages({ status: "active" }),
      ]);

      setCustomer(customerData);
      setPackages(pkgData);

      if (customerData.service_accounts.length > 0) {
        setSelectedServiceId(customerData.service_accounts[0].id);
        setTargetPackageId(customerData.service_accounts[0].internet_package.id);
      }

      // Load optional contextual data asynchronously
      void Promise.allSettled([
        billingService.getInvoices({ customer_id: customerId }),
        billingService.getPayments({ customer_id: customerId }),
        billingService.getLedger({ customer_id: customerId }),
        supportService.getComplaints(),
        networkService.getProvisioningRequests({ search: customerData.customer_number }),
        inventoryService.getDevices(),
      ]).then(([invoicesRes, paymentsRes, ledgerRes, complaintsRes, provRes, devicesRes]) => {
        if (invoicesRes.status === "fulfilled") {
          setInvoices(invoicesRes.value);
        }
        if (paymentsRes.status === "fulfilled") {
          setPayments(paymentsRes.value);
        }
        if (ledgerRes.status === "fulfilled") {
          setLedger(ledgerRes.value);
        }
        if (complaintsRes.status === "fulfilled") {
          setComplaints(complaintsRes.value.filter((c) => c.customer_id === customerId));
        }
        if (provRes.status === "fulfilled") {
          setProvisioningRequests(provRes.value);
        }
        if (devicesRes.status === "fulfilled") {
          setAvailableDevices(devicesRes.value.filter((d) => d.status === "AVAILABLE"));
        }
      });
    } catch (requestError) {
      console.error("Failed to load customer 360 detail:", requestError);
      setCustomer(null);
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to load customer record."
      );
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    if (customerId) {
      void loadCustomerData();
    }
  }, [customerId, loadCustomerData]);

  // Copy helper
  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    toast.success(`${label} copied to clipboard`);
  };

  // Toggle Customer Active Status
  const handleToggleStatus = async () => {
    if (!customer) return;
    try {
      setActionLoading(true);
      const updated = await customersService.toggleCustomerStatus(customer.id);
      setCustomer(updated);
      toast.success(
        updated.is_active
          ? "Customer account activated"
          : "Customer account deactivated"
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to toggle status");
    } finally {
      setActionLoading(false);
    }
  };

  // Suspend Service
  const handleSuspendService = async () => {
    if (!selectedServiceId) return;
    try {
      setActionLoading(true);
      await networkService.requestSuspension(selectedServiceId);
      setIsSuspendModalOpen(false);
      toast.success("Service suspension requested. Provisioning state is pending.");
      await loadCustomerData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Suspension request failed");
    } finally {
      setActionLoading(false);
    }
  };

  // Restore Service
  const handleRestoreService = async () => {
    if (!selectedServiceId) return;
    try {
      setActionLoading(true);
      await networkService.requestRestore(selectedServiceId);
      setIsRestoreModalOpen(false);
      toast.success("Service restoration requested. Provisioning state is pending.");
      await loadCustomerData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Restore request failed");
    } finally {
      setActionLoading(false);
    }
  };

  // Change Package
  const handleChangePackage = async () => {
    if (!selectedServiceId || !targetPackageId) return;
    try {
      setActionLoading(true);
      await networkService.requestPackageChange(selectedServiceId, targetPackageId);
      setIsChangePackageModalOpen(false);
      toast.success("Package change requested successfully.");
      await loadCustomerData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Package change request failed");
    } finally {
      setActionLoading(false);
    }
  };

  // Assign Device
  const handleAssignDevice = async () => {
    if (!selectedServiceId || !selectedDeviceId) {
      toast.error("Please select an available device.");
      return;
    }
    try {
      setActionLoading(true);
      await inventoryService.assignDevice(selectedDeviceId, selectedServiceId, deviceNotes);
      setIsAssignDeviceModalOpen(false);
      setSelectedDeviceId("");
      setDeviceNotes("");
      toast.success("Inventory device assigned successfully.");
      await loadCustomerData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Device assignment failed");
    } finally {
      setActionLoading(false);
    }
  };

  // Return Device
  const handleReturnDevice = async () => {
    if (!isReturnDeviceModalOpen) return;
    try {
      setActionLoading(true);
      await inventoryService.returnDevice(isReturnDeviceModalOpen, returnCondition, returnNotes);
      setIsReturnDeviceModalOpen(null);
      setReturnNotes("");
      setReturnCondition("GOOD");
      toast.success("Device returned and unassigned from service.");
      await loadCustomerData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Device return failed");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8">
        <div className="space-y-6">
          <Skeleton className="h-6 w-36" />
          <Skeleton className="h-20 w-full" />
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <Skeleton className="h-80 w-full lg:col-span-2" />
            <Skeleton className="h-80 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !customer) {
    return (
      <div className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8">
        <Link
          href="/customers"
          className="inline-flex items-center gap-1.5 text-xs text-[var(--text-muted)] hover:text-white"
        >
          <ArrowLeft className="size-3.5" />
          Back to Customers
        </Link>
        <div className="mt-6">
          <ErrorState
            title="Unable to Open Subscriber Profile"
            message={error || "Customer record does not exist or access was denied."}
            onRetry={() => void loadCustomerData()}
          />
        </div>
      </div>
    );
  }

  const primaryService = customer.service_accounts[0] as CustomerServiceAccount | undefined;
  const statusCfg = primaryService ? serviceStatusStyles[primaryService.status] : null;

  return (
    <div className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8">
      {/* Top Navigation */}
      <Link
        href="/customers"
        className="inline-flex items-center gap-1.5 text-xs text-[var(--text-muted)] transition-colors hover:text-white"
      >
        <ArrowLeft className="size-3.5" />
        <span>Subscribers Directory</span>
      </Link>

      {/* Hero 360 Header */}
      <div className="mt-4 border border-[var(--border)] bg-[var(--surface)] p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
                {customer.full_name}
              </h1>

              {statusCfg && (
                <span className={`inline-flex items-center gap-1.5 border px-2.5 py-1 text-xs font-semibold uppercase tracking-wider ${statusCfg.badge}`}>
                  <span className={`size-1.5 rounded-full ${statusCfg.dot}`} />
                  {statusCfg.label}
                </span>
              )}

              <button
                type="button"
                onClick={handleToggleStatus}
                disabled={actionLoading}
                className={`inline-flex items-center gap-1 border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider transition-colors ${
                  customer.is_active
                    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"
                    : "border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20"
                }`}
              >
                {customer.is_active ? <ShieldCheck className="size-3" /> : <ShieldAlert className="size-3" />}
                {customer.is_active ? "Account Active" : "Account Inactive"}
              </button>
            </div>

            <div className="mt-2.5 flex flex-wrap items-center gap-4 text-xs text-[var(--text-muted)]">
              <button
                type="button"
                onClick={() => copyToClipboard(customer.customer_number, "Customer Number")}
                className="group flex items-center gap-1.5 font-mono text-blue-400 hover:text-blue-300"
              >
                <span>{customer.customer_number}</span>
                <Copy className="size-3 opacity-60 group-hover:opacity-100" />
              </button>
              <span>•</span>
              <span className="flex items-center gap-1 text-slate-300">
                <Phone className="size-3 text-slate-500" /> {customer.phone}
              </span>
              <span>•</span>
              <span className="flex items-center gap-1 text-slate-300">
                <MapPin className="size-3 text-slate-500" />
                {[customer.area, customer.city].filter(Boolean).join(", ") || "No location recorded"}
              </span>
              <span>•</span>
              <span>Joined {formatDate(customer.created_at)}</span>
            </div>
          </div>

          {/* Header Action Buttons */}
          <div className="flex flex-wrap items-center gap-2.5">
            <button
              type="button"
              onClick={() => void loadCustomerData()}
              disabled={loading}
              className="flex h-9 items-center gap-2 border border-[var(--border)] bg-[var(--surface-elevated)] px-3 text-xs font-medium text-slate-300 hover:text-white"
            >
              <RefreshCw className={`size-3.5 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </button>

            <button
              type="button"
              onClick={() => setIsEditModalOpen(true)}
              className="flex h-9 items-center gap-2 bg-blue-600 px-4 text-xs font-semibold text-white hover:bg-blue-500"
            >
              <Edit className="size-3.5" />
              Edit Profile
            </button>
          </div>
        </div>

        {/* 360 Navigation Tabs */}
        <div className="mt-6 flex flex-wrap gap-1 border-t border-[var(--border)] pt-4">
          {[
            { id: "connections", label: "Connection & Network", icon: Wifi },
            { id: "devices", label: `Hardware / CPE (${primaryService?.device_assignments?.length || 0})`, icon: Router },
            { id: "billing", label: `Billing & Invoices (${invoices.length})`, icon: CreditCard },
            { id: "support", label: `Support Tickets (${complaints.length})`, icon: HelpCircle },
            { id: "profile", label: "Subscriber Details", icon: UserRound },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 border px-3.5 py-2 text-xs font-medium transition-colors ${
                  isActive
                    ? "border-blue-500/40 bg-blue-500/10 text-blue-400"
                    : "border-transparent text-[var(--text-secondary)] hover:border-[var(--border)] hover:bg-white/[0.02] hover:text-white"
                }`}
              >
                <Icon className="size-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* TAB 1: Connection & Network */}
      {activeTab === "connections" && (
        <div className="mt-6 space-y-6">
          {customer.service_accounts.length === 0 ? (
            <EmptyState
              title="No Service Connections Found"
              description="This customer does not have any active internet service accounts assigned."
            />
          ) : (
            customer.service_accounts.map((service, index) => {
              const svcStatusCfg = serviceStatusStyles[service.status];
              const netAssign = service.network_assignment;
              const canSuspend = service.status === "ACTIVE" || service.status === "GRACE_PERIOD";
              const canRestore = service.status === "SUSPENDED_NON_PAYMENT";
              const canChangePlan = service.status === "ACTIVE";

              return (
                <div key={service.id} className="border border-[var(--border)] bg-[var(--surface)]">
                  {/* Service Header */}
                  <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border)] bg-[var(--surface-elevated)] px-6 py-4">
                    <div>
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                        Service Connection #{index + 1}
                      </span>
                      <div className="mt-1 flex items-center gap-3">
                        <h3 className="font-mono text-base font-bold text-white">
                          {service.service_number}
                        </h3>
                        <span className={`inline-flex items-center gap-1.5 border px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider ${svcStatusCfg.badge}`}>
                          <span className={`size-1.5 rounded-full ${svcStatusCfg.dot}`} />
                          {svcStatusCfg.label}
                        </span>
                      </div>
                    </div>

                    {/* Service Lifecycle Action Buttons */}
                    <div className="flex flex-wrap items-center gap-2">
                      {canSuspend && (
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedServiceId(service.id);
                            setIsSuspendModalOpen(true);
                          }}
                          className="flex h-8 items-center gap-1.5 border border-orange-500/30 bg-orange-500/10 px-3 text-xs font-semibold text-orange-400 hover:bg-orange-500/20"
                        >
                          <PauseCircle className="size-3.5" />
                          Suspend Service
                        </button>
                      )}

                      {canRestore && (
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedServiceId(service.id);
                            setIsRestoreModalOpen(true);
                          }}
                          className="flex h-8 items-center gap-1.5 border border-green-500/30 bg-green-500/10 px-3 text-xs font-semibold text-green-400 hover:bg-green-500/20"
                        >
                          <PlayCircle className="size-3.5" />
                          Restore Service
                        </button>
                      )}

                      {canChangePlan && (
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedServiceId(service.id);
                            setTargetPackageId(service.internet_package.id);
                            setIsChangePackageModalOpen(true);
                          }}
                          className="flex h-8 items-center gap-1.5 border border-blue-500/30 bg-blue-500/10 px-3 text-xs font-semibold text-blue-400 hover:bg-blue-500/20"
                        >
                          <Package className="size-3.5" />
                          Change Plan
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Service Cards Grid */}
                  <div className="grid grid-cols-1 divide-y divide-[var(--border)] lg:grid-cols-2 lg:divide-x lg:divide-y-0">
                    {/* Left: Internet Package & Plan Specs */}
                    <div className="p-6">
                      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-blue-400">
                        <Package className="size-4" />
                        <span>Subscribed Internet Package</span>
                      </div>

                      <div className="mt-4 rounded-md border border-[var(--border)] bg-[var(--background)] p-4">
                        <div className="flex items-baseline justify-between">
                          <h4 className="text-base font-bold text-white">
                            {service.internet_package.name}
                          </h4>
                          <span className="font-mono text-sm font-semibold text-emerald-400">
                            {formatMoney(service.internet_package.monthly_price)} / mo
                          </span>
                        </div>

                        <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
                          <div className="border-t border-[var(--border)] pt-2">
                            <span className="text-[10px] uppercase tracking-wider text-[var(--text-muted)]">Download Speed</span>
                            <p className="font-mono font-bold text-white">{service.internet_package.download_speed_mbps} Mbps</p>
                          </div>
                          <div className="border-t border-[var(--border)] pt-2">
                            <span className="text-[10px] uppercase tracking-wider text-[var(--text-muted)]">Upload Speed</span>
                            <p className="font-mono font-bold text-white">{service.internet_package.upload_speed_mbps} Mbps</p>
                          </div>
                          <div className="border-t border-[var(--border)] pt-2">
                            <span className="text-[10px] uppercase tracking-wider text-[var(--text-muted)]">Package Code</span>
                            <p className="font-mono text-slate-300">{service.internet_package.code}</p>
                          </div>
                          <div className="border-t border-[var(--border)] pt-2">
                            <span className="text-[10px] uppercase tracking-wider text-[var(--text-muted)]">Activated On</span>
                            <p className="text-slate-300">{formatDate(service.activated_at)}</p>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Right: Network & Provisioning Context */}
                    <div className="p-6">
                      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-indigo-400">
                        <Network className="size-4" />
                        <span>Network Node & Provisioning</span>
                      </div>

                      {netAssign ? (
                        <div className="mt-4 rounded-md border border-[var(--border)] bg-[var(--background)] p-4">
                          <div className="flex items-baseline justify-between">
                            <div>
                              <h4 className="text-sm font-bold text-white">{netAssign.network_node_name}</h4>
                              <p className="font-mono text-xs text-blue-400">{netAssign.network_node_code}</p>
                            </div>
                            <span className="border border-indigo-500/20 bg-indigo-500/10 px-2 py-0.5 text-[10px] font-semibold text-indigo-400">
                              Assigned Node
                            </span>
                          </div>

                          <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
                            <div className="border-t border-[var(--border)] pt-2">
                              <span className="text-[10px] uppercase tracking-wider text-[var(--text-muted)]">PPPoE / IP Username</span>
                              <p className="font-mono text-white">{netAssign.username || "Automatic / DHCP"}</p>
                            </div>
                            <div className="border-t border-[var(--border)] pt-2">
                              <span className="text-[10px] uppercase tracking-wider text-[var(--text-muted)]">Assigned IP</span>
                              <p className="font-mono text-white">{netAssign.ip_address || "Dynamic Pool"}</p>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="mt-4 p-4 text-center text-xs text-[var(--text-muted)]">
                          No network assignment attached to this service.
                        </div>
                      )}

                      {/* Safe Provisioning Notice */}
                      <div className="mt-4 rounded border border-blue-500/20 bg-blue-500/5 p-3 text-xs text-slate-300">
                        <p className="font-semibold text-blue-400">Safe Provisioning Provider (STUB)</p>
                        <p className="mt-1 text-[11px] text-slate-400">
                          Network lifecycle actions execute against the development stub state machine without modifying live external routers or OLTs.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* TAB 2: Hardware & Inventory Devices */}
      {activeTab === "devices" && (
        <div className="mt-6 border border-[var(--border)] bg-[var(--surface)] p-6">
          <div className="flex items-center justify-between border-b border-[var(--border)] pb-4">
            <div>
              <h3 className="text-sm font-bold uppercase tracking-wider text-white">
                Assigned Customer Premises Equipment (CPE)
              </h3>
              <p className="mt-0.5 text-xs text-[var(--text-muted)]">
                Manage ONU/ONT routers and hardware serialized custody.
              </p>
            </div>

            {primaryService && (
              <button
                type="button"
                onClick={() => setIsAssignDeviceModalOpen(true)}
                className="flex h-8 items-center gap-1.5 bg-blue-600 px-3 text-xs font-semibold text-white hover:bg-blue-500"
              >
                <Plus className="size-3.5" />
                Assign Device
              </button>
            )}
          </div>

          <div className="mt-4">
            {!primaryService || primaryService.device_assignments.length === 0 ? (
              <EmptyState
                title="No Hardware Devices Assigned"
                description="There are currently no serialized inventory devices assigned to this customer's service connection."
                actionLabel="Assign Available Device"
                onActionClick={() => setIsAssignDeviceModalOpen(true)}
              />
            ) : (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {primaryService.device_assignments.map((assignment) => (
                  <div key={assignment.id} className="border border-[var(--border)] bg-[var(--background)] p-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <span className="font-mono text-sm font-bold text-white">{assignment.asset_tag}</span>
                        <p className="text-xs text-blue-400">{assignment.device_type}</p>
                      </div>
                      <span className={`border px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider ${
                        assignment.is_active
                          ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                          : "border-slate-700 bg-slate-800 text-slate-400"
                      }`}>
                        {assignment.is_active ? "In Custody" : "Returned"}
                      </span>
                    </div>

                    <div className="mt-3 space-y-1.5 text-xs">
                      <div className="flex justify-between text-slate-400">
                        <span>Status:</span>
                        <span className="font-semibold text-white">{assignment.device_status}</span>
                      </div>
                      <div className="flex justify-between text-slate-400">
                        <span>Assigned At:</span>
                        <span className="text-slate-300">{formatDate(assignment.assigned_at)}</span>
                      </div>
                      {assignment.returned_at && (
                        <div className="flex justify-between text-slate-400">
                          <span>Returned At:</span>
                          <span className="text-slate-300">{formatDate(assignment.returned_at)}</span>
                        </div>
                      )}
                    </div>

                    {assignment.is_active && (
                      <div className="mt-4 border-t border-[var(--border)] pt-3">
                        <button
                          type="button"
                          onClick={() => setIsReturnDeviceModalOpen(assignment.id)}
                          className="w-full border border-red-500/30 bg-red-500/10 py-1.5 text-xs font-semibold text-red-400 hover:bg-red-500/20"
                        >
                          Return & Unassign Device
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: Billing & Invoices */}
      {activeTab === "billing" && (
        <div className="mt-6 space-y-6">
          {/* Financial Summary & Quick Action Card */}
          <div className="border border-[var(--border)] bg-[var(--surface)] p-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-[var(--border)] pb-4">
              <div>
                <h3 className="text-base font-bold text-white">Subscriber Financial Overview</h3>
                <p className="text-xs text-[var(--text-muted)]">
                  Live ledger reconciliation, invoice debits, payment credits, and outstanding liability.
                </p>
              </div>

              <button
                type="button"
                onClick={() => {
                  if (customer.service_accounts.length > 0) {
                    setSelectedServiceId(customer.service_accounts[0].id);
                    const outstanding = ledger?.closing_balance || "0.00";
                    setCollectPayAmount(Number(outstanding) > 0 ? outstanding : "");
                  }
                  setIsCollectPaymentOpen(true);
                }}
                className="flex h-9 items-center gap-1.5 bg-emerald-600 px-4 text-xs font-semibold text-white hover:bg-emerald-500"
              >
                <CreditCard className="size-4" />
                Collect Payment
              </button>
            </div>

            <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="border border-[var(--border)] bg-[var(--background)] p-4">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Total Invoiced (Debits)
                </span>
                <p className="mt-1 font-mono text-lg font-bold text-white">
                  {formatMoney(ledger?.total_debit || "0.00")}
                </p>
                <span className="text-[10px] text-[var(--text-muted)]">{invoices.length} total invoices</span>
              </div>

              <div className="border border-[var(--border)] bg-[var(--background)] p-4">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-emerald-400">
                  Total Collected (Credits)
                </span>
                <p className="mt-1 font-mono text-lg font-bold text-emerald-400">
                  {formatMoney(ledger?.total_credit || "0.00")}
                </p>
                <span className="text-[10px] text-emerald-500/80">{payments.filter((p) => !p.is_reversed).length} payments</span>
              </div>

              <div className="border border-[var(--border)] bg-[var(--background)] p-4">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-amber-400">
                  Current Balance Due
                </span>
                <p className="mt-1 font-mono text-lg font-bold text-amber-400">
                  {formatMoney(ledger?.closing_balance || "0.00")}
                </p>
                <span className="text-[10px] text-amber-500/80">Net account position</span>
              </div>
            </div>
          </div>

          {/* Billing Profile Settings Card */}
          {primaryService?.billing_profile && (
            <div className="border border-[var(--border)] bg-[var(--surface)] p-6">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-blue-400">
                Subscriber Billing Settings
              </h3>
              <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div className="border border-[var(--border)] bg-[var(--background)] p-3">
                  <span className="text-[10px] uppercase text-[var(--text-muted)]">Billing Cycle</span>
                  <p className="mt-1 font-semibold text-white">{primaryService.billing_profile.billing_cycle}</p>
                </div>
                <div className="border border-[var(--border)] bg-[var(--background)] p-3">
                  <span className="text-[10px] uppercase text-[var(--text-muted)]">Invoice Generation Day</span>
                  <p className="mt-1 font-semibold text-white">Day {primaryService.billing_profile.billing_day} of month</p>
                </div>
                <div className="border border-[var(--border)] bg-[var(--background)] p-3">
                  <span className="text-[10px] uppercase text-[var(--text-muted)]">Payment Due Day</span>
                  <p className="mt-1 font-semibold text-white">Day {primaryService.billing_profile.due_day} of month</p>
                </div>
                <div className="border border-[var(--border)] bg-[var(--background)] p-3">
                  <span className="text-[10px] uppercase text-[var(--text-muted)]">Profile Status</span>
                  <p className="mt-1 font-semibold text-emerald-400">
                    {primaryService.billing_profile.is_active ? "Active Profile" : "Inactive"}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Unified Customer Financial Ledger */}
          <div className="border border-[var(--border)] bg-[var(--surface)] p-6">
            <h3 className="text-sm font-bold uppercase tracking-wider text-white">
              Customer Financial Statement (Ledger)
            </h3>
            <p className="mt-0.5 text-xs text-[var(--text-muted)]">
              Chronological ledger tracking invoices, payments, reversals, and running account balance.
            </p>

            <div className="mt-4">
              {!ledger || ledger.entries.length === 0 ? (
                <EmptyState
                  title="No Ledger Transactions"
                  description="No financial ledger entries have been recorded for this subscriber account yet."
                />
              ) : (
                <div className="overflow-x-auto border border-[var(--border)]">
                  <table className="w-full min-w-[800px] border-collapse text-left text-xs">
                    <thead>
                      <tr className="border-b border-[var(--border)] bg-white/[0.02] text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                        <th className="p-3">Date</th>
                        <th className="p-3">Reference #</th>
                        <th className="p-3">Description</th>
                        <th className="p-3 text-right">Debit (Invoice)</th>
                        <th className="p-3 text-right">Credit (Payment)</th>
                        <th className="p-3 text-right">Running Balance</th>
                        <th className="p-3 text-center">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--border)]">
                      {ledger.entries.map((entry, idx) => (
                        <tr key={idx} className="hover:bg-white/[0.02]">
                          <td className="p-3 text-zinc-300">{formatDate(entry.date)}</td>
                          <td className="p-3 font-mono font-semibold text-blue-400">{entry.reference}</td>
                          <td className="p-3 text-white">{entry.description}</td>
                          <td className="p-3 text-right font-mono text-white">
                            {Number(entry.debit) > 0 ? formatMoney(entry.debit) : "—"}
                          </td>
                          <td className="p-3 text-right font-mono text-emerald-400">
                            {Number(entry.credit) > 0 ? formatMoney(entry.credit) : "—"}
                          </td>
                          <td className="p-3 text-right font-mono font-bold text-amber-400">
                            {formatMoney(entry.balance)}
                          </td>
                          <td className="p-3 text-center">
                            <span className="border border-[var(--border)] bg-[var(--background)] px-2 py-0.5 text-[9px] font-bold uppercase text-[var(--text-muted)]">
                              {entry.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* Invoices List */}
          <div className="border border-[var(--border)] bg-[var(--surface)] p-6">
            <h3 className="text-sm font-bold uppercase tracking-wider text-white">
              Billing & Invoices History
            </h3>
            <p className="mt-0.5 text-xs text-[var(--text-muted)]">
              Itemized billing invoices issued for this customer account.
            </p>

            <div className="mt-4">
              {invoices.length === 0 ? (
                <EmptyState
                  title="No Invoices Found"
                  description="There are no billing invoices on record for this customer account."
                />
              ) : (
                <div className="overflow-x-auto border border-[var(--border)]">
                  <table className="w-full min-w-[700px] border-collapse text-left text-xs">
                    <thead>
                      <tr className="border-b border-[var(--border)] bg-white/[0.02] text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                        <th className="p-3">Invoice Number</th>
                        <th className="p-3">Billing Period</th>
                        <th className="p-3">Due Date</th>
                        <th className="p-3 text-right">Total Amount</th>
                        <th className="p-3 text-right">Paid Amount</th>
                        <th className="p-3 text-right">Outstanding</th>
                        <th className="p-3">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--border)]">
                      {invoices.map((inv) => (
                        <tr key={inv.id} className="hover:bg-white/[0.02]">
                          <td className="p-3 font-mono font-semibold text-blue-400">{inv.invoice_number}</td>
                          <td className="p-3 text-slate-300">{formatDate(inv.billing_period_start)} — {formatDate(inv.billing_period_end)}</td>
                          <td className="p-3 text-slate-300">{formatDate(inv.due_date)}</td>
                          <td className="p-3 text-right font-mono font-bold text-white">{formatMoney(inv.total_amount)}</td>
                          <td className="p-3 text-right font-mono text-emerald-400">{formatMoney(inv.paid_amount)}</td>
                          <td className="p-3 text-right font-mono font-bold text-amber-400">{formatMoney(inv.outstanding_amount)}</td>
                          <td className="p-3">
                            <span className={`border px-2 py-0.5 text-[9px] font-bold uppercase ${
                              inv.status === "PAID"
                                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                                : inv.status === "PARTIALLY_PAID"
                                ? "border-amber-500/30 bg-amber-500/10 text-amber-400"
                                : inv.status === "CANCELLED"
                                ? "border-zinc-500/30 bg-zinc-500/10 text-zinc-400"
                                : "border-rose-500/30 bg-rose-500/10 text-rose-400"
                            }`}>
                              {inv.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* Payments & Receipts List */}
          <div className="border border-[var(--border)] bg-[var(--surface)] p-6">
            <h3 className="text-sm font-bold uppercase tracking-wider text-white">
              Payments & Receipts History
            </h3>
            <p className="mt-0.5 text-xs text-[var(--text-muted)]">
              Collections recorded against this subscriber account.
            </p>

            <div className="mt-4">
              {payments.length === 0 ? (
                <EmptyState
                  title="No Payments Recorded"
                  description="No payment collections have been recorded for this subscriber yet."
                />
              ) : (
                <div className="overflow-x-auto border border-[var(--border)]">
                  <table className="w-full min-w-[700px] border-collapse text-left text-xs">
                    <thead>
                      <tr className="border-b border-[var(--border)] bg-white/[0.02] text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                        <th className="p-3">Receipt / Payment #</th>
                        <th className="p-3">Date</th>
                        <th className="p-3">Method</th>
                        <th className="p-3">Reference</th>
                        <th className="p-3 text-right">Amount</th>
                        <th className="p-3">Status</th>
                        <th className="p-3 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--border)]">
                      {payments.map((pay) => (
                        <tr key={pay.id} className="hover:bg-white/[0.02]">
                          <td className="p-3 font-mono font-semibold text-emerald-400">{pay.payment_number}</td>
                          <td className="p-3 text-slate-300">{formatDate(pay.paid_at)}</td>
                          <td className="p-3 text-white">{pay.payment_method}</td>
                          <td className="p-3 font-mono text-[11px] text-[var(--text-muted)]">{pay.reference || "—"}</td>
                          <td className="p-3 text-right font-mono font-bold text-white">{formatMoney(pay.amount)}</td>
                          <td className="p-3">
                            {pay.is_reversed ? (
                              <span className="border border-rose-500/30 bg-rose-500/10 px-2 py-0.5 text-[9px] font-bold uppercase text-rose-400">
                                Reversed
                              </span>
                            ) : (
                              <span className="border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[9px] font-bold uppercase text-emerald-400">
                                Active
                              </span>
                            )}
                          </td>
                          <td className="p-3 text-right">
                            <button
                              type="button"
                              onClick={async () => {
                                try {
                                  setReceiptLoading(true);
                                  setIsReceiptModalOpen(true);
                                  const r = await billingService.getReceipt(pay.id);
                                  setSelectedReceipt(r);
                                } catch {
                                  toast.error("Failed to load receipt.");
                                  setIsReceiptModalOpen(false);
                                } finally {
                                  setReceiptLoading(false);
                                }
                              }}
                              className="border border-[var(--border)] bg-[var(--background)] px-2.5 py-1 text-[10px] font-semibold text-emerald-400 hover:text-emerald-300"
                            >
                              Receipt
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: Support Tickets & Maintenance */}
      {activeTab === "support" && (
        <div className="mt-6 border border-[var(--border)] bg-[var(--surface)] p-6">
          <div className="flex items-center justify-between border-b border-[var(--border)] pb-4">
            <div>
              <h3 className="text-sm font-bold uppercase tracking-wider text-white">
                Customer Support Tickets & Maintenance
              </h3>
              <p className="mt-0.5 text-xs text-[var(--text-muted)]">
                Active complaints, SLA targets, assigned field technicians, and resolution logs.
              </p>
            </div>

            <Link
              href="/support"
              className="flex h-8 items-center gap-1.5 border border-blue-500/30 bg-blue-500/10 px-3 text-xs font-semibold text-blue-400 hover:bg-blue-500/20"
            >
              Open Helpdesk
              <ArrowRight className="size-3.5" />
            </Link>
          </div>

          <div className="mt-4">
            {complaints.length === 0 ? (
              <EmptyState
                title="No Support Complaints"
                description="There are no active or historical support tickets recorded for this customer."
              />
            ) : (
              <div className="space-y-3">
                {complaints.map((comp) => (
                  <div key={comp.id} className="border border-[var(--border)] bg-[var(--background)] p-4 transition-all hover:border-[#303E55]">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-blue-400">{comp.complaint_number}</span>
                          <span className={`border px-1.5 py-0.2 text-[9px] font-bold uppercase ${
                            comp.priority === "CRITICAL"
                              ? "border-rose-500/30 bg-rose-500/10 text-rose-400"
                              : comp.priority === "HIGH"
                              ? "border-amber-500/30 bg-amber-500/10 text-amber-400"
                              : "border-blue-500/30 bg-blue-500/10 text-blue-400"
                          }`}>
                            {comp.priority}
                          </span>
                        </div>
                        <h4 className="mt-1 text-sm font-semibold text-white">{comp.subject}</h4>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className={`border px-2 py-0.5 text-[9px] font-bold uppercase ${
                          comp.status === "OPEN" || comp.status === "NEW"
                            ? "border-blue-500/30 bg-blue-500/10 text-blue-400"
                            : comp.status === "ASSIGNED"
                            ? "border-indigo-500/30 bg-indigo-500/10 text-indigo-400"
                            : comp.status === "IN_PROGRESS"
                            ? "border-amber-500/30 bg-amber-500/10 text-amber-400"
                            : comp.status === "ESCALATED"
                            ? "border-rose-500/30 bg-rose-500/15 text-rose-400 font-bold"
                            : comp.status === "RESOLVED"
                            ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                            : "border-slate-700 bg-slate-800 text-slate-400"
                        }`}>
                          {comp.status}
                        </span>
                      </div>
                    </div>

                    <p className="mt-2 text-xs leading-relaxed text-slate-300">{comp.description}</p>

                    {comp.resolution_summary && (
                      <div className="mt-3 rounded border border-emerald-500/20 bg-emerald-500/5 p-2.5 text-xs text-emerald-300">
                        <span className="font-semibold text-emerald-400">Resolution ({comp.diagnosis_category || "Technical Fix"}):</span>{" "}
                        {comp.resolution_summary}
                      </div>
                    )}

                    <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-[var(--border)] pt-2 text-[10px] text-[var(--text-muted)]">
                      <span>Category: {comp.category.replace(/_/g, " ")} {comp.service_number ? `• Service: ${comp.service_number}` : ""}</span>
                      <div className="flex items-center gap-3">
                        {comp.assigned_to_name && <span>Assigned: <strong className="text-slate-300">{comp.assigned_to_name}</strong></span>}
                        <span>Created: {formatDate(comp.created_at)}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 5: Profile & Contact Details */}
      {activeTab === "profile" && (
        <div className="mt-6 border border-[var(--border)] bg-[var(--surface)] p-6">
          <div className="flex items-center justify-between border-b border-[var(--border)] pb-4">
            <div>
              <h3 className="text-sm font-bold uppercase tracking-wider text-white">
                Subscriber Profile Information
              </h3>
              <p className="mt-0.5 text-xs text-[var(--text-muted)]">
                Personal identity, primary contact, and service installation address.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setIsEditModalOpen(true)}
              className="flex h-8 items-center gap-1.5 bg-blue-600 px-3 text-xs font-semibold text-white hover:bg-blue-500"
            >
              <Edit className="size-3.5" />
              Edit Information
            </button>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-2">
            <div>
              <span className="text-[10px] font-semibold uppercase text-[var(--text-muted)]">Customer Number</span>
              <p className="font-mono text-sm font-bold text-white">{customer.customer_number}</p>
            </div>
            <div>
              <span className="text-[10px] font-semibold uppercase text-[var(--text-muted)]">Full Name</span>
              <p className="text-sm font-semibold text-white">{customer.full_name}</p>
            </div>
            <div>
              <span className="text-[10px] font-semibold uppercase text-[var(--text-muted)]">Primary Phone</span>
              <p className="text-sm font-semibold text-white">{customer.phone}</p>
            </div>
            <div>
              <span className="text-[10px] font-semibold uppercase text-[var(--text-muted)]">Alternate Phone</span>
              <p className="text-sm font-semibold text-slate-300">{customer.alternate_phone || "Not provided"}</p>
            </div>
            <div>
              <span className="text-[10px] font-semibold uppercase text-[var(--text-muted)]">Email Address</span>
              <p className="text-sm font-semibold text-slate-300">{customer.email || "Not provided"}</p>
            </div>
            <div>
              <span className="text-[10px] font-semibold uppercase text-[var(--text-muted)]">Operating Region</span>
              <p className="text-sm font-semibold text-white">{customer.city} {customer.area ? `— ${customer.area}` : ""}</p>
            </div>
            <div className="md:col-span-2">
              <span className="text-[10px] font-semibold uppercase text-[var(--text-muted)]">Full Installation Address</span>
              <p className="text-sm font-semibold text-white">{customer.address_line}</p>
            </div>
            <div>
              <span className="text-[10px] font-semibold uppercase text-[var(--text-muted)]">WhatsApp Notifications</span>
              <p className="text-xs font-semibold text-emerald-400">
                {customer.notification_preference?.whatsapp_enabled ? "Enabled" : "Disabled"}
              </p>
            </div>
            <div>
              <span className="text-[10px] font-semibold uppercase text-[var(--text-muted)]">SMS Notifications</span>
              <p className="text-xs font-semibold text-emerald-400">
                {customer.notification_preference?.sms_enabled ? "Enabled" : "Disabled"}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ==================== MODALS ==================== */}

      {/* Modal: Edit Customer Profile */}
      {isEditModalOpen && (
        <EditCustomerModal
          customer={customer}
          onClose={() => setIsEditModalOpen(false)}
          onSuccess={async (updated) => {
            setCustomer(updated);
            setIsEditModalOpen(false);
            toast.success("Customer profile updated successfully.");
          }}
        />
      )}

      {/* Modal: Suspend Service */}
      {isSuspendModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md border border-[var(--border)] bg-[var(--surface)] p-6">
            <h3 className="text-base font-bold text-white">Confirm Service Suspension</h3>
            <p className="mt-2 text-xs text-slate-300">
              Are you sure you want to request suspension for service account{" "}
              <strong className="text-orange-400">{primaryService?.service_number}</strong>?
            </p>
            <p className="mt-2 text-[11px] text-[var(--text-muted)]">
              This creates a backend provisioning request and marks the service status as Suspension Pending.
            </p>

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setIsSuspendModalOpen(false)}
                className="border border-[var(--border)] px-4 py-2 text-xs font-medium text-slate-300 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSuspendService}
                disabled={actionLoading}
                className="flex items-center gap-1.5 bg-orange-600 px-4 py-2 text-xs font-semibold text-white hover:bg-orange-500 disabled:opacity-50"
              >
                {actionLoading && <Loader2 className="size-3.5 animate-spin" />}
                Confirm Suspension
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Restore Service */}
      {isRestoreModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md border border-[var(--border)] bg-[var(--surface)] p-6">
            <h3 className="text-base font-bold text-white">Confirm Service Restoration</h3>
            <p className="mt-2 text-xs text-slate-300">
              Request restoration of service connection{" "}
              <strong className="text-green-400">{primaryService?.service_number}</strong>?
            </p>
            <p className="mt-2 text-[11px] text-[var(--text-muted)]">
              This creates a backend restore provisioning request and marks the status as Restore Pending.
            </p>

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setIsRestoreModalOpen(false)}
                className="border border-[var(--border)] px-4 py-2 text-xs font-medium text-slate-300 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleRestoreService}
                disabled={actionLoading}
                className="flex items-center gap-1.5 bg-green-600 px-4 py-2 text-xs font-semibold text-white hover:bg-green-500 disabled:opacity-50"
              >
                {actionLoading && <Loader2 className="size-3.5 animate-spin" />}
                Confirm Restoration
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Change Package */}
      {isChangePackageModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-lg border border-[var(--border)] bg-[var(--surface)] p-6">
            <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
              <h3 className="text-base font-bold text-white">Change Internet Package</h3>
              <button type="button" onClick={() => setIsChangePackageModalOpen(false)} className="text-[var(--text-muted)] hover:text-white">
                <X className="size-4" />
              </button>
            </div>

            <p className="mt-3 text-xs text-[var(--text-muted)]">
              Select the new broadband tier from your active Internet Packages catalogue:
            </p>

            <div className="mt-4 max-h-60 space-y-2 overflow-y-auto">
              {packages.map((pkg) => (
                <label
                  key={pkg.id}
                  className={`flex cursor-pointer items-center justify-between border p-3 transition-colors ${
                    targetPackageId === pkg.id
                      ? "border-blue-500 bg-blue-500/10"
                      : "border-[var(--border)] bg-[var(--background)] hover:border-slate-600"
                  }`}
                >
                  <div>
                    <input
                      type="radio"
                      name="packageSelect"
                      value={pkg.id}
                      checked={targetPackageId === pkg.id}
                      onChange={() => setTargetPackageId(pkg.id)}
                      className="hidden"
                    />
                    <p className="text-xs font-bold text-white">{pkg.name}</p>
                    <p className="text-[10px] text-[var(--text-muted)]">{pkg.download_speed_mbps} Mbps Down / {pkg.upload_speed_mbps} Mbps Up</p>
                  </div>
                  <span className="font-mono text-xs font-semibold text-blue-400">
                    {formatMoney(pkg.monthly_price)}
                  </span>
                </label>
              ))}
            </div>

            <div className="mt-6 flex justify-end gap-3 border-t border-[var(--border)] pt-4">
              <button
                type="button"
                onClick={() => setIsChangePackageModalOpen(false)}
                className="border border-[var(--border)] px-4 py-2 text-xs font-medium text-slate-300 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleChangePackage}
                disabled={actionLoading || targetPackageId === primaryService?.internet_package.id}
                className="flex items-center gap-1.5 bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
              >
                {actionLoading && <Loader2 className="size-3.5 animate-spin" />}
                Confirm Plan Change
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Assign Device */}
      {isAssignDeviceModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-lg border border-[var(--border)] bg-[var(--surface)] p-6">
            <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
              <h3 className="text-base font-bold text-white">Assign Serialized Hardware (CPE)</h3>
              <button type="button" onClick={() => setIsAssignDeviceModalOpen(false)} className="text-[var(--text-muted)] hover:text-white">
                <X className="size-4" />
              </button>
            </div>

            <div className="mt-4 space-y-4">
              <div>
                <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Select Available Device *
                </label>
                {availableDevices.length === 0 ? (
                  <p className="border border-[var(--border)] bg-[var(--background)] p-3 text-xs text-amber-400">
                    No AVAILABLE devices found in Inventory. Please create or return a device first.
                  </p>
                ) : (
                  <select
                    value={selectedDeviceId}
                    onChange={(e) => setSelectedDeviceId(e.target.value)}
                    className="h-10 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white outline-none focus:border-blue-500"
                  >
                    <option value="">Select Hardware Device...</option>
                    {availableDevices.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.asset_tag} — {d.device_type} ({d.manufacturer} {d.model_name}) [SN: {d.serial_number}]
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div>
                <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Assignment Custody Notes
                </label>
                <input
                  value={deviceNotes}
                  onChange={(e) => setDeviceNotes(e.target.value)}
                  placeholder="e.g. Installed in customer premises on Ground Floor"
                  className="h-10 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white outline-none focus:border-blue-500"
                />
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3 border-t border-[var(--border)] pt-4">
              <button
                type="button"
                onClick={() => setIsAssignDeviceModalOpen(false)}
                className="border border-[var(--border)] px-4 py-2 text-xs font-medium text-slate-300 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleAssignDevice}
                disabled={actionLoading || !selectedDeviceId}
                className="flex items-center gap-1.5 bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
              >
                {actionLoading && <Loader2 className="size-3.5 animate-spin" />}
                Assign Device
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Return Device */}
      {Boolean(isReturnDeviceModalOpen) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md border border-[var(--border)] bg-[var(--surface)] p-6">
            <h3 className="text-base font-bold text-white">Return & Unassign Device</h3>
            <p className="mt-2 text-xs text-slate-300">
              Record device return into inventory stock.
            </p>

            <div className="mt-4 space-y-4">
              <div>
                <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Return Condition *
                </label>
                <select
                  value={returnCondition}
                  onChange={(e) => setReturnCondition(e.target.value as ReturnCondition)}
                  className="h-10 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white outline-none focus:border-blue-500"
                >
                  <option value="GOOD">GOOD (Ready for immediate reassignment)</option>
                  <option value="DAMAGED">DAMAGED (Requires maintenance)</option>
                  <option value="FAULTY">FAULTY (Hardware malfunction)</option>
                </select>
              </div>

              <div>
                <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Return Notes
                </label>
                <input
                  value={returnNotes}
                  onChange={(e) => setReturnNotes(e.target.value)}
                  placeholder="Optional return inspection notes"
                  className="h-10 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white outline-none focus:border-blue-500"
                />
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3 border-t border-[var(--border)] pt-4">
              <button
                type="button"
                onClick={() => setIsReturnDeviceModalOpen(null)}
                className="border border-[var(--border)] px-4 py-2 text-xs font-medium text-slate-300 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleReturnDevice}
                disabled={actionLoading}
                className="flex items-center gap-1.5 bg-red-600 px-4 py-2 text-xs font-semibold text-white hover:bg-red-500 disabled:opacity-50"
              >
                {actionLoading && <Loader2 className="size-3.5 animate-spin" />}
                Confirm Return
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Collect Payment */}
      {isCollectPaymentOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md border border-[var(--border)] bg-[var(--surface)] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
              <h3 className="text-base font-bold text-white">Collect Subscriber Payment</h3>
              <button
                type="button"
                onClick={() => setIsCollectPaymentOpen(false)}
                className="text-[var(--text-muted)] hover:text-white"
              >
                <X className="size-4" />
              </button>
            </div>

            <form
              onSubmit={async (e) => {
                e.preventDefault();
                if (!selectedServiceId) {
                  toast.error("Please select a service account.");
                  return;
                }
                try {
                  setActionLoading(true);
                  await billingService.recordPaymentWithAllocations({
                    service_account_id: selectedServiceId,
                    amount: collectPayAmount,
                    payment_method: collectPayMethod,
                    reference: collectPayRef.trim(),
                    notes: collectPayNotes.trim(),
                  });
                  toast.success("Payment recorded successfully.");
                  setIsCollectPaymentOpen(false);
                  setCollectPayAmount("");
                  setCollectPayRef("");
                  setCollectPayNotes("");
                  await loadCustomerData();
                } catch (err) {
                  toast.error(err instanceof Error ? err.message : "Payment recording failed");
                } finally {
                  setActionLoading(false);
                }
              }}
              className="mt-4 space-y-4"
            >
              <div>
                <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Service Connection *
                </label>
                <select
                  value={selectedServiceId}
                  onChange={(e) => setSelectedServiceId(e.target.value)}
                  className="h-10 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white outline-none focus:border-blue-500"
                >
                  {customer.service_accounts.map((svc) => (
                    <option key={svc.id} value={svc.id}>
                      {svc.service_number} ({svc.internet_package.name})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                    Payment Amount (PKR) *
                  </label>
                  {ledger && (
                    <span className="font-mono text-[10px] text-slate-400">
                      Balance Due: <strong className="text-amber-400">{formatMoney(ledger.closing_balance)}</strong>
                    </span>
                  )}
                </div>

                <input
                  type="number"
                  step="0.01"
                  required
                  value={collectPayAmount}
                  onChange={(e) => setCollectPayAmount(e.target.value)}
                  placeholder="0.00"
                  className="h-10 w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 font-mono text-sm text-white outline-none focus:border-emerald-500"
                />

                {/* Quick Amount Suggestion Chips */}
                {(() => {
                  const outstanding = Number(ledger?.closing_balance) || 0;
                  const latestUnpaid = Number(invoices.find((i) => i.status !== "PAID")?.total_amount) || 0;

                  return (
                    <div className="mt-2 flex flex-wrap items-center gap-1.5">
                      <span className="text-[10px] text-slate-500 mr-1">Quick:</span>
                      {outstanding > 0 && (
                        <button
                          type="button"
                          onClick={() => setCollectPayAmount(outstanding.toFixed(2))}
                          className="rounded border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-300 hover:bg-emerald-500/20 transition"
                        >
                          Full Due (Rs. {outstanding.toLocaleString()})
                        </button>
                      )}
                      {outstanding > 0 && (
                        <button
                          type="button"
                          onClick={() => setCollectPayAmount((outstanding / 2).toFixed(2))}
                          className="rounded border border-blue-500/30 bg-blue-500/10 px-2 py-0.5 text-[10px] font-semibold text-blue-300 hover:bg-blue-500/20 transition"
                        >
                          50% Due (Rs. {(outstanding / 2).toLocaleString()})
                        </button>
                      )}
                      {latestUnpaid > 0 && latestUnpaid !== outstanding && (
                        <button
                          type="button"
                          onClick={() => setCollectPayAmount(latestUnpaid.toFixed(2))}
                          className="rounded border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold text-amber-300 hover:bg-amber-500/20 transition"
                        >
                          Current Bill (Rs. {latestUnpaid.toLocaleString()})
                        </button>
                      )}
                    </div>
                  );
                })()}
              </div>

              <div>
                <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Payment Method *
                </label>
                <select
                  value={collectPayMethod}
                  onChange={(e) => setCollectPayMethod(e.target.value as PaymentMethod)}
                  className="h-10 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white outline-none focus:border-blue-500"
                >
                  <option value="CASH">Cash</option>
                  <option value="BANK_TRANSFER">Bank Transfer</option>
                  <option value="CARD">Debit / Credit Card</option>
                  <option value="MOBILE_WALLET">Mobile Wallet</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>

              <div>
                <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Reference # / Transaction ID
                </label>
                <input
                  value={collectPayRef}
                  onChange={(e) => setCollectPayRef(e.target.value)}
                  placeholder="e.g. Bank Ref #, JazzCash TID"
                  className="h-9 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex justify-end gap-2 border-t border-[var(--border)] pt-4">
                <button
                  type="button"
                  onClick={() => setIsCollectPaymentOpen(false)}
                  className="border border-[var(--border)] px-4 py-2 text-xs font-medium text-slate-300 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="flex items-center gap-1.5 bg-emerald-600 px-4 py-2 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
                >
                  {actionLoading && <Loader2 className="size-3.5 animate-spin" />}
                  Confirm Collection
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Receipt Viewer */}
      {isReceiptModalOpen && selectedReceipt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="relative w-full max-w-md border border-[var(--border)] bg-[var(--surface)] p-6 shadow-2xl">
            <button
              type="button"
              onClick={() => setIsReceiptModalOpen(false)}
              className="absolute right-4 top-4 text-[var(--text-muted)] hover:text-white"
            >
              <X className="size-4" />
            </button>

            <div className="space-y-4">
              <div className="border-b border-[var(--border)] pb-3 text-center">
                <span className="text-[10px] font-bold uppercase tracking-widest text-emerald-400">
                  Payment Receipt
                </span>
                <h3 className="mt-0.5 text-base font-bold text-white">{selectedReceipt.organization_name}</h3>
                <p className="font-mono text-xs text-[var(--text-muted)]">{selectedReceipt.payment_number}</p>
              </div>

              <div className="flex items-center justify-between border border-emerald-500/30 bg-emerald-500/10 p-3">
                <div>
                  <span className="text-[10px] font-bold uppercase text-emerald-300">Amount Paid</span>
                  <p className="text-xs text-[var(--text-muted)]">{selectedReceipt.payment_method}</p>
                </div>
                <span className="font-mono text-xl font-bold text-emerald-400">
                  {formatMoney(selectedReceipt.amount)}
                </span>
              </div>

              <div className="border border-[var(--border)] bg-[var(--background)] p-3 text-xs space-y-1">
                <div className="flex justify-between">
                  <span className="text-[var(--text-muted)]">Subscriber:</span>
                  <span className="font-semibold text-white">{selectedReceipt.customer.full_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--text-muted)]">Service Number:</span>
                  <span className="font-mono text-white">{selectedReceipt.service_number}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--text-muted)]">Payment Date:</span>
                  <span className="text-zinc-300">{formatDate(selectedReceipt.payment_date)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--text-muted)]">Collector:</span>
                  <span className="text-zinc-300">{selectedReceipt.received_by_name}</span>
                </div>
              </div>

              <div className="flex justify-between pt-2 border-t border-[var(--border)]">
                <button
                  type="button"
                  onClick={() => setIsReceiptModalOpen(false)}
                  className="border border-[var(--border)] px-4 py-1.5 text-xs text-slate-300 hover:text-white"
                >
                  Close
                </button>
                <button
                  type="button"
                  onClick={() => window.print()}
                  className="bg-emerald-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-emerald-500"
                >
                  Print
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function EditCustomerModal({
  customer,
  onClose,
  onSuccess,
}: {
  customer: CustomerDetail;
  onClose: () => void;
  onSuccess: (updated: CustomerDetail) => Promise<void>;
}) {
  const [form, setForm] = useState<CustomerUpdatePayload>({
    first_name: customer.first_name,
    last_name: customer.last_name,
    phone: customer.phone,
    alternate_phone: customer.alternate_phone,
    email: customer.email,
    address_line: customer.address_line,
    area: customer.area,
    city: customer.city,
    is_active: customer.is_active,
    sms_enabled: customer.notification_preference?.sms_enabled ?? true,
    whatsapp_enabled: customer.notification_preference?.whatsapp_enabled ?? true,
  });

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.first_name?.trim() || !form.phone?.trim() || !form.address_line?.trim() || !form.city?.trim()) {
      setError("First name, primary phone, address, and city are required.");
      return;
    }

    try {
      setSaving(true);
      setError(null);
      const updated = await customersService.updateCustomer(customer.id, form);
      await onSuccess(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update customer");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4">
      <div className="w-full max-w-2xl border border-[var(--border)] bg-[var(--surface)] p-6">
        <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
          <h3 className="text-base font-bold text-white">Edit Subscriber Profile</h3>
          <button type="button" onClick={onClose} className="text-[var(--text-muted)] hover:text-white">
            <X className="size-4" />
          </button>
        </div>

        {error && (
          <div className="mt-4 border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-400">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-[10px] font-semibold uppercase text-[var(--text-muted)]">
                First Name *
              </label>
              <input
                value={form.first_name || ""}
                onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                className="h-9 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-semibold uppercase text-[var(--text-muted)]">
                Last Name
              </label>
              <input
                value={form.last_name || ""}
                onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                className="h-9 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-semibold uppercase text-[var(--text-muted)]">
                Primary Phone *
              </label>
              <input
                value={form.phone || ""}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                className="h-9 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-semibold uppercase text-[var(--text-muted)]">
                Alternate Phone
              </label>
              <input
                value={form.alternate_phone || ""}
                onChange={(e) => setForm({ ...form, alternate_phone: e.target.value })}
                className="h-9 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-semibold uppercase text-[var(--text-muted)]">
                Email Address
              </label>
              <input
                type="email"
                value={form.email || ""}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="h-9 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-semibold uppercase text-[var(--text-muted)]">
                Operational City *
              </label>
              <input
                value={form.city || ""}
                onChange={(e) => setForm({ ...form, city: e.target.value })}
                className="h-9 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white outline-none focus:border-blue-500"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="mb-1 block text-[10px] font-semibold uppercase text-[var(--text-muted)]">
                Service Area
              </label>
              <input
                value={form.area || ""}
                onChange={(e) => setForm({ ...form, area: e.target.value })}
                className="h-9 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white outline-none focus:border-blue-500"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="mb-1 block text-[10px] font-semibold uppercase text-[var(--text-muted)]">
                Installation Address *
              </label>
              <input
                value={form.address_line || ""}
                onChange={(e) => setForm({ ...form, address_line: e.target.value })}
                className="h-9 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {/* Notification toggles */}
          <div className="grid grid-cols-2 gap-3 border-t border-[var(--border)] pt-4">
            <label className="flex items-center gap-2 text-xs text-slate-300">
              <input
                type="checkbox"
                checked={Boolean(form.whatsapp_enabled)}
                onChange={(e) => setForm({ ...form, whatsapp_enabled: e.target.checked })}
                className="size-4"
              />
              <span>WhatsApp Alerts</span>
            </label>
            <label className="flex items-center gap-2 text-xs text-slate-300">
              <input
                type="checkbox"
                checked={Boolean(form.sms_enabled)}
                onChange={(e) => setForm({ ...form, sms_enabled: e.target.checked })}
                className="size-4"
              />
              <span>SMS Alerts</span>
            </label>
          </div>

          <div className="flex justify-end gap-3 border-t border-[var(--border)] pt-4">
            <button
              type="button"
              onClick={onClose}
              className="border border-[var(--border)] px-4 py-2 text-xs font-medium text-slate-300 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-1.5 bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
            >
              {saving && <Loader2 className="size-3.5 animate-spin" />}
              Save Changes
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}