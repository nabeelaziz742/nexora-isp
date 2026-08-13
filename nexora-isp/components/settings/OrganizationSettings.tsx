import type { OrganizationSettingsData } from "@/types/settings";

interface OrganizationSettingsProps {
  settings: OrganizationSettingsData;
}

export default function OrganizationSettings({
  settings,
}: OrganizationSettingsProps) {
  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="border-b border-[#202938] px-5 py-4">
        <h2 className="text-sm font-semibold text-slate-100">
          ISP Organization
        </h2>

        <p className="mt-1 text-xs text-slate-500">
          Organization identity and regional operating context
        </p>
      </div>

      <div className="grid gap-5 p-5 md:grid-cols-2 xl:grid-cols-3">
        <SettingField
          label="Organization Name"
          value={settings.organizationName}
        />

        <SettingField
          label="Organization Code"
          value={settings.organizationCode}
        />

        <SettingField
          label="Support Phone"
          value={settings.supportPhone}
        />

        <SettingField
          label="Support Email"
          value={settings.supportEmail}
        />

        <SettingField
          label="Operating City"
          value={settings.city}
        />

        <SettingField
          label="Timezone"
          value={settings.timezone}
        />

        <SettingField
          label="Currency"
          value={settings.currency}
        />
      </div>

      <div className="flex justify-end border-t border-[#202938] px-5 py-4">
        <button className="bg-blue-600 px-4 py-2 text-xs font-medium text-white transition hover:bg-blue-500">
          Save Organization Settings
        </button>
      </div>
    </section>
  );
}

interface SettingFieldProps {
  label: string;
  value: string;
}

function SettingField({
  label,
  value,
}: SettingFieldProps) {
  return (
    <label className="block">
      <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">
        {label}
      </span>

      <input
        type="text"
        defaultValue={value}
        className="mt-2 h-10 w-full border border-[#202938] bg-[#070A0F] px-3 text-xs text-slate-200 outline-none transition focus:border-blue-500"
      />
    </label>
  );
}