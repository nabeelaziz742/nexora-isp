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
  BellRing,
  CreditCard,
  Loader2,
  Network,
  Package,
  PauseCircle,
  RefreshCw,
  Router,
  UserRound,
  Wifi,
} from "lucide-react";

import {
  customersService,
  type CustomerDetail,
  type CustomerServiceAccount,
  type CustomerServiceStatus,
  type InternetPackage,
} from "@/services/customers.service";
import { networkService } from "@/services/network.service";

const serviceStatusStyles: Record<
  CustomerServiceStatus,
  string
> = {
  ACTIVE:
    "border-green-500/20 bg-green-500/10 text-green-400",
  GRACE_PERIOD:
    "border-amber-500/20 bg-amber-500/10 text-amber-400",
  SUSPENSION_PENDING:
    "border-orange-500/20 bg-orange-500/10 text-orange-400",
  SUSPENDED_NON_PAYMENT:
    "border-red-500/20 bg-red-500/10 text-red-400",
  RESTORE_PENDING:
    "border-blue-500/20 bg-blue-500/10 text-blue-400",
};

function formatStatus(
  status: CustomerServiceStatus,
) {
  return status.replaceAll("_", " ");
}

function formatMoney(value: string | number) {
  const amount = Number(value);

  if (Number.isNaN(amount)) {
    return String(value);
  }

  return `Rs. ${amount.toLocaleString()}`;
}

function formatDate(value: string | null) {
  if (!value) {
    return "Not available";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-PK", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

export default function CustomerDetailPage() {
  const params = useParams<{ id: string }>();
  const customerId = params.id;

  const [customer, setCustomer] =
    useState<CustomerDetail | null>(null);

  const [packages, setPackages] = useState<
    InternetPackage[]
  >([]);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState<
    string | null
  >(null);

  const loadCustomer = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [customerData, packageData] =
        await Promise.all([
          customersService.getCustomer(customerId),
          customersService.getInternetPackages(),
        ]);

      setCustomer(customerData);
      setPackages(packageData);
    } catch (requestError) {
      console.error(
        "Failed to load customer detail:",
        requestError,
      );

      setCustomer(null);

      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to load customer.",
      );
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    if (customerId) {
      void loadCustomer();
    }
  }, [customerId, loadCustomer]);

  if (loading) {
    return (
      <PageShell>
        <StatePanel message="Loading Customer 360..." />
      </PageShell>
    );
  }

  if (error) {
    return (
      <PageShell>
        <div className="flex min-h-72 items-center justify-center border border-red-500/20 bg-red-500/[0.04]">
          <div className="text-center">
            <p className="text-[12px] font-medium text-red-400">
              Unable to load customer
            </p>

            <p className="mt-2 max-w-md text-[10px] text-[var(--text-muted)]">
              {error}
            </p>
          </div>
        </div>
      </PageShell>
    );
  }

  if (!customer) {
    return (
      <PageShell>
        <StatePanel message="Customer was not found." />
      </PageShell>
    );
  }

  return (
    <PageShell>
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-2xl font-semibold tracking-tight text-white">
              {customer.full_name}
            </h2>

            <span
              className={`inline-flex border px-2 py-1 text-[9px] font-semibold uppercase tracking-wide ${
                customer.is_active
                  ? "border-green-500/20 bg-green-500/10 text-green-400"
                  : "border-red-500/20 bg-red-500/10 text-red-400"
              }`}
            >
              {customer.is_active
                ? "Active"
                : "Inactive"}
            </span>
          </div>

          <div className="mt-2 flex flex-wrap items-center gap-3 text-[10px] text-[var(--text-muted)]">
            <span className="text-blue-400">
              {customer.customer_number}
            </span>

            <span>{customer.phone}</span>

            <span>
              {[customer.area, customer.city]
                .filter(Boolean)
                .join(", ") ||
                "Location unavailable"}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => {
              void loadCustomer();
            }}
            className="inline-flex h-10 items-center gap-2 border border-[var(--border)] bg-[var(--surface)] px-3 text-[10px] font-medium text-[var(--text-secondary)] transition-colors hover:text-white"
          >
            <RefreshCw className="size-3.5" />
            Refresh
          </button>

          <div className="border border-[var(--border)] bg-[var(--surface)] px-4 py-3">
            <p className="text-[9px] uppercase tracking-[0.12em] text-[var(--text-muted)]">
              Customer Since
            </p>

            <p className="mt-1.5 text-[11px] font-medium text-white">
              {formatDate(customer.created_at)}
            </p>
          </div>
        </div>
      </div>

      <div className="mt-7 grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-4">
          <CustomerInformation customer={customer} />

          {customer.service_accounts.length === 0 ? (
            <Section
              title="Service Accounts"
              icon={Wifi}
            >
              <EmptyState message="No service accounts are attached to this customer." />
            </Section>
          ) : (
            customer.service_accounts.map(
              (service, index) => (
                <ServiceAccountCard
                  key={service.id}
                  service={service}
                  index={index}
                  packages={packages}
                  onChanged={loadCustomer}
                />
              ),
            )
          )}
        </div>

        <div className="space-y-4">
          <NotificationPreferences
            customer={customer}
          />

          <Section
            title="Customer Status"
            icon={UserRound}
          >
            <DetailRow
              label="Customer State"
              value={
                customer.is_active
                  ? "Active"
                  : "Inactive"
              }
            />

            <DetailRow
              label="Service Accounts"
              value={String(
                customer.service_accounts.length,
              )}
            />

            <DetailRow
              label="Last Updated"
              value={formatDate(
                customer.updated_at,
              )}
            />
          </Section>
        </div>
      </div>
    </PageShell>
  );
}

function PageShell({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="mx-auto w-full max-w-[1600px] px-8 py-7">
      <Link
        href="/customers"
        className="inline-flex items-center gap-2 text-[11px] text-[var(--text-muted)] transition-colors hover:text-white"
      >
        <ArrowLeft className="size-4" />
        Back to Customers
      </Link>

      <div className="mt-5">{children}</div>
    </div>
  );
}

function CustomerInformation({
  customer,
}: {
  customer: CustomerDetail;
}) {
  return (
    <Section
      title="Customer Information"
      icon={UserRound}
    >
      <div className="grid grid-cols-1 gap-x-8 gap-y-4 md:grid-cols-2">
        <DetailRow
          label="Customer Number"
          value={customer.customer_number}
        />

        <DetailRow
          label="Full Name"
          value={customer.full_name}
        />

        <DetailRow
          label="Primary Phone"
          value={customer.phone}
        />

        <DetailRow
          label="Alternate Phone"
          value={
            customer.alternate_phone ||
            "Not provided"
          }
        />

        <DetailRow
          label="Email"
          value={customer.email || "Not provided"}
        />

        <DetailRow
          label="City"
          value={customer.city}
        />

        <DetailRow
          label="Area"
          value={customer.area || "Not provided"}
        />

        <DetailRow
          label="Customer State"
          value={
            customer.is_active
              ? "Active"
              : "Inactive"
          }
        />

        <div className="md:col-span-2">
          <DetailRow
            label="Installation Address"
            value={customer.address_line}
          />
        </div>
      </div>
    </Section>
  );
}

function ServiceAccountCard({
  service,
  index,
  packages,
  onChanged,
}: {
  service: CustomerServiceAccount;
  index: number;
  packages: InternetPackage[];
  onChanged: () => Promise<void>;
}) {
  const networkAssignment =
    service.network_assignment;

  const billingProfile = service.billing_profile;

  const [selectedPackageId, setSelectedPackageId] =
    useState(service.internet_package.id);

  const [actionLoading, setActionLoading] =
    useState<string | null>(null);

  const [actionError, setActionError] = useState<
    string | null
  >(null);

  const [actionMessage, setActionMessage] =
    useState<string | null>(null);

  async function executeAction(
    action:
      | "SUSPEND"
      | "RESTORE"
      | "CHANGE_PACKAGE",
  ) {
    try {
      setActionLoading(action);
      setActionError(null);
      setActionMessage(null);

      if (action === "SUSPEND") {
        await networkService.requestSuspension(
          service.id,
        );

        setActionMessage(
          "Suspension request created successfully.",
        );
      }

      if (action === "RESTORE") {
        await networkService.requestRestore(
          service.id,
        );

        setActionMessage(
          "Restore request created successfully.",
        );
      }

      if (action === "CHANGE_PACKAGE") {
        if (
          selectedPackageId ===
          service.internet_package.id
        ) {
          setActionError(
            "Select a different internet package.",
          );

          return;
        }

        await networkService.requestPackageChange(
          service.id,
          selectedPackageId,
        );

        setActionMessage(
          "Package change request created successfully.",
        );
      }

      await onChanged();
    } catch (requestError) {
      console.error(
        "Service lifecycle action failed:",
        requestError,
      );

      setActionError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to create service lifecycle request.",
      );
    } finally {
      setActionLoading(null);
    }
  }

  const canSuspend = service.status === "ACTIVE";

  const canRestore =
    service.status === "SUSPENDED_NON_PAYMENT";

  const canChangePackage =
    service.status === "ACTIVE";

  return (
    <div className="border border-[var(--border)] bg-[var(--surface)]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border)] px-5 py-4">
        <div>
          <p className="text-[9px] uppercase tracking-[0.14em] text-[var(--text-muted)]">
            Service Account {index + 1}
          </p>

          <p className="mt-1.5 text-[13px] font-semibold text-white">
            {service.service_number}
          </p>
        </div>

        <span
          className={`inline-flex border px-2 py-1 text-[9px] font-semibold uppercase tracking-wide ${
            serviceStatusStyles[service.status]
          }`}
        >
          {formatStatus(service.status)}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2">
        <ServiceSection
          title="Internet Package"
          icon={Package}
        >
          <DetailRow
            label="Package"
            value={service.internet_package.name}
          />

          <DetailRow
            label="Package Code"
            value={service.internet_package.code}
          />

          <DetailRow
            label="Speed"
            value={`${service.internet_package.download_speed_mbps} Mbps ↓ / ${service.internet_package.upload_speed_mbps} Mbps ↑`}
          />

          <DetailRow
            label="Monthly Price"
            value={formatMoney(
              service.internet_package.monthly_price,
            )}
          />
        </ServiceSection>

        <ServiceSection
          title="Network Assignment"
          icon={Network}
        >
          {networkAssignment ? (
            <>
              <DetailRow
                label="Network Node"
                value={`${networkAssignment.network_node_name} (${networkAssignment.network_node_code})`}
              />

              <DetailRow
                label="Username"
                value={
                  networkAssignment.username ||
                  "Not assigned"
                }
              />

              <DetailRow
                label="IP Address"
                value={
                  networkAssignment.ip_address ||
                  "Not assigned"
                }
              />

              <DetailRow
                label="Assignment State"
                value={
                  networkAssignment.is_active
                    ? "Active"
                    : "Inactive"
                }
              />
            </>
          ) : (
            <EmptyState message="No network assignment is available." />
          )}
        </ServiceSection>

        <ServiceSection
          title="Billing Profile"
          icon={CreditCard}
        >
          {billingProfile ? (
            <>
              <DetailRow
                label="Billing Cycle"
                value={billingProfile.billing_cycle}
              />

              <DetailRow
                label="Billing Day"
                value={String(
                  billingProfile.billing_day,
                )}
              />

              <DetailRow
                label="Due Day"
                value={String(
                  billingProfile.due_day,
                )}
              />

              <DetailRow
                label="Profile State"
                value={
                  billingProfile.is_active
                    ? "Active"
                    : "Inactive"
                }
              />
            </>
          ) : (
            <EmptyState message="No billing profile is available." />
          )}
        </ServiceSection>

        <ServiceSection
          title="Device Assignments"
          icon={Router}
        >
          {service.device_assignments.length === 0 ? (
            <EmptyState message="No inventory devices are assigned." />
          ) : (
            <div className="space-y-3">
              {service.device_assignments.map(
                (assignment) => (
                  <div
                    key={assignment.id}
                    className="border border-[var(--border)] bg-[var(--background)] p-3"
                  >
                    <DetailRow
                      label="Asset Tag"
                      value={assignment.asset_tag}
                    />

                    <div className="mt-3">
                      <DetailRow
                        label="Device Type"
                        value={assignment.device_type}
                      />
                    </div>

                    <div className="mt-3">
                      <DetailRow
                        label="Device Status"
                        value={assignment.device_status}
                      />
                    </div>

                    <div className="mt-3">
                      <DetailRow
                        label="Assignment State"
                        value={
                          assignment.is_active
                            ? "Active"
                            : "Inactive"
                        }
                      />
                    </div>

                    <div className="mt-3">
                      <DetailRow
                        label="Assigned At"
                        value={formatDate(
                          assignment.assigned_at,
                        )}
                      />
                    </div>

                    <div className="mt-3">
                      <DetailRow
                        label="Returned At"
                        value={formatDate(
                          assignment.returned_at,
                        )}
                      />
                    </div>

                    <div className="mt-3">
                      <DetailRow
                        label="Return Condition"
                        value={
                          assignment.return_condition ||
                          "Not available"
                        }
                      />
                    </div>
                  </div>
                ),
              )}
            </div>
          )}
        </ServiceSection>
      </div>

      <ServiceLifecycleActions
        service={service}
        packages={packages}
        selectedPackageId={selectedPackageId}
        setSelectedPackageId={setSelectedPackageId}
        actionLoading={actionLoading}
        actionError={actionError}
        actionMessage={actionMessage}
        canSuspend={canSuspend}
        canRestore={canRestore}
        canChangePackage={canChangePackage}
        executeAction={executeAction}
      />

      <div className="border-t border-[var(--border)] px-5 py-3">
        <p className="text-[10px] text-[var(--text-muted)]">
          Activated: {formatDate(service.activated_at)}
        </p>
      </div>
    </div>
  );
}

function ServiceLifecycleActions({
  service,
  packages,
  selectedPackageId,
  setSelectedPackageId,
  actionLoading,
  actionError,
  actionMessage,
  canSuspend,
  canRestore,
  canChangePackage,
  executeAction,
}: {
  service: CustomerServiceAccount;
  packages: InternetPackage[];
  selectedPackageId: string;
  setSelectedPackageId: (
    packageId: string,
  ) => void;
  actionLoading: string | null;
  actionError: string | null;
  actionMessage: string | null;
  canSuspend: boolean;
  canRestore: boolean;
  canChangePackage: boolean;
  executeAction: (
    action:
      | "SUSPEND"
      | "RESTORE"
      | "CHANGE_PACKAGE",
  ) => Promise<void>;
}) {
  return (
    <section className="border-t border-[var(--border)] bg-[var(--background)] px-5 py-5">
      <div className="flex items-center gap-2">
        <PauseCircle className="size-4 text-blue-400" />

        <h4 className="text-[11px] font-semibold text-white">
          Service Lifecycle Actions
        </h4>
      </div>

      <p className="mt-1.5 text-[10px] text-[var(--text-muted)]">
        Actions create real backend provisioning
        requests. Backend service rules remain the
        source of truth.
      </p>

      {actionError && (
        <div className="mt-4 border border-red-500/20 bg-red-500/[0.05] px-3 py-2.5 text-[10px] text-red-400">
          {actionError}
        </div>
      )}

      {actionMessage && (
        <div className="mt-4 border border-green-500/20 bg-green-500/[0.05] px-3 py-2.5 text-[10px] text-green-400">
          {actionMessage}
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-end gap-3">
        {canSuspend && (
          <button
            type="button"
            disabled={actionLoading !== null}
            onClick={() => {
              void executeAction("SUSPEND");
            }}
            className="inline-flex h-9 items-center gap-2 border border-orange-500/30 bg-orange-500/[0.06] px-3 text-[10px] font-semibold text-orange-400 transition-colors hover:bg-orange-500/10 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {actionLoading === "SUSPEND" && (
              <Loader2 className="size-3.5 animate-spin" />
            )}

            Request Suspension
          </button>
        )}

        {canRestore && (
          <button
            type="button"
            disabled={actionLoading !== null}
            onClick={() => {
              void executeAction("RESTORE");
            }}
            className="inline-flex h-9 items-center gap-2 border border-green-500/30 bg-green-500/[0.06] px-3 text-[10px] font-semibold text-green-400 transition-colors hover:bg-green-500/10 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {actionLoading === "RESTORE" && (
              <Loader2 className="size-3.5 animate-spin" />
            )}

            Request Restore
          </button>
        )}

        {canChangePackage && (
          <>
            <div>
              <p className="mb-2 text-[9px] uppercase tracking-[0.1em] text-[var(--text-muted)]">
                Target Package
              </p>

              <select
                value={selectedPackageId}
                onChange={(event) =>
                  setSelectedPackageId(
                    event.target.value,
                  )
                }
                disabled={actionLoading !== null}
                className="h-9 min-w-56 border border-[var(--border)] bg-[var(--surface)] px-3 text-[10px] text-[var(--text-secondary)] outline-none focus:border-blue-500/60 disabled:opacity-50"
              >
                {packages.map((internetPackage) => (
                  <option
                    key={internetPackage.id}
                    value={internetPackage.id}
                  >
                    {internetPackage.code} —{" "}
                    {internetPackage.name}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="button"
              disabled={actionLoading !== null}
              onClick={() => {
                void executeAction(
                  "CHANGE_PACKAGE",
                );
              }}
              className="inline-flex h-9 items-center gap-2 border border-blue-500/30 bg-blue-500/[0.06] px-3 text-[10px] font-semibold text-blue-400 transition-colors hover:bg-blue-500/10 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {actionLoading ===
                "CHANGE_PACKAGE" && (
                <Loader2 className="size-3.5 animate-spin" />
              )}

              Request Package Change
            </button>
          </>
        )}

        {!canSuspend &&
          !canRestore &&
          !canChangePackage && (
            <div className="border border-[var(--border)] bg-[var(--surface)] px-3 py-2.5">
              <p className="text-[10px] text-[var(--text-muted)]">
                No lifecycle actions are currently
                available for{" "}
                <span className="text-[var(--text-secondary)]">
                  {formatStatus(service.status)}
                </span>
                .
              </p>
            </div>
          )}
      </div>
    </section>
  );
}

function NotificationPreferences({
  customer,
}: {
  customer: CustomerDetail;
}) {
  const preferences =
    customer.notification_preference;

  return (
    <Section title="Notifications" icon={BellRing}>
      {preferences ? (
        <div className="space-y-3">
          <PreferenceStatus
            label="SMS Notifications"
            enabled={preferences.sms_enabled}
          />

          <PreferenceStatus
            label="WhatsApp Notifications"
            enabled={preferences.whatsapp_enabled}
          />
        </div>
      ) : (
        <EmptyState message="Notification preferences are not configured." />
      )}
    </Section>
  );
}

function Section({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
}) {
  return (
    <section className="border border-[var(--border)] bg-[var(--surface)]">
      <div className="flex items-center gap-2 border-b border-[var(--border)] px-5 py-4">
        <Icon className="size-4 text-blue-400" />

        <h3 className="text-[12px] font-semibold text-white">
          {title}
        </h3>
      </div>

      <div className="p-5">{children}</div>
    </section>
  );
}

function ServiceSection({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
}) {
  return (
    <section className="border-b border-[var(--border)] p-5 odd:lg:border-r">
      <div className="mb-5 flex items-center gap-2">
        <Icon className="size-4 text-blue-400" />

        <h4 className="text-[11px] font-semibold text-white">
          {title}
        </h4>
      </div>

      <div className="space-y-4">
        {children}
      </div>
    </section>
  );
}

function DetailRow({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div>
      <p className="text-[9px] uppercase tracking-[0.1em] text-[var(--text-muted)]">
        {label}
      </p>

      <p className="mt-1.5 break-words text-[11px] font-medium text-[var(--text-secondary)]">
        {value}
      </p>
    </div>
  );
}

function PreferenceStatus({
  label,
  enabled,
}: {
  label: string;
  enabled: boolean;
}) {
  return (
    <div className="flex items-center justify-between border border-[var(--border)] bg-[var(--background)] px-3 py-3">
      <span className="text-[10px] text-[var(--text-secondary)]">
        {label}
      </span>

      <span
        className={`text-[9px] font-semibold uppercase ${
          enabled
            ? "text-green-400"
            : "text-red-400"
        }`}
      >
        {enabled ? "Enabled" : "Disabled"}
      </span>
    </div>
  );
}

function EmptyState({
  message,
}: {
  message: string;
}) {
  return (
    <p className="text-[10px] leading-5 text-[var(--text-muted)]">
      {message}
    </p>
  );
}

function StatePanel({
  message,
}: {
  message: string;
}) {
  return (
    <div className="flex min-h-72 items-center justify-center border border-[var(--border)] bg-[var(--surface)]">
      <p className="text-[11px] text-[var(--text-muted)]">
        {message}
      </p>
    </div>
  );
}