"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { toast } from "sonner";

import TemplateForm from "@/components/communications/template-form";
import {
  communicationsService,
  type CommunicationTemplate,
} from "@/services/communications.service";

interface Provider {
  id: string;
  name: string;
  provider_type: "WHATSAPP" | "SMS" | "EMAIL";
}

type TemplateFormState = Pick<
  CommunicationTemplate,
  "name" | "subject" | "body" | "status" | "communication_provider"
>;

export default function CreateCommunicationTemplatePage() {
  const router = useRouter();

  const [loading, setLoading] = useState(false);

  const [providers, setProviders] = useState<Provider[]>([]);

  const [form, setForm] = useState<TemplateFormState>({
    name: "",
    subject: "",
    body: "",
    status: "DRAFT",
    communication_provider: "",
  });

  useEffect(() => {
    loadProviders();
  }, []);

  async function loadProviders() {
    try {
      const data =
        await communicationsService.getProviders();

      setProviders(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error(err);
    }
  }

  function handleChange(
    field: string,
    value: string,
  ) {
    if (
      field === "status" &&
      value !== "DRAFT" &&
      value !== "ACTIVE" &&
      value !== "ARCHIVED"
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
      setLoading(true);

      await communicationsService.createTemplate(form);

      toast.success("Template created successfully.");
      router.push("/communications/templates");
    } catch (err) {
      console.error(err);
      toast.error("Unable to create template.");
    } finally {
      setLoading(false);
    }
  }

  async function handlePreview() {
    console.log(form);
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
          Create Template
        </h1>

        <p className="mt-2 text-sm text-[#64748B]">
          Create reusable communication templates.
        </p>
      </div>

      <TemplateForm
        form={form}
        providers={providers}
        loading={loading}
        onChange={handleChange}
        onSave={handleSave}
        onPreview={handlePreview}
        saveLabel="Create Template"
      />
    </div>
  );
}
