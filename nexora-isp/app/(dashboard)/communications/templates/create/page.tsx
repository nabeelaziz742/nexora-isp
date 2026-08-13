"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { toast } from "sonner";

import TemplateForm from "@/components/communications/template-form";
import { communicationsService } from "@/services/communications.service";

interface Provider {
  id: string;
  name: string;
  provider_type: "WHATSAPP" | "SMS" | "EMAIL";
}

export default function CreateCommunicationTemplatePage() {
  const router = useRouter();

  const [loading, setLoading] = useState(false);

  const [providers, setProviders] = useState<Provider[]>([]);

  const [form, setForm] = useState({
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
  console.log("HANDLE CHANGE:", field, value);

  setForm((prev) => ({
    ...prev,
    [field]: value,
  }));
}

  async function handleSave() {
  try {
    setLoading(true);

    console.log("FORM DATA:", JSON.stringify(form, null, 2));

    await communicationsService.createTemplate(form);

    router.push("/communications/templates");
  } catch (err) {
    console.error(err);
    alert("Unable to create template.");
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