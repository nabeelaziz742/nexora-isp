"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  BellRing,
  Check,
  ChevronLeft,
  ChevronRight,
  CreditCard,
  MapPin,
  Network,
  Package,
  Router,
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
  type Country,
} from "@/services/geo.service";
import {
  inventoryService,
  type InventoryDevice,
} from "@/services/inventory.service";
import LoadingSpinner from "@/components/ui/LoadingSpinner";

const steps = [
  { id: 1, title: "Personal Information", icon: UserRound },
  { id: 2, title: "Service Address", icon: MapPin },
  { id: 3, title: "Internet Package", icon: Package },
  { id: 4, title: "Network Assignment", icon: Network },
  { id: 5, title: "Device Assignment", icon: Router },
  { id: 6, title: "Billing Cycle", icon: CreditCard },
  { id: 7, title: "Notifications", icon: BellRing },
];

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
  networkIpAddress: string;
  deviceId: string;
  deviceAssignmentNotes: string;
  billingDay: string;
  dueDay: string;
  smsEnabled: boolean;
  whatsappEnabled: boolean;
}

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
  networkIpAddress: "",
  deviceId: "",
  deviceAssignmentNotes: "",
  billingDay: "1",
  dueDay: "10",
  smsEnabled: true,
  whatsappEnabled: true,
};

export default function CustomerOnboarding() {
  const router = useRouter();

  const [currentStep, setCurrentStep] = useState(1);
  const [form, setForm] = useState<OnboardingForm>(initialForm);
  const [packages, setPackages] = useState<InternetPackage[]>([]);
  const [networkNodes, setNetworkNodes] = useState<NetworkNode[]>([]);
  const [availableDevices, setAvailableDevices] = useState<InventoryDevice[]>([]);
  const [countries, setCountries] = useState<Country[]>([]);
  const [cities, setCities] = useState<City[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);
  const [selectedCountryId, setSelectedCountryId] = useState<string>("");
  const [selectedCityId, setSelectedCityId] = useState<string>("");
  const [selectedAreaId, setSelectedAreaId] = useState<string>("");
  const [isManualGeo, setIsManualGeo] = useState<boolean>(false);
  const [loadingAreas, setLoadingAreas] = useState(false);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadOptions() {
      try {
        setLoadingOptions(true);
        setError(null);

        const [packageData, nodeData, countryData, cityData, devicesData] =
          await Promise.all([
            customersService.getInternetPackages(),
            networkService.getNodes({
              active: true,
            }),
            geoService.getCountries({ status: "active" }),
            geoService.getCities({ status: "active" }),
            inventoryService.getDevices().catch(() => [] as InventoryDevice[]),
          ]);

        if (!active) {
          return;
        }

        setPackages(packageData);
        setNetworkNodes(nodeData);
        setCountries(countryData);
        setCities(cityData);
        setAvailableDevices(
          devicesData.filter((d) => d.status === "AVAILABLE")
        );
      } catch (requestError) {
        console.error(
          "Failed to load customer activation options:",
          requestError,
        );

        if (active) {
          setError(
            "Unable to load packages, network nodes, and geographic areas.",
          );
        }
      } finally {
        if (active) {
          setLoadingOptions(false);
        }
      }
    }

    void loadOptions();

    return () => {
      active = false;
    };
  }, []);


  async function handleCountryChange(countryId: string) {
    setSelectedCountryId(countryId);
    setSelectedCityId("");
    setSelectedAreaId("");
    setAreas([]);
    updateField("city", "");
    updateField("area", "");

    try {
      const cityData = await geoService.getCities({
        country: countryId || undefined,
        status: "active",
      });
      setCities(cityData);
    } catch {
      // Keep existing cities on error
    }
  }

  async function handleCityChange(cityId: string) {
    setSelectedCityId(cityId);
    setSelectedAreaId("");
    setAreas([]);
    updateField("area", "");

    const matchedCity = cities.find((c) => c.id === cityId);
    if (matchedCity) {
      updateField("city", matchedCity.name);
    } else {
      updateField("city", "");
    }

    if (!cityId) return;

    try {
      setLoadingAreas(true);
      const areaData = await geoService.getAreas({
        city: cityId,
        status: "active",
      });
      setAreas(areaData);
    } catch {
      setAreas([]);
    } finally {
      setLoadingAreas(false);
    }
  }

  function handleAreaChange(areaId: string) {
    setSelectedAreaId(areaId);
    const matchedArea = areas.find((a) => a.id === areaId);
    if (matchedArea) {
      updateField("area", matchedArea.name);
    } else {
      updateField("area", "");
    }
  }

  function updateField<K extends keyof OnboardingForm>(
    field: K,
    value: OnboardingForm[K],
  ) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));

    setError(null);
  }

  function validateStep() {
    if (currentStep === 1) {
      if (
        !form.firstName.trim() ||
        !form.phone.trim()
      ) {
        setError(
          "First name and primary phone are required.",
        );

        return false;
      }
    }

    if (currentStep === 2) {
      if (
        !form.addressLine.trim() ||
        !form.city.trim()
      ) {
        setError(
          "Installation address and city are required.",
        );

        return false;
      }
    }

    if (
      currentStep === 3 &&
      !form.internetPackageId
    ) {
      setError("Select an internet package.");

      return false;
    }

    if (
      currentStep === 4 &&
      !form.networkNodeId
    ) {
      setError("Select a network node.");

      return false;
    }

    if (currentStep === 6) {
      const billingDay = Number(form.billingDay);
      const dueDay = Number(form.dueDay);

      if (
        !Number.isInteger(billingDay) ||
        billingDay < 1 ||
        billingDay > 28 ||
        !Number.isInteger(dueDay) ||
        dueDay < 1 ||
        dueDay > 28
      ) {
        setError(
          "Billing day and due day must be between 1 and 28.",
        );

        return false;
      }
    }

    return true;
  }

  function nextStep() {
    if (!validateStep()) {
      return;
    }

    setError(null);

    setCurrentStep((step) =>
      Math.min(step + 1, steps.length),
    );
  }

  function previousStep() {
    setError(null);

    setCurrentStep((step) =>
      Math.max(step - 1, 1),
    );
  }

  async function activateCustomer() {
    if (!validateStep()) {
      return;
    }

    if (
      !form.internetPackageId ||
      !form.networkNodeId
    ) {
      setError(
        "Internet package and network node are required.",
      );

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
      network_username:
        form.networkUsername.trim(),
      network_ip_address:
        form.networkIpAddress.trim() || null,
      device_assignment_notes:
        form.deviceAssignmentNotes.trim(),
      billing_day: Number(form.billingDay),
      due_day: Number(form.dueDay),
      sms_enabled: form.smsEnabled,
      whatsapp_enabled: form.whatsappEnabled,
    };

    if (form.deviceId) {
      payload.device_id = form.deviceId;
    }

    try {
      setSubmitting(true);
      setError(null);

      const result =
        await customersService.activateCustomer(payload);

      router.push(`/customers/${result.customer.id}`);
    } catch (requestError) {
      console.error(
        "Customer activation failed:",
        requestError,
      );

      const message =
        requestError instanceof Error
          ? requestError.message
          : "Customer activation failed.";

      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  if (loadingOptions) {
    return (
      <div className="flex min-h-[620px] items-center justify-center border border-[var(--border)] bg-[var(--surface)]">
        <p className="text-[11px] text-[var(--text-muted)]">
          Loading activation workflow...
        </p>
      </div>
    );
  }

  return (
    <div className="grid min-h-[620px] grid-cols-1 border border-[var(--border)] bg-[var(--surface)] xl:grid-cols-[280px_minmax(0,1fr)]">
      <aside className="border-b border-[var(--border)] bg-[var(--background)] p-5 xl:border-b-0 xl:border-r">
        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-blue-400">
          Activation Workflow
        </p>

        <p className="mt-2 text-[11px] leading-5 text-[var(--text-secondary)]">
          Complete the subscriber provisioning workflow before service
          activation.
        </p>

        <div className="mt-6 space-y-1">
          {steps.map((step) => {
            const Icon = step.icon;
            const isActive = currentStep === step.id;
            const isComplete = currentStep > step.id;

            return (
              <button
                key={step.id}
                type="button"
                onClick={() => {
                  if (step.id < currentStep) {
                    setError(null);
                    setCurrentStep(step.id);
                    return;
                  }

                  if (step.id === currentStep) {
                    return;
                  }

                  setError(
                    "Complete the current step before continuing.",
                  );
                }}
                className={`flex w-full items-center gap-3 px-3 py-3 text-left transition-colors ${
                  isActive
                    ? "bg-blue-500/10"
                    : "hover:bg-white/[0.03]"
                }`}
              >
                <div
                  className={`flex size-8 shrink-0 items-center justify-center border ${
                    isComplete
                      ? "border-green-500/20 bg-green-500/10 text-green-400"
                      : isActive
                        ? "border-blue-500/20 bg-blue-500/10 text-blue-400"
                        : "border-[var(--border)] text-[var(--text-muted)]"
                  }`}
                >
                  {isComplete ? (
                    <Check className="size-4" />
                  ) : (
                    <Icon className="size-4" />
                  )}
                </div>

                <div>
                  <p className="text-[9px] uppercase tracking-[0.12em] text-[var(--text-muted)]">
                    Step {step.id}
                  </p>

                  <p
                    className={`mt-0.5 text-[11px] font-medium ${
                      isActive
                        ? "text-white"
                        : "text-[var(--text-secondary)]"
                    }`}
                  >
                    {step.title}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </aside>

      <div className="flex min-w-0 flex-col">
        <div className="border-b border-[var(--border)] px-7 py-5">
          <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--text-muted)]">
            Step {currentStep} of {steps.length}
          </p>

          <h3 className="mt-1.5 text-lg font-semibold text-white">
            {steps[currentStep - 1].title}
          </h3>
        </div>

        <div className="flex-1 p-7">
          {error && (
            <div className="mb-5 border border-red-500/20 bg-red-500/[0.05] px-4 py-3 text-[11px] text-red-400">
              {error}
            </div>
          )}

          {currentStep === 1 && (
            <div className="grid max-w-3xl grid-cols-1 gap-5 md:grid-cols-2">
              <Field
                label="First Name"
                placeholder="Customer first name"
                value={form.firstName}
                onChange={(value) =>
                  updateField("firstName", value)
                }
              />

              <Field
                label="Last Name"
                placeholder="Customer last name"
                value={form.lastName}
                onChange={(value) =>
                  updateField("lastName", value)
                }
              />

              <Field
                label="Primary Phone"
                placeholder="03XX XXXXXXX"
                value={form.phone}
                onChange={(value) =>
                  updateField("phone", value)
                }
              />

              <Field
                label="Alternate Phone"
                placeholder="Optional"
                value={form.alternatePhone}
                onChange={(value) =>
                  updateField("alternatePhone", value)
                }
              />

              <div className="md:col-span-2">
                <Field
                  label="Email Address"
                  placeholder="customer@example.com"
                  type="email"
                  value={form.email}
                  onChange={(value) =>
                    updateField("email", value)
                  }
                />
              </div>
            </div>
          )}

          {currentStep === 2 && (
            <div className="space-y-4 max-w-3xl">
              <div className="flex items-center justify-between border-b border-[var(--border)] pb-2">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Installation & Geographic Location
                </span>
                <button
                  type="button"
                  onClick={() => setIsManualGeo(!isManualGeo)}
                  className="text-[11px] text-blue-400 hover:text-blue-300 underline"
                >
                  {isManualGeo
                    ? "Select from registered Areas & Cities"
                    : "Enter custom / unlisted location manually"}
                </button>
              </div>

              {isManualGeo || (cities.length === 0 && !loadingOptions) ? (
                <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
                  <Field
                    label="Operational City *"
                    placeholder="e.g. Islamabad, Lahore"
                    value={form.city}
                    onChange={(value) => updateField("city", value)}
                  />

                  <Field
                    label="Service Area / Sector"
                    placeholder="e.g. Sector F-10/2, Johar Town"
                    value={form.area}
                    onChange={(value) => updateField("area", value)}
                  />
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
                  {/* Country Selector */}
                  <div>
                    <label className={labelClass}>Country (Optional)</label>
                    <select
                      value={selectedCountryId}
                      onChange={(e) => handleCountryChange(e.target.value)}
                      className={inputClass}
                    >
                      <option value="">All Countries</option>
                      {countries.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name} ({c.code})
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* City Selector */}
                  <div>
                    <label className={labelClass}>Operating City *</label>
                    <select
                      value={selectedCityId}
                      onChange={(e) => handleCityChange(e.target.value)}
                      className={inputClass}
                    >
                      <option value="">Select City...</option>
                      {cities.map((city) => (
                        <option key={city.id} value={city.id}>
                          {city.name}{" "}
                          {city.country_name ? `(${city.country_name})` : ""}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Area Selector */}
                  <div>
                    <label className={labelClass}>
                      Sublocality / Area
                      {loadingAreas && (
                        <span className="ml-2 inline-block">
                          <LoadingSpinner size="xs" tone="primary" />
                        </span>
                      )}
                    </label>
                    <select
                      disabled={!selectedCityId || loadingAreas}
                      value={selectedAreaId}
                      onChange={(e) => handleAreaChange(e.target.value)}
                      className={`${inputClass} disabled:opacity-50`}
                    >
                      <option value="">
                        {!selectedCityId
                          ? "Select City First..."
                          : areas.length === 0
                          ? "No areas in city (Optional)"
                          : "Select Area / Sublocality..."}
                      </option>
                      {areas.map((area) => (
                        <option key={area.id} value={area.id}>
                          {area.name} {area.code ? `[${area.code}]` : ""}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              )}

              {/* Selected Location Summary Badge */}
              {form.city && (
                <div className="rounded-md border border-[#202938] bg-[#0D1117] p-3 text-xs text-slate-300">
                  <span className="text-slate-500">Selected Region: </span>
                  <strong className="text-white">{form.city}</strong>
                  {form.area && (
                    <>
                      <span className="text-slate-500"> → Area: </span>
                      <strong className="text-blue-400">{form.area}</strong>
                    </>
                  )}
                </div>
              )}

              {/* Installation Address */}
              <div>
                <Field
                  label="Full Installation Address *"
                  placeholder="House / Flat No., Street, Building, Landmark"
                  value={form.addressLine}
                  onChange={(value) => updateField("addressLine", value)}
                />
              </div>
            </div>
          )}

          {currentStep === 3 && (
            <div className="grid max-w-3xl grid-cols-1 gap-3 md:grid-cols-2">
              {packages.length === 0 ? (
                <EmptyOptionState message="No active internet packages are available." />
              ) : (
                packages.map((internetPackage) => {
                  const selected =
                    form.internetPackageId ===
                    internetPackage.id;

                  return (
                    <button
                      key={internetPackage.id}
                      type="button"
                      onClick={() =>
                        updateField(
                          "internetPackageId",
                          internetPackage.id,
                        )
                      }
                      className={`border p-4 text-left transition-colors ${
                        selected
                          ? "border-blue-500 bg-blue-500/10"
                          : "border-[var(--border)] bg-[var(--background)] hover:border-slate-600"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-[12px] font-semibold text-white">
                          {internetPackage.name}
                        </p>

                        <span
                          className={`size-2 rounded-full ${
                            selected
                              ? "bg-blue-400"
                              : "bg-slate-700"
                          }`}
                        />
                      </div>

                      <p className="mt-2 text-[10px] text-[var(--text-muted)]">
                        {internetPackage.download_speed_mbps} Mbps down /{" "}
                        {internetPackage.upload_speed_mbps} Mbps up
                      </p>

                      <p className="mt-1 text-[10px] text-blue-400">
                        Rs.{" "}
                        {Number(
                          internetPackage.monthly_price,
                        ).toLocaleString()}{" "}
                        / month
                      </p>
                    </button>
                  );
                })
              )}
            </div>
          )}

          {currentStep === 4 && (
            <div className="grid max-w-3xl grid-cols-1 gap-5 md:grid-cols-2">
              <SelectField
                label="Network Node"
                value={form.networkNodeId}
                onChange={(value) =>
                  updateField("networkNodeId", value)
                }
              >
                <option value="">
                  Select active network node
                </option>

                {networkNodes.map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.name} ({node.code}) · {node.node_type}
                  </option>
                ))}
              </SelectField>

              <Field
                label="IP Address"
                placeholder="Optional static IP"
                value={form.networkIpAddress}
                onChange={(value) =>
                  updateField(
                    "networkIpAddress",
                    value,
                  )
                }
              />

              <div className="md:col-span-2">
                <Field
                  label="Network Username"
                  placeholder="Optional provisioning username"
                  value={form.networkUsername}
                  onChange={(value) =>
                    updateField(
                      "networkUsername",
                      value,
                    )
                  }
                />
              </div>

              {networkNodes.length === 0 && (
                <div className="md:col-span-2">
                  <EmptyOptionState message="No active network nodes are available." />
                </div>
              )}
            </div>
          )}

          {currentStep === 5 && (
            <div className="max-w-3xl space-y-4">
              <div className="border border-[var(--border)] bg-[var(--background)] p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[12px] font-semibold text-white">
                      Customer Premises Equipment (CPE) Assignment
                    </p>
                    <p className="mt-1 text-[10px] text-[var(--text-muted)]">
                      Optionally assign an available serialized ONU, ONT, or router to this service connection.
                    </p>
                  </div>
                  <span className="border border-blue-500/20 bg-blue-500/10 px-2 py-0.5 text-[9px] font-semibold text-blue-400">
                    Optional
                  </span>
                </div>

                <div className="mt-4">
                  <label className={labelClass}>Select Available Hardware Device</label>
                  {availableDevices.length === 0 ? (
                    <div className="border border-[var(--border)] bg-[var(--surface)] p-3 text-xs text-amber-400">
                      No AVAILABLE devices found in Inventory. Activation can proceed without a device, or one can be assigned later.
                    </div>
                  ) : (
                    <select
                      value={form.deviceId}
                      onChange={(e) => updateField("deviceId", e.target.value)}
                      className={inputClass}
                    >
                      <option value="">No device assigned (Skip for now)</option>
                      {availableDevices.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.asset_tag} — {d.device_type} ({d.manufacturer} {d.model_name}) [SN: {d.serial_number}]
                        </option>
                      ))}
                    </select>
                  )}
                </div>

                <div className="mt-4">
                  <Field
                    label="Custody Assignment Notes"
                    placeholder="e.g. Installed in living room / Wall mounted"
                    value={form.deviceAssignmentNotes}
                    onChange={(value) =>
                      updateField(
                        "deviceAssignmentNotes",
                        value,
                      )
                    }
                  />
                </div>
              </div>
            </div>
          )}

          {currentStep === 6 && (
            <div className="grid max-w-3xl grid-cols-1 gap-5 md:grid-cols-2">
              <Field
                label="Billing Day"
                placeholder="1"
                type="number"
                min={1}
                max={28}
                value={form.billingDay}
                onChange={(value) =>
                  updateField("billingDay", value)
                }
              />

              <Field
                label="Due Day"
                placeholder="10"
                type="number"
                min={1}
                max={28}
                value={form.dueDay}
                onChange={(value) =>
                  updateField("dueDay", value)
                }
              />

              <div className="md:col-span-2 border border-[var(--border)] bg-[var(--background)] p-4">
                <p className="text-[10px] uppercase tracking-[0.12em] text-[var(--text-muted)]">
                  Billing Cycle
                </p>

                <p className="mt-2 text-[12px] font-medium text-white">
                  Monthly
                </p>

                <p className="mt-1 text-[10px] text-[var(--text-muted)]">
                  Billing profile state is created by the backend activation
                  service.
                </p>
              </div>
            </div>
          )}

          {currentStep === 7 && (
            <div className="grid max-w-3xl grid-cols-1 gap-3 md:grid-cols-2">
              <PreferenceCard
                title="WhatsApp"
                description="Billing and service notifications"
                selected={form.whatsappEnabled}
                onClick={() =>
                  updateField(
                    "whatsappEnabled",
                    !form.whatsappEnabled,
                  )
                }
              />

              <PreferenceCard
                title="SMS"
                description="Critical service alerts"
                selected={form.smsEnabled}
                onClick={() =>
                  updateField(
                    "smsEnabled",
                    !form.smsEnabled,
                  )
                }
              />
            </div>
          )}
        </div>

        <div className="flex items-center justify-between border-t border-[var(--border)] px-7 py-4">
          <button
            type="button"
            onClick={previousStep}
            disabled={currentStep === 1 || submitting}
            className="flex h-9 items-center gap-2 border border-[var(--border)] px-3 text-[11px] text-[var(--text-secondary)] transition-colors hover:text-white disabled:cursor-not-allowed disabled:opacity-30"
          >
            <ChevronLeft className="size-4" />
            Previous
          </button>

          {currentStep < steps.length ? (
            <button
              type="button"
              onClick={nextStep}
              disabled={submitting}
              className="flex h-9 items-center gap-2 bg-blue-500 px-4 text-[11px] font-semibold text-white transition-colors hover:bg-blue-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Continue
              <ChevronRight className="size-4" />
            </button>
          ) : (
            <button
              type="button"
              onClick={activateCustomer}
              disabled={submitting}
              className="flex h-9 items-center gap-2 bg-green-500 px-4 text-[11px] font-semibold text-white transition-colors hover:bg-green-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Check className="size-4" />
              {submitting
                ? "Activating Service..."
                : "Activate Service"}
            </button>
          )}
        </div>
      </div>
    </div>
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
}

function Field({
  label,
  placeholder,
  value,
  onChange,
  type = "text",
  min,
  max,
}: FieldProps) {
  return (
    <label>
      <span className={labelClass}>{label}</span>

      <input
        type={type}
        min={min}
        max={max}
        value={value}
        onChange={(event) =>
          onChange(event.target.value)
        }
        className={inputClass}
        placeholder={placeholder}
      />
    </label>
  );
}

function SelectField({
  label,
  value,
  onChange,
  children,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  children: React.ReactNode;
}) {
  return (
    <label>
      <span className={labelClass}>{label}</span>

      <select
        value={value}
        onChange={(event) =>
          onChange(event.target.value)
        }
        className={inputClass}
      >
        {children}
      </select>
    </label>
  );
}

function PreferenceCard({
  title,
  description,
  selected,
  onClick,
}: {
  title: string;
  description: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`border p-4 text-left transition-colors ${
        selected
          ? "border-blue-500 bg-blue-500/10"
          : "border-[var(--border)] bg-[var(--background)] hover:border-slate-600"
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <p className="text-[12px] font-semibold text-white">
          {title}
        </p>

        <span
          className={`size-2 rounded-full ${
            selected
              ? "bg-blue-400"
              : "bg-slate-700"
          }`}
        />
      </div>

      <p className="mt-2 text-[10px] text-[var(--text-muted)]">
        {description}
      </p>
    </button>
  );
}

function EmptyOptionState({
  message,
}: {
  message: string;
}) {
  return (
    <div className="border border-[var(--border)] bg-[var(--background)] p-5 text-[11px] text-[var(--text-muted)] md:col-span-2">
      {message}
    </div>
  );
}
