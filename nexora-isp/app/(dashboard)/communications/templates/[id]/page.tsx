"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";

import { ArrowLeft, Loader2 } from "lucide-react";

import TemplateForm, {
  Provider,
} from "@/components/communications/template-form";

import {
  communicationsService,
  type CommunicationTemplate,
} from "@/services/communications.service";

type TemplateFormState = Pick<
  CommunicationTemplate,
  "name" | "subject" | "body" | "status" | "communication_provider"
>;

export default function EditCommunicationTemplatePage() {
  const router = useRouter();

  const { id } = useParams<{ id: string }>();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [providers, setProviders] = useState<Provider[]>([]);

  const [form, setForm] = useState<TemplateFormState>({
    name: "",
    subject: "",
    body: "",
    status: "DRAFT",
    communication_provider: "",
  });

  useEffect(() => {
    void loadPage();
  }, [id]);

  async function loadPage() {
    try {
      setLoading(true);

      const [template, providerList] = await Promise.all([
        communicationsService.getTemplate(id),
        communicationsService.getProviders(),
      ]);

      setProviders(Array.isArray(providerList) ? providerList : []);

      setForm({
        name: template.name,
        subject: template.subject ?? "",
        body: template.body ?? "",
        status: template.status,
        communication_provider: template.communication_provider,
      });
    } finally {
      setLoading(false);
    }
  }

  function handleChange(
    field: string,
    value: string,
  ) {
    if (field === "status") {
      if (
        value !== "ACTIVE" &&
        value !== "DRAFT" &&
        value !== "ARCHIVED"
      ) {
        return;
      }

      setForm((prev) => ({
        ...prev,
        status: value,
      }));
      return;
    }

    if (
      field !== "name" &&
      field !== "subject" &&
      field !== "body" &&
      field !== "communication_provider"
    ) {
      return;
    }

    setForm((prev) => ({
      ...prev,
      [field]: value,
    }));
  }

  async function handleSave() {
    try {
      setSaving(true);

      await communicationsService.updateTemplate(id, form);

      toast.success("Template updated successfully.");
      router.push("/communications/templates");
    } catch (err) {
      console.error(err);
      toast.error("Unable to update template.");
    } finally {
      setSaving(false);
    }
  }

  async function handlePreview() {
    try {
      const response = await communicationsService.previewTemplate(id, {});
      console.log(response);
    } catch (err) {
      console.error(err);
    }
  }

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <Link
          href="/communications/templates"
          className="mb-4 inline-flex items-center gap-2 text-sm text-cyan-400"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Link>

        <h1 className="text-2xl font-semibold text-white">
          Edit Template
        </h1>

        <p className="mt-2 text-sm text-[#64748B]">
          Update communication template.
        </p>
      </div>

      <TemplateForm
        form={form}
        providers={providers}
        loading={saving}
        onChange={handleChange}
        onSave={handleSave}
        onPreview={handlePreview}
        saveLabel="Save Changes"
      />
    </div>
  );
}
