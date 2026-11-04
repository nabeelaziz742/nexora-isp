"use client";

import { useMemo } from "react";

export interface Provider {
  id: string;
  name: string;
  provider_type: "WHATSAPP" | "SMS" | "EMAIL";
}

// "customer_name, due_date" -> ["customer_name", "due_date"]
export function parseTemplateParams(value: string | undefined): string[] {
  return (value ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

interface TemplateFormProps {
  form: {
    name: string;
    subject: string;
    body: string;
    status: string;
    communication_provider: string;
    whatsapp_template_name?: string;
    whatsapp_template_language?: string;
    // Comma-separated variable names, in the Meta template's {{1}}, {{2}} order.
    whatsapp_template_params?: string;
  };

  providers: Provider[];

  loading?: boolean;

  onChange: (
    field: string,
    value: string,
  ) => void;

  onSave: () => void;

  onPreview: () => void;

  saveLabel?: string;
}

export default function TemplateForm({
  form,
  providers,
  loading = false,
  onChange,
  onSave,
  onPreview,
  saveLabel = "Save",
}: TemplateFormProps) {

  const variables = useMemo(() => {

    return Array.from(
      new Set(
        (
          form.body.match(
            /{{\s*([a-zA-Z0-9_]+)\s*}}/g,
          ) || []
        ).map((item) =>
          item
            .replace(/[{}]/g, "")
            .trim(),
        ),
      ),
    );

  }, [form.body]);

  const isWhatsApp =
    providers.find((provider) => provider.id === form.communication_provider)
      ?.provider_type === "WHATSAPP";

  return (

    <div className="grid gap-6 lg:grid-cols-3">

      <div className="space-y-5 lg:col-span-2">

        <div className="space-y-5 border border-[#202938] bg-[#0D1117] p-6">

          <div>

            <label className="mb-2 block text-sm text-white">

              Template Name

            </label>

            <input
              value={form.name}
              onChange={(e) => {
                console.log("INPUT NAME:", e.target.value);
                onChange("name", e.target.value);
              }}
              className="w-full border border-[#202938] bg-[#080B10] px-4 py-2 text-white"
            />

          </div>

          <div>

            <label className="mb-2 block text-sm text-white">

              Provider

            </label>

            <select
              value={form.communication_provider}
              onChange={(e) => {
                console.log("INPUT PROVIDER:", e.target.value);
                onChange("communication_provider", e.target.value);
              }}
              className="w-full border border-[#202938] bg-[#080B10] px-4 py-2 text-white"
            >

              <option value="">

                Select Provider

              </option>

              {providers.map((provider) => (

                <option
                  key={provider.id}
                  value={provider.id}
                >

                  {provider.name}

                </option>

              ))}

            </select>

          </div>

          <div>

            <label className="mb-2 block text-sm text-white">

              Subject

            </label>

            <input
              value={form.subject}
              onChange={(e) =>
                onChange(
                  "subject",
                  e.target.value,
                )
              }
              className="w-full border border-[#202938] bg-[#080B10] px-4 py-2 text-white"
            />

          </div>

          <div>

            <label className="mb-2 block text-sm text-white">

              Message

            </label>

            <textarea
              rows={12}
              value={form.body}
              onChange={(e) => {
                console.log("INPUT BODY:", e.target.value);
                onChange("body", e.target.value);
              }}
              className="w-full border border-[#202938] bg-[#080B10] px-4 py-3 text-white"
            />

          </div>

          {isWhatsApp && (
            <div className="space-y-4 border border-emerald-500/20 bg-emerald-500/5 p-4">
              <div>
                <h3 className="text-sm font-semibold text-white">
                  WhatsApp (Meta) Template
                </h3>
                <p className="mt-1 text-xs text-[#94A3B8]">
                  Meta only delivers business-initiated messages through approved templates.
                  Without one, the message above is sent as plain text and reaches only
                  customers who messaged you in the last 24 hours.
                </p>
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                <div className="sm:col-span-2">
                  <label className="mb-2 block text-sm text-white">
                    Approved Template Name
                  </label>
                  <input
                    value={form.whatsapp_template_name ?? ""}
                    onChange={(e) => onChange("whatsapp_template_name", e.target.value)}
                    placeholder="e.g. nexora_bill_overdue"
                    className="w-full border border-[#202938] bg-[#080B10] px-4 py-2 font-mono text-white"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm text-white">
                    Language Code
                  </label>
                  <input
                    value={form.whatsapp_template_language ?? "en"}
                    onChange={(e) => onChange("whatsapp_template_language", e.target.value)}
                    placeholder="en"
                    className="w-full border border-[#202938] bg-[#080B10] px-4 py-2 font-mono text-white"
                  />
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm text-white">
                  Template Variables (in order)
                </label>
                <input
                  value={form.whatsapp_template_params ?? ""}
                  onChange={(e) => onChange("whatsapp_template_params", e.target.value)}
                  placeholder="customer_name, outstanding_amount, invoice_number, due_date"
                  className="w-full border border-[#202938] bg-[#080B10] px-4 py-2 font-mono text-white"
                />
                <p className="mt-1 text-xs text-[#64748B]">
                  First name fills {"{{1}}"}, second fills {"{{2}}"}, and so on. Use the same
                  variable names as the message above.
                </p>
              </div>
            </div>
          )}

                    <div>

            <label className="mb-2 block text-sm text-white">
              Status
            </label>

            <select
              value={form.status}
              onChange={(e) =>
                onChange("status", e.target.value)
              }
              className="w-full border border-[#202938] bg-[#080B10] px-4 py-2 text-white"
            >
              <option value="DRAFT">
                Draft
              </option>

              <option value="ACTIVE">
                Active
              </option>

              <option value="ARCHIVED">
                Archived
              </option>

            </select>

          </div>

          <div className="flex flex-wrap justify-end gap-3 pt-2">

            <button
              type="button"
              onClick={onPreview}
              className="rounded-md border border-[#202938] bg-[#111827] px-4 py-2 text-sm text-white transition hover:border-cyan-500"
            >
              Preview
            </button>

            <button
              type="button"
              disabled={loading}
              onClick={onSave}
              className="rounded-md bg-green-500 px-5 py-2 text-sm font-medium text-black transition hover:bg-green-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Saving..." : saveLabel}
            </button>

          </div>

        </div>

      </div>

      <div className="space-y-5">

        <div className="border border-[#202938] bg-[#0D1117] p-6">

          <h2 className="mb-4 text-lg font-semibold text-white">
            Detected Variables
          </h2>

          <div className="flex flex-wrap gap-2">

            {variables.length === 0 && (
              <p className="text-sm text-[#64748B]">
                No variables detected.
              </p>
            )}

            {variables.map((variable) => (
              <span
                key={variable}
                className="rounded-md border border-cyan-500/20 bg-cyan-500/10 px-2 py-1 text-xs text-cyan-400"
              >
                {variable}
              </span>
            ))}

          </div>

        </div>

        <div className="border border-[#202938] bg-[#0D1117] p-6">

          <h2 className="mb-4 text-lg font-semibold text-white">
            Common Variables
          </h2>

          <div className="space-y-2 text-sm text-[#94A3B8]">

            <div>{"{{customer_name}}"}</div>
            <div>{"{{organization_name}}"}</div>
            <div>{"{{invoice_number}}"}</div>
            <div>{"{{amount}}"}</div>
            <div>{"{{due_date}}"}</div>
            <div>{"{{service_name}}"}</div>
            <div>{"{{ticket_number}}"}</div>
            <div>{"{{payment_date}}"}</div>
            <div>{"{{technician_name}}"}</div>

          </div>

        </div>

      </div>

    </div>

  );
}
