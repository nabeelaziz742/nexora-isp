"use client";

import Link from "next/link";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { toast } from "sonner";

import { communicationsService } from "@/services/communications.service";

import {
  ArrowLeft,
  Loader2,
  Save,
} from "lucide-react";

interface TemplateOption {
  id: string;
  name: string;
}

export default function EditAutomationPage() {
  const router = useRouter();

  const params = useParams();

  const automationId = params.id as string;

  const [loading, setLoading] = useState(true);

  const [saving, setSaving] = useState(false);

  const [templates, setTemplates] =
    useState<TemplateOption[]>([]);

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
    loadPage();
  }, []);

  async function loadPage() {
    try {
      setLoading(true);

      const [
        automation,
        templatesResponse,
      ] = await Promise.all([
        communicationsService.getAutomation(
          automationId,
        ),

        communicationsService.getTemplates(),
      ]);

      setTemplates(
        Array.isArray(templatesResponse)
          ? templatesResponse
          : [],
      );

      setForm({
        name: automation.name,
        description:
          automation.description ?? "",
        trigger: automation.trigger,
        template: automation.template,
        execution_order:
          automation.execution_order,
        delay_minutes:
          automation.delay_minutes,
        max_retry_attempts:
          automation.max_retry_attempts,
        is_enabled:
          automation.is_enabled,
      });
    } catch (error) {
      console.error(error);

      toast.error(
        "Unable to load automation.",
      );
    } finally {
      setLoading(false);
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

  async function handleUpdate() {
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

      await communicationsService.updateAutomation(
        automationId,
        {
          name: form.name,
          description: form.description,
          trigger: form.trigger,
          template: form.template,
          execution_order: form.execution_order,
          delay_minutes: form.delay_minutes,
          max_retry_attempts:
            form.max_retry_attempts,
          is_enabled: form.is_enabled,
        },
      );

      toast.success(
        "Automation updated successfully.",
      );

      router.push(
        "/communications/automations",
      );
    } catch (error) {
      console.error(error);

      toast.error(
        "Unable to update automation.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="p-6">

        <div className="animate-pulse rounded-lg border border-[#202938] bg-[#0D1117] p-10">

          <div className="mb-6 h-8 w-64 rounded bg-[#111827]" />

          <div className="grid gap-6 md:grid-cols-2">

            {Array.from({ length: 8 }).map((_, index) => (
              <div
                key={index}
                className="h-12 rounded bg-[#111827]"
              />
            ))}

          </div>

        </div>

      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">

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
          Edit Automation
        </h1>

        <p className="mt-2 text-sm text-[#64748B]">
          Update automation configuration.
        </p>

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
              className="w-full rounded-md border border-[#202938] bg-[#080B10] px-4 py-2 text-white"
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
              className="w-full rounded-md border border-[#202938] bg-[#080B10] px-4 py-3 text-white"
            />

          </div>

          {/* Template */}

          <div className="space-y-2">

            <label className="text-sm font-medium text-white">
              Template
            </label>

            <select
              value={form.template}
              onChange={(e) =>
                updateField("template", e.target.value)
              }
              className="w-full rounded-md border border-[#202938] bg-[#080B10] px-4 py-2 text-white"
            >

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
              Delay Minutes
            </label>

            <input
              type="number"
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
              Retry Attempts
            </label>

            <input
              type="number"
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
                Automation Enabled
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
            onClick={handleUpdate}
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
                Save Changes
              </>
            )}

          </button>

        </div>

      </div>

    </div>
  );
}
