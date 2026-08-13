"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { communicationsService } from "@/services/communications.service";

import {
  ArrowLeft,
  Save,
  Loader2,
} from "lucide-react";

interface TemplateOption {
  id: string;
  name: string;
}

export default function CreateAutomationPage() {
  const router = useRouter();

  const [saving, setSaving] = useState(false);

  const [templates, setTemplates] = useState<
    TemplateOption[]
  >([]);

  const [form, setForm] = useState({
    name: "",
    description: "",
    trigger: "",
    template: "",
    execution_order: 1,
    delay_minutes: 0,
    max_retry_attempts: 3,
    is_enabled: true,
  });

  useEffect(() => {
    loadTemplates();
  }, []);

  async function loadTemplates() {
    try {
      const response =
        await communicationsService.getTemplates();

      const items = Array.isArray(response)
        ? response
        : [];

      setTemplates(items);
    } catch (error) {
      console.error(error);

      toast.error(
        "Unable to load templates.",
      );
    }
  }

  function updateField(
    key: keyof typeof form,
    value: any,
  ) {
    setForm((prev) => ({
      ...prev,
      [key]: value,
    }));
  }

  async function handleSubmit() {
    if (!form.name.trim()) {
      toast.error("Automation name is required.");
      return;
    }

    if (!form.trigger) {
      toast.error("Please select a trigger.");
      return;
    }

    if (!form.template) {
      toast.error("Please select a template.");
      return;
    }

    try {
      setSaving(true);

      await communicationsService.createAutomation({
        name: form.name,
        description: form.description,
        trigger: form.trigger,
        template: form.template,
        execution_order: form.execution_order,
        delay_minutes: form.delay_minutes,
        max_retry_attempts: form.max_retry_attempts,
        is_enabled: form.is_enabled,
      });

      toast.success(
        "Automation created successfully.",
      );

      router.push(
        "/communications/automations",
      );
    } catch (error) {
      console.error(error);

      toast.error(
        "Unable to create automation.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6 p-6">

      <div className="flex items-center justify-between">

        <div>

          <Link
            href="/communications/automations"
            className="mb-3 inline-flex items-center gap-2 text-sm text-[#94A3B8] hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </Link>

          <p className="text-[10px] font-semibold uppercase tracking-[0.20em] text-green-400">
            Communication
          </p>

          <h1 className="mt-2 text-2xl font-semibold text-white">
            Create Automation
          </h1>

          <p className="mt-2 text-sm text-[#64748B]">
            Configure an automated communication
            workflow.
          </p>

        </div>

      </div>

      <div className="rounded-lg border border-[#202938] bg-[#0D1117]">

        <div className="border-b border-[#202938] px-6 py-4">

          <h2 className="text-lg font-semibold text-white">
            Automation Details
          </h2>

        </div>

        <div className="grid gap-6 p-6 md:grid-cols-2">

          {/* Name */}

          <div className="space-y-2">

            <label className="text-sm font-medium text-white">
              Automation Name
            </label>

            <input
              value={form.name}
              onChange={(e) =>
                updateField("name", e.target.value)
              }
              placeholder="Invoice Reminder Automation"
              className="w-full rounded-md border border-[#202938] bg-[#080B10] px-4 py-2 text-white outline-none focus:border-green-500"
            />

          </div>

          {/* Trigger */}

          <div className="space-y-2">

            <label className="text-sm font-medium text-white">
              Trigger
            </label>

            <select
              value={form.trigger}
              onChange={(e) =>
                updateField("trigger", e.target.value)
              }
              className="w-full rounded-md border border-[#202938] bg-[#080B10] px-4 py-2 text-white"
            >

              <option value="">
                Select Trigger
              </option>

              <option value="CUSTOMER_CREATED">
                Customer Created
              </option>

              <option value="SERVICE_ACTIVATED">
                Service Activated
              </option>

              <option value="INVOICE_CREATED">
                Invoice Generated
              </option>

              <option value="PAYMENT_RECEIVED">
                Payment Received
              </option>

              <option value="TICKET_CREATED">
                Ticket Created
              </option>

            </select>

          </div>

          {/* Description */}

          <div className="space-y-2 md:col-span-2">

            <label className="text-sm font-medium text-white">
              Description
            </label>

            <textarea
              rows={4}
              value={form.description}
              onChange={(e) =>
                updateField(
                  "description",
                  e.target.value,
                )
              }
              placeholder="Describe what this automation does..."
              className="w-full rounded-md border border-[#202938] bg-[#080B10] px-4 py-3 text-white outline-none focus:border-green-500"
            />

          </div>

          {/* Template */}

          <div className="space-y-2">

            <label className="text-sm font-medium text-white">
              Communication Template
            </label>

            <select
              value={form.template}
              onChange={(e) =>
                updateField(
                  "template",
                  e.target.value,
                )
              }
              className="w-full rounded-md border border-[#202938] bg-[#080B10] px-4 py-2 text-white"
            >

              <option value="">
                Select Template
              </option>

              {templates.map((template) => (

                <option
                  key={template.id}
                  value={template.id}
                >
                  {template.name}
                </option>

              ))}

            </select>

          </div>

          {/* Execution Order */}

          <div className="space-y-2">

            <label className="text-sm font-medium text-white">
              Execution Order
            </label>

            <input
              type="number"
              min={1}
              value={form.execution_order}
              onChange={(e) =>
                updateField(
                  "execution_order",
                  Number(e.target.value),
                )
              }
              className="w-full rounded-md border border-[#202938] bg-[#080B10] px-4 py-2 text-white"
            />

          </div>

          {/* Delay */}

          <div className="space-y-2">

            <label className="text-sm font-medium text-white">
              Delay (Minutes)
            </label>

            <input
              type="number"
              min={0}
              value={form.delay_minutes}
              onChange={(e) =>
                updateField(
                  "delay_minutes",
                  Number(e.target.value),
                )
              }
              className="w-full rounded-md border border-[#202938] bg-[#080B10] px-4 py-2 text-white"
            />

          </div>

          {/* Retry */}

          <div className="space-y-2">

            <label className="text-sm font-medium text-white">
              Max Retry Attempts
            </label>

            <input
              type="number"
              min={0}
              value={form.max_retry_attempts}
              onChange={(e) =>
                updateField(
                  "max_retry_attempts",
                  Number(e.target.value),
                )
              }
              className="w-full rounded-md border border-[#202938] bg-[#080B10] px-4 py-2 text-white"
            />

          </div>

          {/* Enabled */}

          <div className="md:col-span-2">

            <label className="flex items-center gap-3 rounded-md border border-[#202938] bg-[#080B10] px-4 py-3">

              <input
                type="checkbox"
                checked={form.is_enabled}
                onChange={(e) =>
                  updateField(
                    "is_enabled",
                    e.target.checked,
                  )
                }
              />

              <span className="text-sm text-white">
                Enable this automation immediately after creation
              </span>

            </label>

          </div>

        </div>

        <div className="flex justify-end gap-3 border-t border-[#202938] px-6 py-4">

          <Link
            href="/communications/automations"
            className="rounded-md border border-[#202938] bg-[#111827] px-4 py-2 text-sm text-white transition hover:border-cyan-500"
          >
            Cancel
          </Link>

          <button
            type="button"
            disabled={saving}
            onClick={handleSubmit}
            className="flex items-center gap-2 rounded-md bg-green-500 px-5 py-2 text-sm font-medium text-black transition hover:bg-green-400 disabled:cursor-not-allowed disabled:opacity-60"
          >

            {saving ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="h-4 w-4" />
                Create Automation
              </>
            )}

          </button>

        </div>

      </div>

    </div>
  );
}
