"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Check,
  ChevronDown,
  MapPin,
  Package,
  SlidersHorizontal,
  UserRound,
} from "lucide-react";

import {
  customersService,
  type CustomerActivationPayload,
  type InternetPackage,
} from "@/services/customers.service";
import {
  networkService,
  type NetworkNode,
} from "@/services/network.service";
import {
  geoService,
  type Area,
  type City,
} from "@/services/geo.service";
import {
  inventoryService,
  type InventoryDevice,
} from "@/services/inventory.service";
import LoadingSpinner from "@/components/ui/LoadingSpinner";

// One-page activation: the counter staff fills the essentials top to bottom and
// presses Activate once. Rarely used settings stay folded under "More options".

const inputClass =
  "h-10 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-[12px] text-white outline-none transition-colors placeholder:text-[var(--text-muted)] focus:border-blue-500";

const labelClass =
  "mb-2 block text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--text-muted)]";

interface OnboardingForm {
  firstName: string;
  lastName: string;
  phone: string;
  alternatePhone: string;
  email: string;
  addressLine: string;
  area: string;
  city: string;
  internetPackageId: string;
  networkNodeId: string;
  networkUsername: string;
  networkPassword: string;
  networkIpAddress: string;
  deviceId: string;
  deviceAssignmentNotes: string;
  billingDay: string;
  dueDay: string;
  billingCycle: "MONTHLY" | "PREPAID";
  smsEnabled: boolean;
  whatsappEnabled: boolean;
}

type FieldErrors = Partial<Record<keyof OnboardingForm, string>>;

const initialForm: OnboardingForm = {
  firstName: "",
  lastName: "",
  phone: "",
  alternatePhone: "",
  email: "",
  addressLine: "",
  area: "",
  city: "",
  internetPackageId: "",
  networkNodeId: "",
  networkUsername: "",
  networkPassword: "",
  networkIpAddress: "",
  deviceId: "",
  deviceAssignmentNotes: "",
  billingDay: "1",
  dueDay: "10",
  billingCycle: "MONTHLY",
  smsEnabled: true,
  whatsappEnabled: true,
};

// Fields inside "More options"; an error there opens the panel.
const ADVANCED_FIELDS: (keyof OnboardingForm)[] = ["billingDay", "dueDay", "networkIpAddress"];

function validate(form: OnboardingForm): FieldErrors {
  const errors: FieldErrors = {};
  if (!form.firstName.trim()) errors.firstName = "Enter the customer's name.";
  if (!form.phone.trim()) errors.phone = "Enter a mobile number.";
  if (!form.city.trim()) errors.city = "Choose the city.";
  if (!form.addressLine.trim()) errors.addressLine = "Enter the installation address.";
  if (!form.internetPackageId) errors.internetPackageId = "Choose a package.";
  if (!form.networkNodeId) errors.networkNodeId = "Choose the router / node.";
  const inRange = (value: string) => {
    const day = Number(value);
    return Number.isInteger(day) && day >= 1 && day <= 28;
  };
  if (!inRange(form.billingDay)) errors.billingDay = "Use a day from 1 to 28.";
  if (!inRange(form.dueDay)) errors.dueDay = "Use a day from 1 to 28.";
  return errors;
}

export default function CustomerOnboarding() {
  const router = useRouter();
  const formRef = useRef<HTMLFormElement>(null);

  const [form, setForm] = useState<OnboardingForm>(initialForm);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [packages, setPackages] = useState<InternetPackage[]>([]);
  const [networkNodes, setNetworkNodes] = useState<NetworkNode[]>([]);
  const [availableDevices, setAvailableDevices] = useState<InventoryDevice[]>([]);
  const [cities, setCities] = useState<City[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);
  const [selectedCityId, setSelectedCityId] = useState("");
  const [selectedAreaId, setSelectedAreaId] = useState("");
  const [isManualGeo, setIsManualGeo] = useState(false);
  const [showMore, setShowMore] = useState(false);
  const [loadingAreas, setLoadingAreas] = useState(false);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activatedCredentials, setActivatedCredentials] = useState<{
    customerId: string;
    customerName: string;
    serviceNumber: string;
    username: string;
    password: string;
  } | null>(null);

  const selectedPackage = useMemo(
    () => packages.find((item) => item.id === form.internetPackageId) ?? null,
    [packages, form.internetPackageId],
  );

  function updateField<K extends keyof OnboardingForm>(field: K, value: OnboardingForm[K]) {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => (current[field] ? { ...current, [field]: undefined } : current));
    setError(null);
  }

  async function selectCity(cityId: string, cityList: City[] = cities) {
    setSelectedCityId(cityId);
    setSelectedAreaId("");
    setAreas([]);
    const matchedCity = cityList.find((c) => c.id === cityId);
    setForm((current) => ({ ...current, city: matchedCity?.name ?? "", area: "" }));
    setErrors((current) => ({ ...current, city: undefined }));

    if (!cityId) return;
    try {
      setLoadingAreas(true);
      setAreas(await geoService.getAreas({ city: cityId, status: "active" }));
    } catch {
      setAreas([]);
    } finally {
      setLoadingAreas(false);
    }
  }

  useEffect(() => {
    let active = true;

    async function loadOptions() {
      try {
        setLoadingOptions(true);
        setError(null);

        const [packageData, nodeData, cityData, devicesData] = await Promise.all([
          customersService.getInternetPackages(),
          networkService.getNodes({ active: true }),
          geoService.getCities({ status: "active" }),
          inventoryService.getDevices().catch(() => [] as InventoryDevice[]),
        ]);

        if (!active) return;

        setPackages(packageData);
        setNetworkNodes(nodeData);
        setCities(cityData);
        setAvailableDevices(devicesData.filter((d) => d.status === "AVAILABLE"));

        // Most ISPs have one router and work in one city: pick those for the staff.
        setForm((current) => ({
          ...current,
          networkNodeId: current.networkNodeId || (nodeData.length === 1 ? nodeData[0].id : ""),
          internetPackageId: current.internetPackageId || (packageData.length === 1 ? packageData[0].id : ""),
        }));
        if (cityData.length === 1) {
          void selectCity(cityData[0].id, cityData);
        }
      } catch (requestError) {
        console.error("Failed to load customer activation options:", requestError);
        if (active) {
          setError("Unable to load packages, network nodes, and geographic areas.");
        }
      } finally {
        if (active) setLoadingOptions(false);
      }
    }

    void loadOptions();
    return () => {
      active = false;
    };
    // selectCity only reads state setters here; run once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleAreaChange(areaId: string) {
    setSelectedAreaId(areaId);
    updateField("area", areas.find((a) => a.id === areaId)?.name ?? "");
  }

  async function activateCustomer(event: React.FormEvent) {
    event.preventDefault();

    const found = validate(form);
    if (Object.values(found).some(Boolean)) {
      setErrors(found);
      setError("Please fill the highlighted fields.");
      if (ADVANCED_FIELDS.some((field) => found[field])) setShowMore(true);
      // Bring the first problem into view.
      requestAnimationFrame(() => {
        formRef.current?.querySelector<HTMLElement>("[data-invalid='true']")?.scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
      });
      return;
    }

    const payload: CustomerActivationPayload = {
      internet_package_id: form.internetPackageId,
      network_node_id: form.networkNodeId,
      first_name: form.firstName.trim(),
      last_name: form.lastName.trim(),
      phone: form.phone.trim(),
      alternate_phone: form.alternatePhone.trim(),
      email: form.email.trim(),
      address_line: form.addressLine.trim(),
      area: form.area.trim(),
      city: form.city.trim(),
      network_username: form.networkUsername.trim(),
      network_ip_address: form.networkIpAddress.trim() || null,
      device_assignment_notes: form.deviceAssignmentNotes.trim(),
      billing_day: Number(form.billingDay),
      due_day: Number(form.dueDay),
      billing_cycle: form.billingCycle,
      sms_enabled: form.smsEnabled,
      whatsapp_enabled: form.whatsappEnabled,
    };

    if (form.deviceId) payload.device_id = form.deviceId;
    if (form.networkPassword) payload.network_password = form.networkPassword;

    try {
      setSubmitting(true);
      setError(null);

      const result = await customersService.activateCustomer(payload);

      // PPPoE credentials are only returned once, so show them before leaving the page.
      if (result.network_assignment.password) {
        setActivatedCredentials({
          customerId: result.customer.id,
          customerName: result.customer.full_name,
          serviceNumber: result.service_account.service_number,
          username: result.network_assignment.username,
          password: result.network_assignment.password,
        });
        return;
      }

      router.push(`/customers/${result.customer.id}`);
    } catch (requestError) {
      console.error("Customer activation failed:", requestError);
      setError(requestError instanceof Error ? requestError.message : "Customer activation failed.");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } finally {
      setSubmitting(false);
    }
  }

  if (loadingOptions) {
    return (
      <div className="flex min-h-[420px] items-center justify-center border border-[var(--border)] bg-[var(--surface)]">
        <p className="text-[11px] text-[var(--text-muted)]">Loading form...</p>
      </div>
    );
  }

  if (activatedCredentials) {
    return (
      <div className="flex min-h-[420px] items-center justify-center border border-[var(--border)] bg-[var(--surface)] p-6">
        <div className="w-full max-w-md border border-[var(--border)] bg-[var(--background)] p-6">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-emerald-400">Service Activated</p>
          <h2 className="mt-2 text-base font-semibold text-white">{activatedCredentials.customerName}</h2>
          <p className="mt-1 font-mono text-[11px] text-[var(--text-muted)]">{activatedCredentials.serviceNumber}</p>

          <div className="mt-5 space-y-3 border border-[var(--border)] bg-[var(--surface)] p-4">
            <div>
              <span className={labelClass}>PPPoE Username</span>
              <p className="font-mono text-[13px] text-white">{activatedCredentials.username}</p>
            </div>
            <div>
              <span className={labelClass}>PPPoE Password</span>
              <p className="font-mono text-[13px] text-white">{activatedCredentials.password}</p>
            </div>
          </div>

          <p className="mt-3 text-[11px] leading-5 text-[var(--text-secondary)]">
            Configure these on the customer&apos;s router now. The password is stored encrypted and is not shown again.
          </p>

          <button
            type="button"
            onClick={() => router.push(`/customers/${activatedCredentials.customerId}`)}
            className="mt-5 flex h-10 w-full items-center justify-center bg-blue-600 text-[12px] font-semibold text-white transition-colors hover:bg-blue-500"
          >
            Open Customer Profile
          </button>
        </div>
      </div>
    );
  }

  const showCitySelect = !isManualGeo && cities.length > 0;
  const price = selectedPackage ? Number(selectedPackage.monthly_price).toLocaleString() : null;

  return (
    <form ref={formRef} onSubmit={activateCustomer} noValidate className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
      <div className="space-y-5">
        {error && (
          <div className="border border-red-500/20 bg-red-500/[0.05] px-4 py-3 text-[11px] text-red-400">{error}</div>
        )}

        <Section icon={UserRound} title="Customer">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Field label="First Name *" placeholder="Customer first name" value={form.firstName}
              error={errors.firstName} autoFocus onChange={(value) => updateField("firstName", value)} />
            <Field label="Last Name" placeholder="Customer last name" value={form.lastName}
              onChange={(value) => updateField("lastName", value)} />
            <Field label="Mobile Number *" placeholder="03XX XXXXXXX" type="tel" value={form.phone}
              error={errors.phone} onChange={(value) => updateField("phone", value)} />
            <Field label="Other Number" placeholder="Optional" type="tel" value={form.alternatePhone}
              onChange={(value) => updateField("alternatePhone", value)} />
          </div>
        </Section>

        <Section
          icon={MapPin}
          title="Address"
          action={cities.length > 0 ? (
            <button type="button" onClick={() => setIsManualGeo(!isManualGeo)}
              className="text-[11px] text-blue-400 underline hover:text-blue-300">
              {isManualGeo ? "Choose from list" : "Type city / area instead"}
            </button>
          ) : null}
        >
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {showCitySelect ? (
              <>
                <SelectField label="City *" value={selectedCityId} error={errors.city}
                  onChange={(value) => void selectCity(value)}>
                  <option value="">Select city...</option>
                  {cities.map((city) => <option key={city.id} value={city.id}>{city.name}</option>)}
                </SelectField>
                <label>
                  <span className={labelClass}>
                    Area
                    {loadingAreas && <span className="ml-2 inline-block"><LoadingSpinner size="xs" tone="primary" /></span>}
                  </span>
                  <select disabled={!selectedCityId || loadingAreas} value={selectedAreaId}
                    onChange={(e) => handleAreaChange(e.target.value)} className={`${inputClass} disabled:opacity-50`}>
                    <option value="">
                      {!selectedCityId ? "Select city first..." : areas.length === 0 ? "No areas added (optional)" : "Select area..."}
                    </option>
                    {areas.map((area) => <option key={area.id} value={area.id}>{area.name}</option>)}
                  </select>
                </label>
              </>
            ) : (
              <>
                <Field label="City *" placeholder="e.g. Lahore" value={form.city} error={errors.city}
                  onChange={(value) => updateField("city", value)} />
                <Field label="Area" placeholder="e.g. Johar Town" value={form.area}
                  onChange={(value) => updateField("area", value)} />
              </>
            )}
            <div className="md:col-span-2">
              <Field label="Installation Address *" placeholder="House / street / block / landmark"
                value={form.addressLine} error={errors.addressLine}
                onChange={(value) => updateField("addressLine", value)} />
            </div>
          </div>
        </Section>

        <Section icon={Package} title="Connection">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <SelectField label="Package *" value={form.internetPackageId} error={errors.internetPackageId}
              onChange={(value) => updateField("internetPackageId", value)}>
              <option value="">{packages.length === 0 ? "No packages — add one first" : "Select package..."}</option>
              {packages.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name} · {item.download_speed_mbps} Mbps · Rs. {Number(item.monthly_price).toLocaleString()}
                </option>
              ))}
            </SelectField>

            <SelectField label="Router / Node *" value={form.networkNodeId} error={errors.networkNodeId}
              onChange={(value) => updateField("networkNodeId", value)}>
              <option value="">{networkNodes.length === 0 ? "No routers — add one on Network page" : "Select router / node..."}</option>
              {networkNodes.map((node) => (
                <option key={node.id} value={node.id}>{node.name} ({node.code})</option>
              ))}
            </SelectField>

            <div className="md:col-span-2">
              <span className={labelClass}>Billing</span>
              <div className="grid grid-cols-2 gap-2">
                {([
                  ["MONTHLY", "Monthly bill", "A bill is made every month"],
                  ["PREPAID", "Prepaid recharge", "Recharge from the customer page"],
                ] as const).map(([value, title, hint]) => (
                  <button key={value} type="button" onClick={() => updateField("billingCycle", value)}
                    className={`border p-3 text-left transition-colors ${
                      form.billingCycle === value
                        ? "border-blue-500 bg-blue-500/10"
                        : "border-[var(--border)] bg-[var(--background)] hover:border-slate-600"
                    }`}>
                    <p className="text-[12px] font-semibold text-white">{title}</p>
                    <p className="mt-1 text-[10px] text-[var(--text-muted)]">{hint}</p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </Section>

        <section className="border border-[var(--border)] bg-[var(--surface)]">
          <button type="button" onClick={() => setShowMore(!showMore)}
            className="flex w-full items-center justify-between px-5 py-4 text-left">
            <span className="flex items-center gap-2 text-[12px] font-semibold text-white">
              <SlidersHorizontal className="size-4 text-blue-400" />
              More options
              <span className="font-normal text-[var(--text-muted)]">
                · email, PPPoE login, IP, device, billing dates, alerts
              </span>
            </span>
            <ChevronDown className={`size-4 text-[var(--text-muted)] transition-transform ${showMore ? "rotate-180" : ""}`} />
          </button>

          {showMore && (
            <div className="grid grid-cols-1 gap-4 border-t border-[var(--border)] p-5 md:grid-cols-2">
              <div className="md:col-span-2">
                <Field label="Email" placeholder="customer@example.com" type="email" value={form.email}
                  onChange={(value) => updateField("email", value)} />
              </div>
              <Field label="PPPoE Username" placeholder="Auto: service number" value={form.networkUsername}
                onChange={(value) => updateField("networkUsername", value)} />
              <Field label="PPPoE Password" placeholder="Auto-generated if blank" type="password"
                value={form.networkPassword} onChange={(value) => updateField("networkPassword", value)} />
              <Field label="Static IP" placeholder="Optional" value={form.networkIpAddress} error={errors.networkIpAddress}
                onChange={(value) => updateField("networkIpAddress", value)} />
              <SelectField label="Device (ONU / Router)" value={form.deviceId}
                onChange={(value) => updateField("deviceId", value)}>
                <option value="">{availableDevices.length === 0 ? "No devices in stock" : "No device"}</option>
                {availableDevices.map((d) => (
                  <option key={d.id} value={d.id}>{d.asset_tag} — {d.device_type} {d.model_name} (SN {d.serial_number})</option>
                ))}
              </SelectField>
              {form.deviceId && (
                <div className="md:col-span-2">
                  <Field label="Device Notes" placeholder="e.g. Wall mounted in lounge" value={form.deviceAssignmentNotes}
                    onChange={(value) => updateField("deviceAssignmentNotes", value)} />
                </div>
              )}
              <Field label="Bill Day (1–28)" placeholder="1" type="number" min={1} max={28} value={form.billingDay}
                error={errors.billingDay} onChange={(value) => updateField("billingDay", value)} />
              <Field label="Due Day (1–28)" placeholder="10" type="number" min={1} max={28} value={form.dueDay}
                error={errors.dueDay} onChange={(value) => updateField("dueDay", value)} />
              <div className="md:col-span-2">
                <span className={labelClass}>Customer Alerts</span>
                <div className="flex flex-wrap gap-4">
                  <Toggle label="WhatsApp" checked={form.whatsappEnabled}
                    onChange={(value) => updateField("whatsappEnabled", value)} />
                  <Toggle label="SMS" checked={form.smsEnabled}
                    onChange={(value) => updateField("smsEnabled", value)} />
                </div>
              </div>
            </div>
          )}
        </section>
      </div>

      <aside className="xl:sticky xl:top-20 xl:self-start">
        <div className="border border-[var(--border)] bg-[var(--surface)] p-5">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-blue-400">Summary</p>
          <dl className="mt-4 space-y-3 text-[12px]">
            <SummaryRow label="Customer" value={[form.firstName, form.lastName].filter(Boolean).join(" ")} />
            <SummaryRow label="Mobile" value={form.phone} />
            <SummaryRow label="Area" value={[form.area, form.city].filter(Boolean).join(", ")} />
            <SummaryRow label="Package" value={selectedPackage?.name ?? ""} />
            <SummaryRow label="Billing" value={form.billingCycle === "PREPAID" ? "Prepaid" : "Monthly"} />
          </dl>
          {price && (
            <div className="mt-4 border-t border-[var(--border)] pt-4">
              <p className="text-[10px] uppercase tracking-[0.12em] text-[var(--text-muted)]">Monthly</p>
              <p className="mt-1 text-xl font-semibold text-white">Rs. {price}</p>
            </div>
          )}
          <button type="submit" disabled={submitting}
            className="mt-5 flex h-11 w-full items-center justify-center gap-2 bg-green-600 text-[12px] font-semibold text-white transition-colors hover:bg-green-500 disabled:cursor-not-allowed disabled:opacity-50">
            {submitting ? <LoadingSpinner size="xs" tone="white" /> : <Check className="size-4" />}
            {submitting ? "Activating..." : "Activate Service"}
          </button>
          <p className="mt-2 text-center text-[10px] text-[var(--text-muted)]">* required fields</p>
        </div>
      </aside>
    </form>
  );
}

function Section({
  icon: Icon,
  title,
  action,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="border border-[var(--border)] bg-[var(--surface)] p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h3 className="flex items-center gap-2 text-[12px] font-semibold uppercase tracking-[0.12em] text-white">
          <Icon className="size-4 text-blue-400" />
          {title}
        </h3>
        {action}
      </div>
      {children}
    </section>
  );
}

interface FieldProps {
  label: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  min?: number;
  max?: number;
  error?: string;
  autoFocus?: boolean;
}

function Field({ label, placeholder, value, onChange, type = "text", min, max, error, autoFocus }: FieldProps) {
  return (
    <label data-invalid={error ? "true" : undefined}>
      <span className={labelClass}>{label}</span>
      <input
        type={type}
        min={min}
        max={max}
        value={value}
        autoFocus={autoFocus}
        aria-invalid={Boolean(error)}
        onChange={(event) => onChange(event.target.value)}
        className={`${inputClass} ${error ? "border-red-500/60" : ""}`}
        placeholder={placeholder}
      />
      {error && <span className="mt-1 block text-[10px] text-red-400">{error}</span>}
    </label>
  );
}

function SelectField({
  label,
  value,
  onChange,
  error,
  children,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <label data-invalid={error ? "true" : undefined}>
      <span className={labelClass}>{label}</span>
      <select
        value={value}
        aria-invalid={Boolean(error)}
        onChange={(event) => onChange(event.target.value)}
        className={`${inputClass} ${error ? "border-red-500/60" : ""}`}
      >
        {children}
      </select>
      {error && <span className="mt-1 block text-[10px] text-red-400">{error}</span>}
    </label>
  );
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-[12px] text-[var(--text-secondary)]">
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)}
        className="size-4 accent-blue-500" />
      {label}
    </label>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-[var(--text-muted)]">{label}</dt>
      <dd className="truncate text-right text-white">{value || "—"}</dd>
    </div>
  );
}
